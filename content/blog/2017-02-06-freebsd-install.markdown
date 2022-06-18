---
date: "2017-02-06T22:40:00Z"
tags: [ "freebsd" ]
title: Installation Time
slug: freebsd install
---

Hi there,

Taking over where i left before, so now i do have a fresh and shiny new machine, time to set it up.

As previously stated, the intended OS for this gig is FreeBSD, so there i am, discovering the [Online Administration Console][online-console], trying to figure out what to do with this stuff.

Has it happens, there are a few installation procedures availables "out-of-the-box", letting you setup your server within the web console, for a bunch of OS, including FreeBSD, but - yeah there is always a but - the FreeBSD 11 install procedure only support the [UFS][freebsd-ufs] filesystem. I wanted to experiment all the fuss about [ZFS][freebsd-zfs] so this wasn't good enough for me !

The only way forward was to install the server using some kind of remote admin system, luckily the server is a dell-based one, including the entreprise version of dell's handoff service: iDRAC, unluckily for me the iDRAC access wasn't available initially ... After a few search it appeared to me that i needed to install the server once using one of the automated and integrated procedure of the administrative console, to unlock the iDRAC access option.

So there we are, setting up a stub freebsd over UFS just for the sake of it, and waiting one hour for the installation procedure to finish.

Once this mandatory, but un-necessary step is done, the iDRAC console access is cleared and you are free to do whatever you want with your box. You only have to know the path to [Online Virtual Media Database][online-virtualmedia] ! Here you'll find all you need to 'plug-in' a whole lot of install media, including FreeBSD, and install you server the way you want it !

This is quite standard, a few text-based question later and i got a new OS, on a ZFS mirror setup !

```pre
Copyright (c) 1992-2016 The FreeBSD Project.
Copyright (c) 1979, 1980, 1983, 1986, 1988, 1989, 1991, 1992, 1993, 1994
        The Regents of the University of California. All rights reserved.
FreeBSD is a registered trademark of The FreeBSD Foundation.
FreeBSD 11.0-RELEASE-p2 #0: Mon Oct 24 06:55:27 UTC 2016
    root@amd64-builder.daemonology.net:/usr/obj/usr/src/sys/GENERIC amd64                                                                                                                                                                     FreeBSD clang version 3.8.0 (tags/RELEASE_380/final 262564) (based on LLVM 3.8.0)                                                                                                                                                             VT(vga): resolution 640x480
CPU: Intel(R) Xeon(R) CPU E3-1231 v3 @ 3.40GHz (3392.22-MHz K8-class CPU)
  Origin="GenuineIntel"  Id=0x306c3  Family=0x6  Model=0x3c  Stepping=3
  Features=0xbfebfbff<FPU,VME,DE,PSE,TSC,MSR,PAE,MCE,CX8,APIC,SEP,MTRR,PGE,MCA,CMOV,PAT,PSE36,CLFLUSH,DTS,ACPI,MMX,FXSR,SSE,SSE2,SS,HTT,TM,PBE>
  Features2=0x7ffafbff<SSE3,PCLMULQDQ,DTES64,MON,DS_CPL,VMX,SMX,EST,TM2,SSSE3,SDBG,FMA,CX16,xTPR,PDCM,PCID,SSE4.1,SSE4.2,x2APIC,MOVBE,POPCNT,TSCDLT,AESNI,XSAVE,OSXSAVE,AVX,F16C,RDRAND>
  AMD Features=0x2c100800<SYSCALL,NX,Page1GB,RDTSCP,LM>
  AMD Features2=0x21<LAHF,ABM>
  Structured Extended Features=0x2fbb<FSGSBASE,TSCADJ,BMI1,HLE,AVX2,SMEP,BMI2,ERMS,INVPCID,RTM,NFPUSG>
  XSAVE Features=0x1<XSAVEOPT>
  VT-x: PAT,HLT,MTF,PAUSE,EPT,UG,VPID
  TSC: P-state invariant, performance statistics
real memory  = 34359738368 (32768 MB)
avail memory = 33090113536 (31557 MB)
...
```

{{< highlight shell >}}
root@frb:~ # zfs list
NAME                    USED  AVAIL  REFER  MOUNTPOINT
zroot                  2.37G   897G    96K  /zroot
zroot/ROOT             1.07G   897G    96K  none
zroot/ROOT/default     1.07G   897G  1.07G  /
...
{{< / highlight >}}

Look like we are on track !

[online-virtualmedia]: https://virtualmedia.online.net/
[online-console]: https://console.online.net/
[freebsd-ufs]: https://en.wikipedia.org/wiki/Unix_File_System
[freebsd-zfs]: https://www.freebsd.org/doc/handbook/zfs.html
