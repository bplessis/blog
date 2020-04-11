#!/usr/bin/env python

"""Healthchecker for exabgp.

This program is to be used as a process for exabgp. It will announce
some VIP depending on the state of a check whose a third-party program
wrapped by this program.

To use, declare this program as a process in your
:file:`/etc/exabgp/exabgp.conf`::

    neighbor 192.0.2.1 {
       router-id 192.0.2.2;
       local-as 64496;
       peer-as 64497;
    }
    process watch-haproxy {
       run python healthcheckHaproxy --url "/_healthcheck" --label haproxy;
    }
    process watch-mysql {
       run python -m exabgp healthcheck --cmd "mysql -u check -e 'SELECT 1'" --label mysql;
    }

"""

from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
import subprocess
import re
import logging
import logging.handlers
import argparse
import signal
import time
import collections
import requests

logger = logging.getLogger("healthcheck")

try:
    # Python 3.3+ or backport
    from ipaddress import ip_network as ip_network  # pylint: disable=F0401
    from ipaddress import ip_address as ip_address  # pylint: disable=F0401

    def fix(f):
        def fixed(x):
            try:
                x = x.decode('ascii')
            except AttributeError:
                pass
            return f(x)
        return fixed
    ip_network = fix(ip_network)
    ip_address = fix(ip_address)

except ImportError:
    try:
        # Python 2.6, 2.7, 3.2
        from ipaddr import IPNetwork as ip_network
        from ipaddr import IPAddress as ip_address
    except ImportError:
        sys.stderr.write(
            '\n'
            'This program requires the python module ip_address (for python 3.3+) or ipaddr (for python 2.6, 2.7, 3.2)\n'
            'Please pip install one of them with one of the following command.\n'
            '> pip install ip_address\n'
            '> pip install ipaddr\n'
            '\n'
        )
        sys.exit(1)

def enum(*sequential):
    """Create a simple enumeration."""
    return type(str("Enum"), (), dict(zip(sequential, sequential)))


