---
categories: ["blog"]
date: "2017-02-14T00:00:00Z"
tags: ["freebsd"]
title: Configuration Time
---

Hi there,

Taking over where i left before, so now i do have a fresh and shiny new machine, time to set it up.

# The Base System #

FreeBSD contrarious to linux system is separated into two main part, the main part is the "base system", basically it's what FreeBSD is, and is released and updated as a whole.

To keep the base system up to date we need to use the *freebsd-update* utility.

{{< highlight shell >}}
root@frb:~ # freebsd-update fetch
root@frb:~ # freebsd-update install
{{< / highlight >}}

# Additional Software #

Contrary to Linux Distributions, at least thoses like debian, freebsd by itself is relatively small. But there is a huge collection of additionnal software available in two differents forms, the *port* system, and the *pkg* repository. The *port* system is basicaly a collection of build process to build software from source with all required dependencies and integrate it on the freebsd system. The *pkg* repository is a binary form distribution, which also take care of dependency handling.

The choice is yours, *ports* allow for fine tuning build options, while *pkg* packages can be provided with a few 'flavors' but there is a limited choice.

*pkg* must be bootstrapped by running it first:

{{< highlight shell >}}
root@frb:~ # pkg
The package management tool is not yet installed on your system.
Do you want to fetch and install it now? [y/N]: y
Bootstrapping pkg from pkg+http://pkg.FreeBSD.org/FreeBSD:11:amd64/quarterly, please wait...
Verifying signature with trusted certificate pkg.freebsd.org.2013102301... done
[frb] Installing pkg-1.9.4_1...
[frb] Extracting pkg-1.9.4_1: 100%
pkg: not enough arguments
Usage: pkg [-v] [-d] [-l] [-N] [-j <jail name or id>|-c <chroot path>|-r <rootdir>] [-C <configuration file>] [-R <repo config dir>] [-o var=value] [-4|-6] <command> [<args>]

For more information on available commands and options see 'pkg help'.
{{< / highlight >}}

Then we can use the install method to start adding some value to the base system:

{{< highlight shell >}}
root@frb:~ # pkg install zsh bash
Updating FreeBSD repository catalogue...
[frb] Fetching meta.txz: 100%    944 B   0.9kB/s    00:01
[frb] Fetching packagesite.txz: 100%    6 MiB   5.9MB/s    00:01
Processing entries: 100%
FreeBSD repository update completed. 25857 packages processed.
Updating database digests format: 100%
The following 4 package(s) will be affected (of 0 checked):

New packages to be INSTALLED:
        zsh: 5.3.1
        bash: 4.4.12
        indexinfo: 0.2.6
        gettext-runtime: 0.19.8.1_1

Number of packages to be installed: 4

The process will require 24 MiB more space.
5 MiB to be downloaded.

Proceed with this action? [y/N]: y
[frb] Fetching zsh-5.3.1.txz: 100%    4 MiB   4.1MB/s    00:01
[frb] Fetching bash-4.4.12.txz: 100%    1 MiB   1.5MB/s    00:01
[frb] Fetching indexinfo-0.2.6.txz: 100%    5 KiB   5.3kB/s    00:01
[frb] Fetching gettext-runtime-0.19.8.1_1.txz: 100%  147 KiB 151.0kB/s    00:01
Checking integrity... done (0 conflicting)
[frb] [1/4] Installing indexinfo-0.2.6...
[frb] [1/4] Extracting indexinfo-0.2.6: 100%
[frb] [2/4] Installing gettext-runtime-0.19.8.1_1...
[frb] [2/4] Extracting gettext-runtime-0.19.8.1_1: 100%
[frb] [3/4] Installing zsh-5.3.1...
[frb] [3/4] Extracting zsh-5.3.1: 100%
[frb] [4/4] Installing bash-4.4.12...
[frb] [4/4] Extracting bash-4.4.12: 100%
Message from zsh-5.3.1:
==========================================================

By default, zsh looks for system-wide defaults in
/usr/local/etc.

If you previously set up /etc/zprofile, /etc/zshenv, etc.,
either move them to /usr/local/etc or rebuild zsh with the
ETCDIR option enabled.

