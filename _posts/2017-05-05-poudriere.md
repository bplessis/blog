---
layout: post
title:  "Poudriere"
categories: freebsd
---

In some cases you might need to use some customisation over the standard pre-built packages repository. Two choices there: you can either manually build them using the *ports* system on each of your jails/servers, or you can make a custom pkg repository with your build options.

This is what i will show here, using the *poudriere* build system, a creation by the same author of *pkg*, [bapt][bapt-home], a good guy (yes yes ;) ) who has coped with me during many FreeBSD rants (well he wasn't the only one, thanks [Keltia][keltia-home] , nerzhul, renchap and others for your precious help).

## Setup & configuration

As usual we start with installing the pkg:

{% highlight shell %}
root@frb:~# pkg install poudriere
{% endhighlight %}

First step will be, strangely enough ;) , customisation of the configuration file:

{% highlight shell %}
# Poudriere can make use of ZFS, so we tell him where he should work
ZPOOL=zroot
ZROOTFS=/poudriere
# Recommanded
FREEBSD_HOST=https://download.FreeBSD.org
RESOLV_CONF=/usr/jails/flavours/mine/etc/resolv.conf

# The directory where poudriere will store jails and ports
BASEFS=/usr/local/poudriere
{% endhighlight %}

## Build Jail

Next step is to setup a build jail, every thing is automated, you only need to provide a name and a version:

{% highlight shell %}
root@frb:~# poudriere jail -c -j FreeBSD:11amd64 -v 11.0-RELEASE
[00:00:00] ====>> Creating FreeBSD:11amd64 fs... done
[00:00:01] ====>> Using pre-distributed MANIFEST for FreeBSD 11.0-RELEASE amd64
[00:00:01] ====>> Fetching base.txz for FreeBSD 11.0-RELEASE amd64
/usr/local/poudriere/jails/FreeBSD:11amd64/fro100% of   91 MB   44 MBps 00m02s
[00:00:03] ====>> Extracting base.txz... done
[00:00:13] ====>> Fetching src.txz for FreeBSD 11.0-RELEASE amd64
/usr/local/poudriere/jails/FreeBSD:11amd64/fro100% of  133 MB   44 MBps 00m03s
[00:00:16] ====>> Extracting src.txz... done
[00:00:33] ====>> Fetching lib32.txz for FreeBSD 11.0-RELEASE amd64
/usr/local/poudriere/jails/FreeBSD:11amd64/fro100% of   17 MB   20 MBps 00m01s
[00:00:34] ====>> Extracting lib32.txz... done
[00:00:36] ====>> Cleaning up... done
[00:00:36] ====>> Recording filesystem state for clean... done
[00:00:36] ====>> Upgrading using ftp
/usr/jails/flavours/mine/etc/resolv.conf -> /usr/local/poudriere/jails/FreeBSD:11amd64/etc/resolv.conf
mount: /usr/local/poudriere/jails/FreeBSD:11amd64/compat: No such file or directory
Looking up update.FreeBSD.org mirrors... 4 mirrors found.
Fetching public key from update6.freebsd.org... done.
Fetching metadata signature for 11.0-RELEASE from update6.freebsd.org... done.
Fetching metadata index... done.
Fetching 2 metadata files... done.
Inspecting system... done.
Preparing to download files... done.
Fetching 1782 patches.....10....20....30....40....50....60....70....80....90....100....110....120....130....140....150....160....170....180....190....200....210....220....230....240....250....260....270....280....290....300....310....320.
...330....340....350....360....370....380....390....400....410....420....430....440....450....460....470....480....490....500....510....520....530....540....550....560....570....580....590....600....610....620....630....640....650....660.
...670....680....690....700....710....720....730....740....750....760....770....780....790....800....810....820....830....840....850....860....870....880....890....900....910....920....930....940....950....960....970....980....990....1000
....1010....1020....1030....1040....1050....1060....1070....1080....1090....1100....1110....1120....1130....1140....1150....1160....1170....1180....1190....1200....1210....1220....1230....1240....1250....1260....1270....1280....1290....13
00....1310....1320....1330....1340....1350....1360....1370....1380....1390....1400....1410....1420....1430....1440....1450....1460....1470....1480....1490....1500....1510....1520....1530....1540....1550....1560....1570....1580....1590....
1600....1610....1620....1630....1640....1650....1660....1670....1680....1690....1700....1710....1720....1730....1740....1750....1760....1770....1780. done.
Applying patches... done.
Fetching 22 files... done.