def parse():
    """Parse arguments"""
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=sys.modules[__name__].__doc__,
                                     formatter_class=formatter)

    g = parser.add_mutually_exclusive_group()
    g.add_argument("--debug", "-d", action="store_true",
                   default=False,
                   help="enable debugging")
    g.add_argument("--silent", "-s", action="store_true",
                   default=False,
                   help="don't log to console")
    g.add_argument("--syslog-facility", "-sF", metavar="FACILITY",
                   nargs='?',
                   const="daemon",
                   default="daemon",
                   help=("log to syslog using FACILITY, "
                         "default FACILITY is daemon"))
    g.add_argument("--no-syslog", action="store_true",
                   help="disable syslog logging")
    parser.add_argument("--name", "-n", metavar="NAME",
                        help="name for this healthchecker")
    parser.add_argument("--pid", "-p", metavar="FILE",
                        type=argparse.FileType('w'),
                        help="write PID to the provided file")

    g = parser.add_argument_group("checking healthiness")
    g.add_argument("--interval", "-i", metavar='N',
                   default=5,
                   type=float,
                   help="wait N seconds between each healthcheck")
    g.add_argument("--fast-interval", "-f", metavar='N',
                   default=1,
                   type=float, dest="fast",
                   help=("when a state change is about to occur, "
                         "wait N seconds between each healthcheck"))
    g.add_argument("--timeout", "-t", metavar='N',
                   default=5,
                   type=int,
                   help="wait N seconds for the check command to execute")
    g.add_argument("--rise", metavar='N',
                   default=3,
                   type=int,
                   help="check N times before considering the service up")
    g.add_argument("--fall", metavar='N',
                   default=3,
                   type=int,
                   help="check N times before considering the service down")
    g.add_argument("--disable", metavar='FILE',
                   type=str,
                   help="if FILE exists, the service is considered disabled")
    g.add_argument("--command", "--cmd", "-c", metavar='CMD',
                   type=str,
                   help="command to use for healthcheck")

    g = parser.add_argument_group("haproxy dataplane api")
    g.add_argument("--api-url", metavar='N',
                   type=str,
                   default="http://localhost:5555/v1/services/haproxy",
                   help="self IP address to use as next hop")
    g.add_argument("--api-login", metavar='N',
                   type=str,
                   default="dataplaneapi",
                   help="Login to access dataplane API")
    g.add_argument("--api-password", metavar='N',
                   type=str,
                   help="Password to access dataplane API")

    g = parser.add_argument_group("advertising options")
    g.add_argument("--next-hop", "-N", metavar='IP',
                   type=ip_address,
                   help="self IP address to use as next hop")
    g.add_argument("--ip", metavar='IP',
                   type=ip_network, dest="ips", action="append",
                   help="advertise this IP address or network (CIDR notation)")
    g.add_argument("--deaggregate-networks",
                   dest="deaggregate_networks", action="store_true",
                   help="Deaggregate Networks specified in --ip")
    g.add_argument("--no-ip-setup",
                   action="store_false", dest="ip_setup",
                   help="don't setup missing IP addresses")
    g.add_argument("--dynamic-ip-setup", default=False,
                   action="store_true", dest="ip_dynamic",
                   help="delete existing loopback ips on state down and "
                        "disabled, then restore loopback when up")
    g.add_argument("--label", default=None,
                   help="use the provided label to match loopback addresses")
    g.add_argument("--start-ip", metavar='N',
                   type=int, default=0,
                   help="index of the first IP in the list of IP addresses")
    g.add_argument("--up-metric", metavar='M',
                   type=int, default=100,
                   help="first IP get the metric M when the service is up")
    g.add_argument("--down-metric", metavar='M',
                   type=int, default=1000,
                   help="first IP get the metric M when the service is down")
    g.add_argument("--disabled-metric", metavar='M',
                   type=int, default=500,
                   help=("first IP get the metric M "
                         "when the service is disabled"))
    g.add_argument("--increase", metavar='M',
                   type=int, default=1,
                   help=("for each additional IP address, "
                         "increase metric value by M"))
    g.add_argument("--community", metavar="COMMUNITY",
                   type=str, default=None,
                   help="announce IPs with the supplied community")
    g.add_argument("--extended-community", metavar="EXTENDEDCOMMUNITY",
                   type=str, default=None,
                   help="announce IPs with the supplied extended community")
    g.add_argument("--large-community", metavar="LARGECOMMUNITY",
                   type=str, default=None,
                   help="announce IPs with the supplied large community")
    g.add_argument("--disabled-community", metavar="DISABLEDCOMMUNITY",
                   type=str, default=None,
                   help="announce IPs with the supplied community when disabled")
    g.add_argument("--as-path", metavar="ASPATH",
                   type=str, default=None,
                   help="announce IPs with the supplied as-path")
    g.add_argument("--withdraw-on-down", action="store_true",
                   help=("Instead of increasing the metric on health failure, "
                         "withdraw the route"))

    g = parser.add_argument_group("reporting")
    g.add_argument("--execute", metavar='CMD',
                   type=str, action="append",
                   help="execute CMD on state change")
    g.add_argument("--up-execute", metavar='CMD',
                   type=str, action="append",
                   help="execute CMD when the service becomes available")
    g.add_argument("--down-execute", metavar='CMD',
                   type=str, action="append",
                   help="execute CMD when the service becomes unavailable")
    g.add_argument("--disabled-execute", metavar='CMD',
                   type=str, action="append",
                   help="execute CMD when the service is disabled")

    options = parser.parse_args()
    return options


