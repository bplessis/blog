---
date: "2017-10-30T00:00:00Z"
tags: [ "freebsd", "backup" ]
title: Drive Failure and reinstall
---

Hi,

This weekend was one of thoses weekend ... Sunday morning while trying to destroy an unused jail i got a zfs warning: "pool is degraded".

As it turn out i was missing a drive in my zfs mirror setup, so heck .. no fun.

After a few email with the hosting company they recommended i migrate over a new server, which is running ok if you're reading this ;).

I needed to make a backup of the old system, not wanting to reinstall everything from scratch, i dig a bit and made two "files" from the original server:

1/ a backup of the geometry:

{{< highlight shell >}}
root@frb:~# gpart backup ada0 > /var/tmp/backup.geom
{{< / highlight >}}

which gave me something like that:

{{< highlight shell >}}
  GPT 152
  1   freebsd-boot         40       1024
  2   freebsd-swap       2048    4194304 swap0
  3   freebsd-zfs    4196352 1949327360 zfs0
{{< / highlight >}}

2/ a backup of the filesystem:

{{< highlight shell >}}
root@frb:~# zfs snapshot -r zroot@sunday_20171029
root@frb:~# zfs send -R zroot@sunday_20171029 > /var/tmp/backup.zfs
{{< / highlight >}}

And voila ! i just had to put this two file over an ftp server.

(well actually the first time i tried using the -D option of zfs send to further shrink the stream, as it turn out it wasn't a great idea, the recv method didn't like it).

The new serveur was made available at around 20:00 sunday evening, thanks to some limitation in the cloud tools provided i had to start an automated pre-scripted install before being able to "hack over" the hardware. So i did started the process just before going over to the movie (latest Blade Runner, fine by the way but so slow ... ).

So after the movie, the server was up and running and i only had to ... reboot it in rescue mode. The rescue mode is a PXE-booted environment that come in multiple "flavor", including three FreeBSD version, that allow an ssh acces and will allow the reset everything easily.

When the freebsd/rescue is booted /tmp is mounted as a tmpfs, lucky me the memory available on the server is greated that the size of the zfs backup stream so i downloaded everything over it.

The drives where re-partitionned using:

{{< highlight shell >}}
root@frb:~# gpart restore -F -l ada0 < backup.geom
root@frb:~# gpart restore -F ada1 < backup.geom
root@frb:~# gpart modify -i 2 -l swap1 ada1
root@frb:~# gpart modify -i 3 -l zfs1 ada1
{{< / highlight >}}

Boot code was installed using:

{{< highlight shell >}}
root@frb:~# gpart bootcode -b /boot/pmbr -p /boot/gptzfsboot -i 1 ada0
root@frb:~# gpart bootcode -b /boot/pmbr -p /boot/gptzfsboot -i 1 ada1
{{< / highlight >}}

Apparently the swap took care of itself ;)

The *only* thing left was .. the file system, this get a bit tricky and it took quite a bit to get it done right but the process should be only:

{{< highlight shell >}}
root@frb:~# zpool create zroot mirror gpt/zfs0 gpt/zfs1
root@frb:~# zfs recv zroot < backup.zfs
root@frb:~# zpool set bootfs=zroot/ROOT/default zroot
{{< / highlight >}}

If, like me, you had to restart the server in rescue mode because the first boot didn't get you there, there is a few interesting command to consider:

{{< highlight shell >}}
root@frb:~# zpool import -R /mnt zroot
root@frb:~# mount -t zfs zroot/ROOT/default /altroot
{{< / highlight >}}

anyway, short things short the new server was up and running after only a 15 minutes service interruption !
