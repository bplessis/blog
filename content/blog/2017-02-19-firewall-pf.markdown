---
date: "2017-02-19T00:00:00Z"
tags: [ "freebsd" ]
title: 'Firewalling: PF'
slug: firewall pf
---

So, now we have some basis of a working system.

Time to think about protecting if, while the Internet is the place to be it's also a kind of a bad place, moreover when you're in the middle of a known hosting company.

# Firewalling #

So, we have to play with FreeBSD firewall solution: *PF*, as in *Packet Filter*.

## Configuring ##

So first thing is to setup a few rules in the */etc/pf.conf* file:

    pub="192.0.2.1" # Host public IPv4 address
    pub6="2001:db8:1::1" # Host public IPv6 address

    if="bge0"

    # Rules must be in order: options, normalization, queueing, translation, filtering
    # 1: options

    set block-policy return
    set skip on lo
    scrub in

    table <sshguard> persist

    # 2: Normalization

    # 3: Queueing

    # 4: Translation ?

    # 5 Filtering
    # default outbound
    pass out quick on $if from $pub to any
    pass out quick on $if from $pub6 to any

    # Filter brut-forcer
    block in quick proto tcp from <sshguard>
    block in log on $if

    # ICMP v4/v6
    pass in quick on $if inet proto icmp from any to any
    pass in quick on $if inet6 proto ipv6-icmp from any to any

    # DHCPv6
    pass in quick on $if inet6 proto udp from any to bge0 port 546 keep state

    # ssh/mosh on the host machine
    pass in quick on $if proto tcp from any to $pub port ssh
    pass in quick on $if proto udp from any to $pub port 60000:60100
    pass in quick on $if proto tcp from any to $pub6 port ssh
    pass in quick on $if proto udp from any to $pub6 port 60000:60100

## Starting ##

Then a few line in the */etc/rc.conf* are needed to automatically activate the firewall on start:

    pf_enable="YES"
    pf_rules="/etc/pf.conf"
    pflog_enable="YES"

Then it's just a matter of starting the service as usual.

{{< highlight shell >}}
root@frb:~ # service pf start
root@frb:~ # service pflogd start
{{< / highlight >}}

## Updating ##

Whenever you need to update the pf ruleset, you just have to edit the */etc/pf.conf* file, and then test it:

{{< highlight shell >}}
root@frb:~ # pfctl -nf /etc/pf.conf
{{< / highlight >}}

And update it with:

{{< highlight shell >}}
root@frb:~ # pfctl -f /etc/pf.conf
{{< / highlight >}}

# sshguard #

Having a general firewall is good, it could be usefull to do some automated log analysis and defense. For that you can use the same mollyguard tool as under linux system, or you can use `sshguard` who has an native `pf` integration:

{{< highlight shell >}}
root@frb:~ # pkg install sshguard-pf
Updating FreeBSD repository catalogue...
[test] Fetching meta.txz: 100%    944 B   0.9kB/s    00:01
[test] Fetching packagesite.txz: 100%    6 MiB   5.9MB/s    00:01
Processing entries: 100%
FreeBSD repository update completed. 25860 packages processed.
The following 1 package(s) will be affected (of 0 checked):

New packages to be INSTALLED:
        sshguard-pf: 1.7.0_1

Number of packages to be installed: 1

The process will require 2 MiB more space.
320 KiB to be downloaded.

Proceed with this action? [y/N]: y
[frb] Fetching sshguard-pf-1.7.0_1.txz: 100%  320 KiB 327.7kB/s    00:01
Checking integrity... done (0 conflicting)
[frb] [1/1] Installing sshguard-pf-1.7.0_1...
[frb] [1/1] Extracting sshguard-pf-1.7.0_1: 100%
Message from sshguard-pf-1.7.0_1:
##########################################################################
  Sshguard installed successfully.

  To activate or configure PF see http://www.sshguard.net/docs/setup/firewall/pf/

  You can start sshguard as a daemon by using the
  rc.d script installed at /usr/local/etc/rc.d/sshguard .

  See sshguard(8) and http://www.sshguard.net/docs/setup for additional info.

  Please note that a few rc script parameters have been renamed to
  better reflect the documentation:

  sshguard_safety_thresh -> sshguard_danger_thresh
  sshguard_pardon_min_interval -> sshguard_release_interval
  sshguard_prescribe_interval -> sshguard_reset_interval
##########################################################################
{{< / highlight >}}

Next step is simply activating the service in *rc.conf*, manually or by using `sysrc`:
{{< highlight shell >}}
root@frb:~ # sysrc sshguard_enable="YES"
{{< / highlight >}}

And starting up the service:
{{< highlight shell >}}
root@frb:~ # service sshguard start
{{< / highlight >}}

You can then look for sshguard message in */var/log/message* and inspect the deny table using:
{{< highlight shell >}}
root@frb:~ # pfctl -t sshguard -T show
{{< / highlight >}}

NB setting up a few IPs addresses in */usr/local/etc/sshguard.whitelist* might be a good idea.