def setup_logging(debug, silent, name, syslog_facility, syslog):
    """Setup logger"""

    def syslog_address():
        """Return a sensible syslog address"""
        if sys.platform == "darwin":
            return "/var/run/syslog"
        if sys.platform.startswith("freebsd"):
            return "/var/run/log"
        if sys.platform.startswith("netbsd"):
            return "/var/run/log"
        if sys.platform.startswith("linux"):
            return "/dev/log"
        raise EnvironmentError("Unable to guess syslog address for your "
                               "platform, try to disable syslog")

    logger.setLevel(debug and logging.DEBUG or logging.INFO)
    enable_syslog = syslog and not debug
    # To syslog
    if enable_syslog:
        facility = getattr(logging.handlers.SysLogHandler,
                           "LOG_{0}".format(syslog_facility.upper()))
        sh = logging.handlers.SysLogHandler(address=str(syslog_address()),
                                            facility=facility)
        if name:
            healthcheck_name = "healthcheck-{0}".format(name)
        else:
            healthcheck_name = "healthcheck"
        sh.setFormatter(logging.Formatter(
            "{0}[{1}]: %(message)s".format(
                healthcheck_name,
                os.getpid())))
        logger.addHandler(sh)
    # To console
    toconsole = (hasattr(sys.stderr, "isatty") and
                 sys.stderr.isatty() and  # pylint: disable=E1101
                 not silent)
    if toconsole:
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter(
            "%(levelname)s[%(name)s] %(message)s"))
        logger.addHandler(ch)

def retrieve_ips(url, login, password):

    haApiCtx = requests.Session()
    haApiCtx.auth = ( login, password )

    # List Frontends
    hapFrontends = haApiCtx.get( '%s/configuration/frontends' % url ).json()

    annonceList = []
    for frontend in hapFrontends['data']:
        hapBind = haApiCtx.get( '%s/configuration/binds?frontend=%s' % (url, frontend['name'] ) ).json()

        for data in hapBind['data']:
            annonceList.append( data['address'] )

    return list( set( annonceList ) )

def check(cmd, ip, timeout):
    """Check the return code of the given command.

    :param cmd: command to execute. If :keyword:`None`, no command is executed.
    :param timeout: how much time we should wait for command completion.
    :return: :keyword:`True` if the command was successful or
             :keyword:`False` if not or if the timeout was triggered.
    """
    if cmd is None:
        return True

    class Alarm(Exception):
        """Exception to signal an alarm condition."""
        pass

    def alarm_handler(number, frame):  # pylint: disable=W0613
        """Handle SIGALRM signal."""
        raise Alarm()

    logger.debug("Checking command %s", repr(cmd % ip))
    p = subprocess.Popen(cmd % ip, shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         preexec_fn=os.setpgrp)
    if timeout:
        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(timeout)
    try:
        stdout = None
        stdout, _ = p.communicate()
        if timeout:
            signal.alarm(0)
        if p.returncode != 0:
            logger.warn("Check command was unsuccessful: %s",
                        p.returncode)
            if stdout.strip():
                logger.info("Output of check command: %s", stdout)
            return False
        logger.debug(
            "Command was executed successfully %s %s", p.returncode, stdout)
        return True
    except Alarm:
        logger.warn("Timeout (%s) while running check command %s",
                    timeout, cmd)
        os.killpg(p.pid, signal.SIGKILL)
        return False


