---
categories: bind knot linux freebsd dns dnssec
date: "2017-09-01T00:00:00Z"
draft: true
title: DNSSEC with an heterogenous and dynamic Bind DNS system
---

Hi,

It's been a long time without update so today to change a bit i'll speak about DNSSEC.

My starting setup is quite standard: four dns serveur, two slaves in my control, one generic slave from the registrar and one master. Not all of them use the same software also.

There are many way to setup DNSSEC but in my case the generci slave from Gandi limit the option, i'll need the master serveur to do all the signing and transfer the resulting zone data to the slaves.


mkdir /etc/bind/keys
cd /etc/bind/keys

dnssec-keygen -3 -a RSASHA256 -b 2048 -n ZONE plessis.info
dnssec-keygen -3 -f KSK -a RSASHA256 -b 4096 -n ZONE plessis.info

options {

        dnssec-enable yes;
        dnssec-validation auto;
        dnssec-lookaside auto;
}

zone "plessis.info" IN {
        type master;
        notify yes;

        auto-dnssec maintain;
        dnssec-secure-to-insecure yes;
        key-directory "/etc/bind/keys/";
        inline-signing yes;
}


rndc reconfig

: 1504047989:0;rndc signing -list plessis.info
