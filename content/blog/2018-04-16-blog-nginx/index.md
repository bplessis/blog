---
date: "2018-04-16T00:00:00Z"
tags: [ "freebsd", "nginx" ]
title: Upgrading the blog, day 1
---

A year has past since the beginning of this little experiment, and some results are already showing:

 * i'm not very prolific ^^
 * i'm becoming more and more grumpy
 * i don't like my blog's setup (but didn't find better for now)
.

So yeah, new year was 4 month ago and still nothing new here, my article on bind, dnssec and knot hasn't moved further, but work-related issues send me back here to make some experiments, our SEO consultants where reportings issues on our client's website and where in need of informations. Using the provided analytics software (PageSpeed Insight) on this blog gave horrendous results:

 * This is a static content blog but not cache informations was returned by the webserver
 * HTML, Javascript and CSS code where not exactly optimized
 * Text data wasn't compressed on the way to the browser

Well not everything was bad, at least SSL was working OK and even more so HTTP/2.0 is active on the setup, however this isn't part of PageSpeed Insight analysis (so much for all the SEO-fuss on https/...).

## Enhancing webserver configuration

As said previously this is an experementation server, so as if using FreeBSD wasn't enough i also used nginx on many services, so there is that i didn't look over levergage browser cache, compressing stream,.. So there is the job for today.

The starting point is a pretty straightforward configuration, i have setup two server block, one for the http service with a forced 301 redirect over HTTPS url and the second for the HTTPS service. Only peculiarity is the IPv4 private IP that is used, having only one IPv4 address has made me a little "creative" and so i'm using an haproxy redirect service which allow real source IP preservation, even with SSL stream using special protocol:
{{< highlight nginx >}}
   server {
        listen       10.x.y.z:80       proxy_protocol;
        listen       [2001:bc8:2909:101::4]:80;

        server_name  blog.plessis.info;

        set_real_ip_from                10.x.y.w;
        real_ip_header                  proxy_protocol;
        real_ip_recursive               on;

        # enforce https
        location / {
                return 301 https://$server_name$request_uri;
        }
    }

    server {
        listen       10.x.y.z:443      ssl http2 proxy_protocol;
        listen       [2001:bc8:2909:101::4]:443 ssl http2;

        server_name  blog.plessis.info;

        # Set the client remote address to the one sent in the X_FORWARDED_FOR header from trusted addresses.
        set_real_ip_from                10.x.y.w;
        real_ip_header                  proxy_protocol;
        real_ip_recursive               on;

        ssl_certificate      /usr/local/etc/dehydrated/certs/blog.plessis.info/fullchain.pem;
        ssl_certificate_key  /usr/local/etc/dehydrated/certs/blog.plessis.info/privkey.pem;

        ssl_ciphers  HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers  on;

        location / {
            root   /usr/local/www/nginx/data;
            index  index.html index.htm;
        }

        # redirect server error pages to the static page /50x.html
        #
        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   /usr/local/www/nginx-dist;
        }
    }
{{< / highlight >}}

### Browser Cache

So we need to add a few rules, for starter leveraging browser cache is usually done by adding a location block matching common static content extensions and adding an expires keyword:

{{< highlight nginx >}}
    server {
        [...]
        location ~* \.(js|css|jpg|png)$ {
            expires 120d;
        }
        [...]
    }
{{< / highlight >}}

However widespread this is (it even found it's way in some configuration sample for many web applications) this didn't feel right compared to the ExpiresByType of apache's mod_deflate.
Also i had to repeat the root stanza which didn't feel very nice.

Luckily i found another way here [Digital Ocean Community](https://www.digitalocean.com/community/tutorials/how-to-implement-browser-caching-with-nginx-s-header-module-on-ubuntu-16-04): setting up an "expire map" feel much more like what i'm used to, so there i go.

{{< highlight nginx >}}
    # Expires map
    map $sent_http_content_type $expires {
        default                    off;
        text/html                  epoch;
        text/css                   max;
        application/javascript     max;
        ~image/                    max;
    }

    [...]

    server {
        [...]
        server_name  blog.plessis.info;
        root   /usr/local/www/nginx/data;

        [...]
        location / {
            index  index.html index.htm;
        }

        expires $expires;
        [...]
    }
{{< / highlight >}}

This feel much better !

### Content compression

For this there is not much discussion here, the setup is quite simple so no need to rack our brains. Given the nature of the website (statically _generated_) i also included an option to detect and serve pre-generated compressed ressources, this will however need some work on jekyll side but i'm getting ahead of myself :

{{< highlight nginx >}}
    server {
        [...]
        #
        # Gzip Settings
        ##

        gzip on;
        gzip_disable "msie6";

        gzip_vary on;
        gzip_proxied any;
        gzip_comp_level 8;
        gzip_min_length 256;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;

        # Allow serving pre-compressed files
        gzip_static on;
        [...]
    }
{{< / highlight >}}

### Security Headers: HSTS, X-Frame-Option, ...

While being there, adding a few security-related headers couldn't hurt so there we go:

{{< highlight nginx >}}
    server {
        [...]
        #
        # Security headers:

        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options "SAMEORIGIN";
        add_header X-XSS-Protection "1; mode=block";
        add_header X-Download-Options noopen;
        add_header X-Permitted-Cross-Domain-Policies none;

        [...]
    }
{{< / highlight >}}

## Conclusion

This helped a bit increasing PageSpeed score but it wasn't the promised/foretold revolution you could hear here and there.

So, next step is content optimisation !

PS: You can download the [NGINX Configuration](nginx_blog_20180417.conf).