==========================================================
Message from bash-4.4.12:
======================================================================

bash requires fdescfs(5) mounted on /dev/fd

If you have not done it yet, please do the following:

        mount -t fdescfs fdesc /dev/fd

To make it permanent, you need the following lines in /etc/fstab:

        fdesc   /dev/fd         fdescfs         rw      0       0

======================================================================
{{< / highlight >}}

There is a small set of useful software i installed of the system:
* shells:
  * zsh
  * bash
* utilities:
  * screen
  * tshark
  * vim-lite
  * mtr-nox11
  * curl
  * bind-tools (dig)

* Remote management:
  * mosh
  * sshguard-pf (mollyguard alternative)


# Configuration #

## Services ##

Everything goes in */etc/rc.conf*, either by editing it directly, or by using the 'sysrc' utility.

Default values are available in */etc/defaults/rc.conf*.

### Mail ###

FreeBSD ship with sendmail as default mail solution. To replace it we need first to disable it with:

{{< highlight shell >}}
root@frb:~ # sysrc sendmail_enable="NONE"
{{< / highlight >}}

We also need to disable sendmail related periodic traitements, for that it is necessary to create */etc/periodic.conf* if it doesn't exist and add the following:

    # disable sendmail task
    daily_clean_hoststat_enable="NO"
    daily_status_mail_rejects_enable="NO"
    daily_status_include_submit_mailq="NO"
    daily_submit_queuerun="NO"

And last but not least, i'm sorry but we need to install a replacement for sendmail, that's not an options ^^ :

{{< highlight shell >}}
root@frb:~ # pkg install postfix
{{< / highlight >}}

## Charset ##

Editing */etc/login.conf* to add

    ...
    :charset=UTF-8:\
    :lang=en_US.UTF-8:\
    ...

And then rebuild the database with:

{{< highlight shell >}}
root@frb:~ # cap_mkdb /etc/login.conf
{{< / highlight >}}

## IPv6 ##

FreeBSD support natively IPv6 networking, however online IP allocation system require a special setup. I used <http://barfooze.de/stuff/online_ipv6.txt> as reference / starting point.

Start by installing dhcp6c from the ports collection / pkg repository:

{{< highlight shell >}}
root@frb:~ # pkg install dhcp6c
{{< / highlight >}}

Build the duid file using this syntax:

{{< highlight shell >}}
root@frb:~ # echo 00:03:XX:XX:... | awk '{ gsub(":"," "); printf "0: 0a 00 %s\n", $0 }' | xxd -r > /var/db/dhcp6c_duid
{{< / highlight >}}

And configure dhcp6c:

    interface bge0 {
        send ia-pd 0;
        send ia-na 0;
    };

    id-assoc na {
    };

    id-assoc pd {
        prefix-interface bge0 {
        };
    };

You also might need to set some interface related option using rc.conf:

    ifconfig_bge0_ipv6="inet6 accept_rtadv"
    ifconfig_bge1_ipv6="inet6 -accept_rtadv"
    dhcp6c_enable="YES"
    dhcp6c_interfaces="bge0"

Next start the dhcp daemon:
{{< highlight shell >}}
root@frb:~ # service dhcp6c start
{{< / highlight >}}

You can also start it in a debug mode prior to using the service, to check that everything is ok:
{{< highlight shell >}}
root@frb:~ # dhcp6c -Df -c /usr/local/etc/dhcp6c.conf bge0
{{< / highlight >}}

Also you will need to activate the router solicitation daemon to trigger RS (Router Sollicitation) request and process RA (Router Annoncement) replies.
Add the following to your *rc.conf* file:

    rtsold_enable="YES"
    rtsold_flags="bge0"

And then start the daemon:

{{< highlight shell >}}
root@frb:~ # service rtsold start
{{< / highlight >}}

It's then easy to add a static IPv6 to the public interface and a IPv6 network on the loopback for the jails by adding the following to *rc.conf*:

    ifconfig_bge0_ipv6_alias0="inet6 alias 2001:bc8:2909:100:::dead:beef prefixlen 128"
    ifconfig_lo1_ipv6="inet6 2001:bc8:2909:101:0:0:0:1/64"
