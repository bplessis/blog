---
categories: [ "blog" ]
date: "2018-04-22T00:00:00Z"
tags: [ "freebsd", "dhcp", "ipv6" ]
title: FreeBSD DHCPv6
---

In [FreeBSD Setup]({{< ref "2017-02-14-freebsd-setup" >}} "FreeBSD Setup") i detailed the use of KAME's dhcp client to authentify and request an IPv6 block to be routed onto the server.

However as it seem this client has a tendancy to misbehave and trigger the hosting provider DOS defense mechanism (mainly rebooting the serveur after disabling dhcp service autorisations, not fun).

While checking around with friend it seems i wasn't the first one hit by this and that the solution was to switch over to ISC's dhcp service, with a little twist (freebsd package for isc-dhcp doesn't include an init script for dhcpv6).

# Installation 

{{< highlight shell >}}
root@frb:~ # pkg install isc-dhcp44-client
{{< / highlight >}}

However as stated before the package doesn't include a statup script for ipv6 service, so there is one you need to paste into `/usr/local/etc/rc.d/dhclient6` (courtesy of [neuro](https://t37.net)):

{{< highlight shell >}}
#!/bin/sh
#
# PROVIDE: dhclient6
# REQUIRE: DAEMON
# KEYWORD: dhcp
#
# Add the following lines to /etc/rc.conf to enable dhclient6:
#
# dhclient6_enable="YES"
#

. /etc/rc.subr

name="dhclient6"
desc="ISC DHCPv6 client"
rcvar="dhclient6_enable"

start_cmd="dhclient6_start"
stop_cmd="dhclient6_stop"

dhclient6_start()
{
          /usr/local/sbin/dhclient -cf "${dhclient6_conf}" -P -v "${dhclient6_iface}"

}

dhclient6_stop()
{ 
  if [ -r "${dhclient6_pid}" ]
  then
    kill -- -$(cat "${dhclient6_pid}")
    rm -f "${dhclient6_pid}"
  fi
}

load_rc_config ${name}

: ${dhclient6_enable="NO"}
: ${dhclient6_pid="/var/run/dhclient6.pid"}
: ${dhclient6_conf="/usr/local/etc/dhclient6.conf"}
: ${dhclient6_iface=""}

run_rc_command "$1"
{{< / highlight >}}


# Configuration

Configuration is simpler than using KAME's dhcp6c, most notably the DUID doesn't need some magic, only need to write it up in a `dhclient6.conf`:

{{< highlight shell >}}
interface "bge0" {
        send dhcp6.client-id 00:03:xx:xx:xx:xx:xx:xx:xx:xx;
}
{{< / highlight >}}

And activate everything in `rc.conf` like before, there is however one minor diff with previous configuration, i didn't had time to investigate as of why but `dhcp6c` setup did add and ipv6 address to the requesting interface, current `isc-dhcp` does not, so i added an alias:

{{< highlight shell >}}
ifconfig_bge0_ipv6="inet6 -ifdisabled accept_rtadv up"
ifconfig_bge0_aliases="inet6 alias 2001:bc8:2909:xx:y:z prefixlen 128"

#dhcp6c_enable="YES"
#dhcp6c_interfaces="bge0"
dhclient6_iface="bge0"
dhclient6_enable="YES"
{{< / highlight >}}

# Cleanup

When happy with this new setup you can do some cleanup:

{{< highlight shell >}}
root@frb:~ # pkg remove dhcp6
root@frb:~ # /bin/rm /usr/local/etc/dhcp6c.conf /var/db/dhcp6c_duid
{{< / highlight >}}