def loop(options):
    """Main loop."""
    states = enum(
        "INIT",                 # Initial state
        "DISABLED",             # Disabled state
        "RISING",               # Checks are currently succeeding.
        "FALLING",              # Checks are currently failing.
        "UP",                   # Service is considered as up.
        "DOWN",                 # Service is considered as down.
    )

    def exabgp(target,ip):
        """Communicate new state to ExaBGP"""
        if target not in (states.UP, states.DOWN, states.DISABLED):
            return

        logger.info("send announces for %s state to ExaBGP", target)
        metric = vars(options).get("{0}_metric".format(str(target).lower()))
        if options.withdraw_on_down:
            command = "announce" if target is states.UP else "withdraw"
        else:
            command = "announce"
        announce = "route {0} next-hop {1}".format(
            str(ip),
            options.next_hop or "self")

        if command == "announce":
            announce = "{0} med {1}".format(announce, metric)
            if options.community or options.disabled_community:
                community = options.community
                if target in (states.DOWN, states.DISABLED):
                    if options.disabled_community:
                        community = options.disabled_community
                if community:
                    announce = "{0} community [ {1} ]".format(
                        announce, community)
            if options.extended_community:
                announce = "{0} extended-community [ {1} ]".format(
                    announce,
                    options.extended_community)
            if options.large_community:
                announce = "{0} large-community [ {1} ]".format(
                    announce,
                    options.large_community)
            if options.as_path:
                announce = "{0} as-path [ {1} ]".format(
                    announce,
                    options.as_path)

        logger.debug("exabgp: {0} {1}".format(command, announce))
        print("{0} {1}".format(command, announce))
        # Flush command and wait for confirmation from ExaBGP
        sys.stdout.flush()
        sys.stdin.readline()
        metric += options.increase

    def trigger(target):
        """Trigger a state change and execute the appropriate commands"""
        # Shortcut for RISING->UP and FALLING->UP
        if target == states.RISING and options.rise <= 1:
            target = states.UP
        elif target == states.FALLING and options.fall <= 1:
            target = states.DOWN

        # Log and execute commands
        logger.debug("Transition to %s", str(target))
        cmds = []
        cmds.extend(vars(options).get("{0}_execute".format(
            str(target).lower()), []) or [])
        cmds.extend(vars(options).get("execute", []) or [])
        for cmd in cmds:
            logger.debug("Transition to %s, execute `%s`",
                         str(target), cmd)
            env = os.environ.copy()
            env.update({"STATE": str(target)})
            with open(os.devnull, "w") as fnull:
                subprocess.call(
                    cmd, shell=True, stdout=fnull, stderr=fnull, env=env)

        return target

    def one(checks, ip, state):
        """Execute one loop iteration."""
        disabled = (options.disable is not None and
                    os.path.exists(options.disable))
        successful = disabled or check(options.command, ip, options.timeout)
        # FSM
        if state != states.DISABLED and disabled:
            state = trigger(states.DISABLED)
        elif state == states.INIT:
            if successful and options.rise <= 1:
                state = trigger(states.UP)
            elif successful:
                state = trigger(states.RISING)
                checks = 1
            else:
                state = trigger(states.FALLING)
                checks = 1
        elif state == states.DISABLED:
            if not disabled:
                state = trigger(states.INIT)
        elif state == states.RISING:
            if successful:
                checks += 1
                if checks >= options.rise:
                    state = trigger(states.UP)
            else:
                state = trigger(states.FALLING)
                checks = 1
        elif state == states.FALLING:
            if not successful:
                checks += 1
                if checks >= options.fall:
                    state = trigger(states.DOWN)
            else:
                state = trigger(states.RISING)
                checks = 1
        elif state == states.UP:
            if not successful:
                state = trigger(states.FALLING)
                checks = 1
        elif state == states.DOWN:
            if successful:
                state = trigger(states.RISING)
                checks = 1
        else:
            raise ValueError("Unhandled state: {0}".format(str(state)))

        # Send announces. We announce them on a regular basis in case
        # we lose connection with a peer.
        exabgp(state, ip)
        return checks, state

    checks = 0
    state = {}
    for ip in options.ips:
        state[ip] = states.INIT

    while True:
        for ip in options.ips:
            checks, s = one(checks, ip, state[ip])
            state[ip] = s

        # How much we should sleep?
#        if state in (states.FALLING, states.RISING):
#            time.sleep(options.fast)
#        else:
        time.sleep(options.interval)


def main():
    """Entry point."""
    options = parse()
    setup_logging(options.debug, options.silent, options.name,
                  options.syslog_facility, not options.no_syslog)
    if options.pid:
        options.pid.write("{0}\n".format(os.getpid()))
        options.pid.close()
    try:
        # Get IP to annonce from haproxy dataplance
        options.ips = retrieve_ips(options.api_url, options.api_login, options.api_password)
        if not options.ips:
            logger.error("No IP found")
            sys.exit(1)

        # Parse defined networks into a list of IPs for advertisement
        if options.deaggregate_networks:
            options.ips = [ip_network(ip) for net in options.ips for ip in net]

        options.ips = collections.deque(options.ips)
        options.ips.rotate(-options.start_ip)
        options.ips = list(options.ips)
        # Main loop
        loop(options)
    except Exception as e:  # pylint: disable=W0703
        logger.exception("Uncaught exception: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
