---
date: "2020-02-11T00:00:00Z"
title:  Setting up an HA LoadBalancer with haproxy 2.x and exabgp 4.x
tags: ["linux","haproxy","exabgp","bgp","ha","dataplaneapi","debian","buster"]
---

A few time ago i started a project of replacing our proprietary load-balancing solution. As i already previously used haproxy for the task i leaned over re-using this formidable software.
However i did not wanted to use VRRP for HA-ing the lot, so there is the story of how i did this.

# Schema

Here is a quick schematic depicting the final configuration:

![Global Schematic](/assets/files/2020/02/global_schematic.png)

# Setting up HAProxy

First things first, you'll need to add haproxy (at least 2.0 to use the included process manager to handle the dataplaneapi).

I used the almost official [Debian/Ubuntu HAProxy packages](https://haproxy.debian.net) page to add a recent enough haproxy onto buster.

Configuration of haproxy is not really in the context of this article, but some points shown below need special care, a full configuration example is available [here](/assets/files/2020/02/haproxy.cfg).

## Setting up the DataplaneAPI

The idea is to have as little configuration redundancy as possible, so in order for exabgp to publish services IP we will need to extract them one way or another. The solution that caught my eye was the newly open-sourced DataPlaneAPI module for haproxy (originaly limited to HAProxy Enterprise). This tool handle configuration parsing and publishing over a REST service.

You can download dataplaneapi from [HAProxy Tech GitHub](https://github.com/haproxytech/dataplaneapi)

Once the binary stored on you server, you'll need to add two configurations blocks in your haproxy.cfg, one /userlist/ for controlling access to the API and one /program/ for starting the module:

{{< highlight shell >}}
userlist controller
  user dataplaneapi insecure-password <set a password>

program api
  command /usr/local/bin/dataplaneapi --host 127.0.0.1 --port 5555 --haproxy-bin /usr/sbin/haproxy --config-file /etc/haproxy/haproxy.cfg --reload-cmd "systemctl reload haproxy" --reload-delay 5 --userlist controller
{{< / highlight >}}


## Setting up frontends with monitoring

You'll also need to publish an healthcheck url on your frontends, like that

{{< highlight shell >}}
frontend _frontend_ex1
  mode http
  bind 192.0.2.30:80
  [...]
  monitor-uri /_healthcheck
  monitor-net 127.0.0.0/8
{{< / highlight >}}

## Service IP

There is a little catch in this setup, service IP won't be dynamically added to one of the network interface, so you'll need to add thoses IP(s) to the loopback interface. I real life scenario the full setup is deployed by a confmgmt service (opscode-chef) but you might want to add the addresses in the network scripts for them to be up on boot.

{{< highlight shell >}}
root@localhost# ip addr add 192.0.2.30/32 dev lo
{{< / highlight >}}

# Setting up HA/exabgp

Now that the service is avaible, time to make it highly !

For this part we will be using [Exabgp 4.0+](https://github.com/Exa-Networks/exabgp), I used debian/buster package without issues, your mileage may vary.

The idea is to make BGP session with your core BGP platform to publish /32 routes for each frontend, for this you'll need BGP-aware router (duh) and a BGP-aware speaker on your server (this will be exabgp's role).

## Configuration exabgp.conf

{{< highlight shell >}}
process watch-haproxy {
    run /usr/bin/python3 /usr/local/sbin/healthcheck-haproxy.py -s --api-password <set a password> --cmd "curl --fail --verbose --max-time 2 http://%s/_healthcheck";
    encoder text;
}
template {
    neighbor core-bgp {
        router-id 192.0.2.5;
        local-address 192.0.2.5;
        local-as 65512;
        peer-as 65530;
        family {
        	ipv4 unicast;
        }
        api services {
            processes [ watch-haproxy ];
        }
    }
}

neighbor 192.0.2.2 {
    inherit core-bgp;
    description "r-1";
}
neighbor 192.0.2.3 {
    inherit core-bgp;
    description "r-2";
}
{{< / highlight >}}

PS: This is more of a manual optimized configuration, when deploying with configuration management I ended with a ["flattened"](/assets/files/2020/02/exabgp.conf) configuration.

## Configuration BGP Router

This part will highly depend on your network's technology, you'll need to setup eBGP links with your LB hosts, I also added a few safeguard with an empty export policy (exabgp doesn't need info from the routing in my configuration) and an import policy that allow only /32 routes over my network:

{{< highlight shell >}}
set protocols bgp group lb type external
set protocols bgp group lb import bgp_filter_exabgp
set protocols bgp group lb export bgp_export_none
set protocols bgp group lb peer-as 65512
set protocols bgp group lb neighbor 192.0.2.5
set protocols bgp group lb neighbor 192.0.2.6

set policy-options policy-statement bgp_export_none term 1 then reject
set policy-options policy-statement bgp_filter_exabgp term 1 from route-filter 192.0.2.0/24 prefix-length-range /32-/32 accept
set policy-options policy-statement bgp_filter_exabgp term 10 then reject
{{< / highlight >}}

## Service

The default systemd unit for exabgp/debian is a bit limited so I added some override to create the fifo used to interrogate the daemon from CLI.

{{< highlight shell >}}
[Service]
User=exabgp
Group=exabgp
RuntimeDirectory=exabgp
RuntimeDirectoryMode=2750
ExecStartPre=-/usr/bin/mkfifo /run/exabgp/exabgp.in /run/exabgp/exabgp.out
{{< / highlight >}}

## Agent

Last but not least we will need an agent for exabgp, he will extract the services IPs from the dataplaneapi and do some healthcheck before publishing an IP.

[Haproxy / DataplaneAPI healthcheck Agent](/assets/files/2020/02/healthcheck-haproxy.py)

The agent will query haproxy dataplane to extract service IPs, and then tests them using the argument provided check, if everything is ok then a route will be sent over the bgp routers using exabgp.

This agent is a modified version of exabgp healthcheck.py, more for the fun of it since the original IP discovery using loopback listing could very well do the trick, however there is another modification, the healthcheck command is applied to each service IP and not once globally, so that we only advertise really enabled services.

# Starting the monster

Time to start the lot, first haproxy and then exabgp:

{{< highlight shell >}}
[root@lb1:~]# systemctl haproxy start
[root@lb1:~]# systemctl status haproxy 
● haproxy.service - HAProxy Load Balancer
   Loaded: loaded (/etc/systemd/system/haproxy.service; enabled; vendor preset: enabled)
   Active: active (running) since Sat 2020-04-11 23:52:51 CEST; 1s ago
     Docs: file:/usr/share/doc/haproxy/configuration.txt.gz
  Process: 96115 ExecStartPre=/usr/sbin/haproxy -f $CONFIG -c -q (code=exited, status=0/SUCCESS)
 Main PID: 96117 (haproxy)
    Tasks: 13 (limit: 2322)
   Memory: 42.6M
   CGroup: /system.slice/haproxy.service
           ├─96117 /usr/sbin/haproxy -Ws -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid
           ├─96122 /usr/local/bin/dataplaneapi --host 0.0.0.0 --port 5555 --haproxy-bin /usr/sbin/haproxy --config-file /etc/haproxy/haproxy.cfg --reload-cmd systemctl reload haproxy --reload-delay 5 --userlist controller
           └─96123 /usr/sbin/haproxy -Ws -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid

Apr 11 23:52:51 lb1 haproxy[96117]: Proxy xxx started.
Apr 11 23:52:51 lb1 haproxy[96117]: Proxy xxy started.
Apr 11 23:52:51 lb1 haproxy[96117]: Proxy stats started.
Apr 11 23:52:51 lb1 haproxy[96117]: [NOTICE] 101/235251 (96117) : New program 'api' (96122) forked
Apr 11 23:52:51 lb1 haproxy[96117]: [NOTICE] 101/235251 (96117) : New worker #1 (96123) forked
[root@lb1:~]# systemctl start exabgp
[root@lb1:~]# systemctl status exabgp 
● exabgp.service - ExaBGP
   Loaded: loaded (/etc/systemd/system/exabgp.service; enabled; vendor preset: enabled)
   Active: active (running) since Sat 2020-04-11 23:54:42 CEST; 1s ago
     Docs: https://github.com/Exa-Networks/exabgp/wiki
  Process: 96222 ExecStartPre=/usr/bin/mkfifo /run/exabgp/exabgp.in /run/exabgp/exabgp.out (code=exited, status=0/SUCCESS)
 Main PID: 96223 (exabgp)
    Tasks: 3 (limit: 2322)
   Memory: 55.6M
   CGroup: /system.slice/exabgp.service
           ├─96223 /usr/bin/python3 /usr/sbin/exabgp /etc/exabgp/exabgp.conf
           ├─96230 /usr/bin/python3 /usr/local/sbin/healthcheck-haproxy.py -s --api-password <set a password> --cmd curl --fail --verbose --max-time 2 http://%s/_healthcheck
           └─96231 /usr/bin/python3 /usr/sbin/exabgp

Apr 11 23:54:43 lb1 exabgp[96223]: 23:54:43 | 96223  | interpreter     | 3.7.3 (default, Dec 20 2019, 18:57:59)  [GCC 8.3.0]
Apr 11 23:54:43 lb1 exabgp[96223]: 23:54:43 | 96223  | os              | Linux lb1 4.19.0-8-amd64 #1 SMP Debian 4.19.98-1 (2020-01-26) x86_64
Apr 11 23:54:43 lb1 exabgp[96223]: 23:54:43 | 96223  | installation    |
Apr 11 23:54:43 lb1 exabgp[96223]: 23:54:43 | 96223  | cli control     | named pipes for the cli are:
Apr 11 23:54:43 lb1 exabgp[96223]: 23:54:43 | 96223  | cli control     | to send commands  /run/exabgp/exabgp.in
Apr 11 23:54:43 lb1 exabgp[96223]: 23:54:43 | 96223  | cli control     | to read responses /run/exabgp/exabgp.out
Apr 11 23:54:43 lb1 exabgp[96223]: 23:54:43 | 96223  | configuration   | performing reload of exabgp 4.0.8-793a2931
Apr 11 23:54:43 lb1 exabgp[96223]: 23:54:43 | 96223  | reactor         | loaded new configuration successfully
Apr 11 23:54:43 lb1 exabgp[96223]: 23:54:43 | 96223  | reactor         | connected to peer-2 with outgoing-1 192.0.5-192.0.2.2
Apr 11 23:54:43 lb1 exabgp[96223]: 23:54:43 | 96223  | reactor         | connected to peer-1 with outgoing-2 192.0.5-192.0.2.2
{{< / highlight >}}
