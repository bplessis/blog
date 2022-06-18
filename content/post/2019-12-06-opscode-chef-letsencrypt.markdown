---
layout: post
date: "2019-12-06T00:00:00Z"
title:  Let's Encrypt Chef-Server
categories: ["blog"]
tags: ["linux","chef-server","letsencrypt","ssl","dehydrated"]
---

Hi,

So today i wanted to switch our chef-server certificates from an old internal pki with issues (SHA1 ...) to another solution, and since we are avid users of Let's Encrypt this was my first idea.

However i quickly stumble onto an issue, the chef-server private cookbook aren't 'compatible' with this (ie there is no way to insert some custom nginx rules on the correct location to allow serving of /.well-known/acme-challenge/) ...

So i had to be creative, and the first idea is: *put an nginx in front of chef's nginx on port 80*, and there is how i did it:

# Setting up the webproxy

So, first things first, we have to tell chef to free our beloved port 80 for our internal use, we start by editing '/etc/opscode/chef-server.rb' to add/modify the non_ssl_port attribute:

{{< highlight shell >}}
nginx['non_ssl_port'] = 8080
{{< / highlight >}}

And then we can trigger chef-server reconfiguration:
{{< highlight shell >}}
root@chef:~ # chef-server-ctl reconfigure
{{< / highlight >}}

After that's done, we can install and set-up nginx on the linux host, here is the ubuntu/debian way but i'm sure you can adapt to your liking:

{{< highlight shell >}}
root@chef:~ # apt install nginx
root@chef:~ # cat > /etc/nginx/sites-available/chef-server-le <<EOF

upstream opscode_chef {
	server 127.0.0.1:8080;
}

server {
	listen 80 default_server;
	listen [::]:80 default_server;

	root /var/www/html;

	index index.html index.htm index.nginx-debian.html;

	server_name _;
	
	# Serve well-known file locally
	location /.well-known/ {
		try_files $uri $uri/ =404;
	}

	# Forward everything else to chef-server nginx
	location / {
		include proxy_params;
		proxy_pass http://opscode_chef;
	}
}
EOF
root@chef:~ # ln -s /etc/nginx/sites-available/chef-server-le /etc/nginx/sites-enabled/chef-server-le
root@chef:~ # service nginx restart
{{< / highlight >}}

# Setting up the acme client

I am pretty fond of Lukas Schauer [@lukas2511](https://twitter.com/lukas2511) bash solution [*dehydrated*](https://github.com/lukas2511/dehydrated) so there is how i set it up, it shouldn't be difficult to adapt this to any other acme client:

## Installing dehydrated (my way)
{{< highlight shell >}}
root@chef:~ # git clone https://github.com/lukas2511/dehydrated.git /usr/local/share/dehydrated
root@chef:~ # ln -s /usr/local/share/dehydrated/dehydrated /usr/local/sbin/dehydrated
root@chef:~ # cat > /etc/cron.daily/dehydrated << EOF
#!/bin/bash
#
#
test -x /usr/local/sbin/dehydrated || exit 0
LANGUAGE=C
LC_ALL=C
export LANGUAGE LC_ALL

# If you need a proxy:
#https_proxy=http://proxy:3128
#http_proxy=http://proxy:3128
#ftp_proxy=http://proxy:3128
#export https_proxy http_proxy ftp_proxy

# Load dehydrated configuration
TMPENV=$(mktemp -t dhenvXXX)
/usr/local/sbin/dehydrated --env >> $TMPENV
source $TMPENV

if [ -e "$DOMAINS_TXT" ]; then
    /usr/local/sbin/dehydrated -c -g
fi

/bin/rm $TMPENV

#EOF
EOF
{{< / highlight >}}

And there you go !

## Configuring dehydrated

... Well almost ^^ we still have a bit of setup to do.

So we have three files to create: the global configuration, the domain list and the hook script who will take care of restarting chef-server when needed.

For the global configuration (default path /usr/local/etc/dehydrated/config), i mostly setup the bare minimum: CONTACT_EMAIL for the account creation / mail notifications from LE, WELLKNOWN which is the path that will publish the challenges and HOOK to define our custom-made scripts, exemple:

{{< highlight shell >}}
root@chef:~ # cat > /usr/local/etc/dehydrated/config << EOF
CONTACT_EMAIL=ssl@xxx.com
WELLKNOWN=/var/www/html/.well-known/acme-challenge
HOOK=/usr/local/sbin/le-hook.sh
EOF
{{< / highlight >}}

For the ssl domain, if as i did you only need the host name there is an easy way:
{{< highlight shell >}}
root@chef:~ # hostname -f >| /usr/local/etc/dehydrated/domains.txt
{{< / highlight >}}
If not you'll need to fire-up your favorite EDITOR (echo or cat, as you wish ^^) and create '/usr/local/etc/dehydrated/domains.txt'.

And as for the hook script there is a base for you to extend if you want:

{{< highlight shell >}}
root@chef:~ # cat > /usr/local/sbin/le-hook.sh << EOF
#!/usr/bin/env bash

function deploy_challenge {
    local DOMAIN="" TOKEN_FILENAME="" TOKEN_VALUE=""
}

function clean_challenge {
    local DOMAIN="" TOKEN_FILENAME="" TOKEN_VALUE=""
}

function deploy_cert {
    local DOMAIN="" KEYFILE="" CERTFILE="" FULLCHAINFILE="" CHAINFILE="" TIMESTAMP=""
    chef-server-ctl restart
}

function unchanged_cert {
    local DOMAIN="" KEYFILE="" CERTFILE="" FULLCHAINFILE="" CHAINFILE=""
}

invalid_challenge() {
    local DOMAIN="" RESPONSE=""
#    sendmail -t <<MAIL_END
#MAIL_END
}

request_failure() {
    local STATUSCODE="" REASON="" REQTYPE=""
#    sendmail -t <<MAIL_END
#MAIL_END
}

exit_hook() {
  # This hook is called at the end of a dehydrated command and can be used
  # to do some final (cleanup or other) tasks.

  :
}

HANDLER=""; shift
if [[ "" =~ ^(deploy_challenge|clean_challenge|deploy_cert|unchanged_cert|invalid_challenge|request_failure|exit_hook)$ ]]; then
  "" ""
fi
EOF
{{< / highlight >}}

## Certificate generation

Easy enough, you only need to register the account (once) and trigger a first run of dehydrated using "-c":
{{< highlight shell >}}
root@chef:~ # /usr/local/sbin/dehydrated --register --accept-terms
root@chef:~ # /usr/local/sbin/dehydrated -c
{{< / highlight >}}

# Setting up the new certificate for chef-server

Easy enough, fire up this good old $EDITOR onto '/etc/opscode/chef-server.rb' and modify the two ssl_certificate/ssl_certificate_key attributes, exemple:

{{< highlight shell >}}
nginx['ssl_certificate']  = "/usr/local/etc/dehydrated/certs/chef.xxx.com/cert.pem"
nginx['ssl_certificate_key']  = "/usr/local/etc/dehydrated/certs/chef.xxx.com/privkey.pem"
{{< / highlight >}}

And reconfigure chef, which will also restart it:

{{< highlight shell >}}
root@chef:~ # chef-server-ctl reconfigure
{{< / highlight >}}

Et Voila !
