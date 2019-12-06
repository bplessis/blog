---
layout: post
title:  Let's Encrypt Chef-Server
categories: blog
tags: linux chef-server letsencrypt ssl dehydrated
---

Hi,

So today i wanted to switch our chef-server certificates from an old internal pki with issues (SHA1 ...) to another solution, and since we are avid users of Let's Encrypt this was my first idea.

However i quickly stumble onto an issue, the chef-server private cookbook aren't 'compatible' with this (ie there is no way to insert some custom nginx rules on the correct location to allow serving of /.well-known/acme-challenge/) ...

So i had to be creative, and the first idea is: *put an nginx in front of chef's nginx on port 80*, and there is how i did it:

# Setting up the webproxy

So, first things first, we have to tell chef to free our beloved port 80 for our internal use, we start by editing '/etc/opscode/chef-server.rb' to add/modify the non_ssl_port attribute:

{% highlight shell %}
nginx['non_ssl_port'] = 8080
{% endhighlight %}

And then we can trigger chef-server reconfiguration:
{% highlight shell %}
root@chef:~ # chef-server-ctl reconfigure
{% endhighlight %}

After that's done, we can install and set-up nginx on the linux host, here is the ubuntu/debian way but i'm sure you can adapt to your liking:

{% highlight shell %}
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
{% endhighlight %}

# Setting up the acme client

I am pretty fond of Lukas Schauer [@lukas2511](https://twitter.com/lukas2511) bash solution [*dehydrated*](https://github.com/lukas2511/dehydrated) so there is how i set it up, it shouldn't be difficult to adapt this to any other acme client:

## Installing dehydrated (my way)
{% highlight shell %}
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
{% endhighlight %}

And there you go !

## Configuring dehydrated

... Well almost ^^ we still have a bit of setup to do.

Nous avons trois fichiers à créer: la configuration 'globale', la liste des domaines à entretenir et le script des hooks qui redemarrera chef-server lors de l'obtention d'un nouveau certificat.

Pour la configuration globale (chemin de base /usr/local/etc/dehydrated/config), nous avons principalement trois variables à définir: CONTACT_EMAIL pour le suivi du certificat, WELLKNOWN qui indique le dossier de base dans lequel seront créés les challenges et HOOK pour definir le chemin du script des hooks, exemple:

{% highlight shell %}
root@chef:~ # cat > /usr/local/etc/dehydrated/config << EOF
CONTACT_EMAIL=ssl@xxx.com
WELLKNOWN=/var/www/html/.well-known/acme-challenge
HOOK=/usr/local/sbin/le-hook.sh
EOF
{% endhighlight %}

Pour le domaine si comme moi vous utilisez le nom de la machine il y a une solution simple:
{% highlight shell %}
root@chef:~ # hostname -f >| /usr/local/etc/dehydrated/domains.txt
{% endhighlight %}
Sinon il suffit de rentrer votre domaine dans '/usr/local/etc/dehydrated/domains.txt'.

Pour le script de hook, voici un exemple:

{% highlight shell %}
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
{% endhighlight %}

## Creation du certificat

{% highlight shell %}
root@chef:~ # /usr/local/sbin/dehydrated --register --accept-terms
root@chef:~ # /usr/local/sbin/dehydrated -c
{% endhighlight %}

# Activation du certificat dans chef-server

/etc/opscode/chef-server.rb
{% highlight shell %}
nginx['ssl_certificate']  = "/usr/local/etc/dehydrated/certs/chef.xxx.com/cert.pem"
nginx['ssl_certificate_key']  = "/usr/local/etc/dehydrated/certs/chef.xxx.com/privkey.pem"
{% endhighlight %}


{% highlight shell %}
root@chef:~ # chef-server-ctl reconfigure
{% endhighlight %}

Et Voila !