The following files will be removed as part of updating to 11.0-RELEASE-p10:
/usr/share/zoneinfo/America/Santa_Isabel
/usr/share/zoneinfo/Asia/Rangoon
/usr/src/contrib/ntp/compile
/usr/src/contrib/ntp/config.guess
/usr/src/contrib/ntp/config.sub
...
/usr/src/usr.sbin/ntp/doc/ntpq.8
/usr/src/usr.sbin/ntp/doc/sntp.8
/usr/src/usr.sbin/ntp/libntp/Makefile
/usr/src/usr.sbin/ntp/scripts/mkver
Installing updates... done.
FreeBSD:11amd64-default: removed
FreeBSD:11amd64-default-n: removed
11.0-RELEASE-p10
[00:01:39] ====>> Recording filesystem state for clean... done
[00:01:39] ====>> Jail FreeBSD:11amd64 11.0-RELEASE amd64 is ready to be used
{% endhighlight %}

For subsequent update:
{% highlight shell %}
root@frb:~# poudriere jail -u -j FreeBSD:11amd64
{% endhighlight %}
will be enough.

## Port Tree


And setup/update a port tree (a collection of package "build rules"):
{% highlight shell %}
root@frb:~# poudriere ports -c
[00:00:00] ====>> Creating default fs... done
[00:00:01] ====>> Extracting portstree "default"...
Looking up portsnap.FreeBSD.org mirrors... 6 mirrors found.
Fetching public key from ec2-eu-west-1.portsnap.freebsd.org... done.
Fetching snapshot tag from ec2-eu-west-1.portsnap.freebsd.org... done.
Fetching snapshot metadata... done.
Fetching snapshot generated at Fri May  5 02:07:51 CEST 2017:
25b9a390c7dac576abba7fa6df9fc984186f6456475710100% of   75 MB   26 MBps 00m03s
Extracting snapshot... done.
...
/usr/local/poudriere/ports/default/x11/yalias/
/usr/local/poudriere/ports/default/x11/yeahconsole/
/usr/local/poudriere/ports/default/x11/yelp/
/usr/local/poudriere/ports/default/x11/zenity/
Building new INDEX files... done.
{% endhighlight %}

For updating:
{% highlight shell %}
root@frb:~# poudriere ports -u
{% endhighlight %}

## Package list & configuration

You will then have to decide what should be rebuilt, and how, for that you'll need to setup some generic build rules within a 'make.conf' file:
{% highlight shell %}
root@frb:# cat FreeBSD:11amd64-make.conf
DEFAULT_PHP_VER?=       71
{% endhighlight %}

And a list of packages to be built:
{% highlight shell %}
root@frb:# cat FreeBSD:11amd64-pkglist
devel/pecl-APCu
{% endhighlight %}

And lastly you should setup per-package options for all the listed package and thers build-dependencies:
{% highlight shell %}
root@frb:~# poudriere options -j FreeBSD:11amd64 -f FreeBSD:11amd64-pkglist
{% endhighlight %}

# Building

Yes, now we can rebuilt all thoses pesky packages, with a simple command line:
{% highlight shell %}
root@frb:~# poudriere bulk -j FreeBSD:11amd64 -f FreeBSD:11amd64-pkglist
[00:00:00] ====>> Creating the reference jail... done
[00:00:00] ====>> Mounting system devices for FreeBSD:11amd64-default
[00:00:00] ====>> Mounting ports/packages/distfiles
[00:00:00] ====>> Converting package repository to new format
[00:00:00] ====>> Stashing existing package repository
[00:00:00] ====>> Mounting packages from: /usr/local/poudriere/data/packages/FreeBSD:11amd64-default
[00:00:00] ====>> Copying /var/db/ports from: /usr/local/etc/poudriere.d/FreeBSD:11amd64-options
[00:00:00] ====>> Appending to make.conf: /usr/local/etc/poudriere.d/FreeBSD:11amd64-make.conf
/usr/jails/flavours/mine/etc/resolv.conf -> /usr/local/poudriere/data/.m/FreeBSD:11amd64-default/ref/etc/resolv.conf
[00:00:00] ====>> Starting jail FreeBSD:11amd64-default
[00:00:01] ====>> Logs: /usr/local/poudriere/data/logs/bulk/FreeBSD:11amd64-default/2017-05-05_13h00m34s
[00:00:01] ====>> Loading MOVED
[00:00:01] ====>> Calculating ports order and dependencies
[00:00:01] ====>> pkg package missing, skipping sanity
[00:00:01] ====>> Skipping incremental rebuild and repository sanity checks
[00:00:01] ====>> Cleaning the build queue
[00:00:01] ====>> Recording filesystem state for prepkg... done
[00:00:02] ====>> Building 17 packages using 8 builders
[00:00:02] ====>> Starting/Cloning builders
[00:00:02] ====>> Hit CTRL+t at any time to see build progress and stats
...
Creating repository in /tmp/packages: 100%
Packing files for repository: 100%
[00:08:00] ====>> Committing packages to repository
[00:08:00] ====>> Removing old packages
[00:08:00] ====>> Built ports: ports-mgmt/pkg devel/autoconf-wrapper print/indexinfo devel/pkgconf devel/gettext-runtime devel/pcre devel/gettext-tools devel/gmake textproc/libxml2 lang/perl5.24 devel/p5-Locale-gettext misc/help2man print/texinfo devel/m4 devel/autoconf lang/php71 devel/pecl-APCu
[FreeBSD:11amd64-default] [2017-05-05_13h00m34s] [committing:] Queued: 17 Built: 17 Failed: 0  Skipped: 0  Ignored: 0  Tobuild: 0   Time: 00:07:59
[00:08:00] ====>> Logs: /usr/local/poudriere/data/logs/bulk/FreeBSD:11amd64-default/2017-05-05_13h00m34s
[00:08:00] ====>> Cleaning up
FreeBSD:11amd64-default: removed
FreeBSD:11amd64-default-n: removed
[00:08:00] ====>> Unmounting file systems
{% endhighlight %}

# Sharing

Ok then now there is the simple question of sharing thoses new shiny packages with all your hosts/jails. Since i don't have multiple FreeBSD hosts i will use a really simple way for this: the package directory will be null-mounted (read 'bind-ed' for all you linux users) on the jails using the fstab.<jailname> file.

{% highlight shell %}
root@frb:~# cat /etc/fstab.ns3_plessis_info
/usr/jails/basejail /usr/jails/ns3.plessis.info/basejail nullfs ro 0 0
{% endhighlight %}

And in the jail you need to add the repository with a simple definition:
{% highlight shell %}
root@ns3:~# cat /usr/local/etc/pkg/repos/local.conf
local: {
    url: "file:///usr/local/poudriere/data/packages/FreeBSD:11amd64-default",
    priority: 100,
    enabled: yes
}
{% endhighlight %}

# Updating the builds

{% highlight shell %}
root@frb:~# /usr/local/bin/poudriere jail -u -j FreeBSD:11amd64
root@frb:~# /usr/local/bin/poudriere ports -u -p default && /usr/local/bin/poudriere bulk -f /usr/local/etc/poudriere.d/FreeBSD:11amd64-pkglist -j FreeBSD:11amd64 -p default
{% endhighlight %}


[keltia-home]: https://www.keltia.net/
[bapt-home]: http://blog.etoilebsd.net/
