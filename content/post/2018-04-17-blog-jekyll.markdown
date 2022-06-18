---
categories: [ 'blog' ]
date: "2018-04-17T00:00:00Z"
tags: [ "jekyll" ]
title: Upgrading the blog, day 2
---

Last time up on setting up nginx to make PageSpeed Insight happy, we saw that tweaking the webserver wasn't enough, so now we will have to work on the content.

 * Compress html output
 * minify & pre-compress js/css assets
 * optimize media assets


## Compress (minify) html output

There are a bunch of solutions for this step, as of now i'm using the simpler approach of "jekyll-compress", it's an html "compressor" that work in pure "Liquid" (the templating language of jekyll), so no strange ruby installation and whatnot, you only need to fetch the compress.html layout generated in the releases, put it in your `_layouts/` folder and modify your layouts to use it as base. If there is a "master" default.html layout it's as simple as adding the following in the header:

{{< highlight liquid >}}
---
layout: compress
---

{{< / highlight >}}

You can tweak the layout so as to filter jekyll to use this new plugin (altough using bundle seem to make this step optionnal)

{{< highlight yaml >}}
compress_html:
  clippings: all
  comments: ["<!-- ", " -->"]
# you can even remove 'optionnal' end tags:
#  endings: [html, head, body, li, dt, dd, rt, rp, optgroup, option, colgroup, caption, thead, tbody, tfoot, tr, td, th]
  profile: false
  blanklines: false
  ignore:
    envs: [local, dev, developpment]
{{< / highlight >}}

[Jekyll Compress GitHub Projet](https://github.com/penibelst/jekyll-compress-html).


## Minify CSS/JS, Optimize media, ..

There again exist a lot of solutions, i choose for now [jekyll-assets](https://github.com/envygeeks/jekyll-assets) which promise a wide list of capabilities regarding assets management.

However using this tool wasn't exactly "easy-peasy".

### Setup

My first attempt was to add the jekyll-assets gem to the system (debian on the laptop/FreeBSD on the server) like before, however this proved a bit chalenging (two gems needed different version for activesupport) and not very "clieanish", so i looked into deployment using `bundle` tool.

{{< highlight shell >}}
root@arcanin:~ # apt install ruby-bundler
{{< / highlight >}}

Then you need to write a `Gemfile`, listing all your dependencies:
{{< highlight ruby >}}
source "https://rubygems.org"

gem "jekyll"

#
# jekyll-assets plugin itself
#

gem "jekyll-assets"

#
# Additional gems for jekyll-assets
#
gem "coffee-script"  # We want to write our javascripts in CoffeeScript
gem "uglifier"       # And we want our javascripts to be minified with UglifyJS
gem "sass"           # And we want to write our stylesheets using SCSS/SASS
#gem "bootstrap-sass" # For bootstrap 3.x, there is a "funny" gotcha here since jekyll-assets wrongly assume the gem is named boostrap-sass
gem "bootstrap"      # For bootstrap 4
gem "font-awesome-sass"

gem "image_optim"

gem "jemoji"
{{< / highlight >}}

And execute `bunde install` to install all thoses dependencies.

NB: By default, even if you're not a privileged user, bundle will try to install gems globally, if that's not what you want you need to provide `--path vendor/bundle` ou `--deployment` to the first install command (this will create a `.bundle/config` file to hold the installation path so that consecutives commands will be able to find the gems).

{{< highlight shell >}}
user@arcanin:~ $ bundle install --deployment
Fetching gem metadata from https://rubygems.org/.........
Fetching concurrent-ruby 1.0.5
Installing concurrent-ruby 1.0.5
Fetching i18n 0.9.5
Installing i18n 0.9.5
[...]
Fetching jekyll-assets 3.0.11
Installing jekyll-assets 3.0.11
Fetching jemoji 0.6.2
Installing jemoji 0.6.2
Fetching uglifier 4.1.9
Installing uglifier 4.1.9
Bundle complete! 9 Gemfile dependencies, 56 gems now installed.
Bundled gems are installed into `./vendor/bundle`
Post-install message from html-pipeline:
-------------------------------------------------
Thank you for installing html-pipeline!
You must bundle Filter gem dependencies.
See html-pipeline README.md for more details.
https://github.com/jch/html-pipeline#dependencies
-------------------------------------------------
Post-install message from image_optim:
Rails image assets optimization is extracted into image_optim_rails gem
You can safely remove `config.assets.image_optim = false` if you are not going to use that gem
{{< / highlight >}}


Next i setup jekyll to use this new plugin. Although using `bundle` some step are optionnal (the gems/plugins list for example), it is IMPERATIVE to add "vendor" in your exclude list because otherwise you will encounter errors of the weirdest kind like:

```
Document 'vendor/bundle/ruby/2.5.0/gems/jekyll-3.7.3/lib/site_template/_posts/0000-00-00-welcome-to-jekyll.markdown.erb' does not have a valid date in the YAML front matter.
```

So here is my configuration:

{{< highlight yaml >}}
sass:
  style: compressed

assets:
  gzip: true
  plugins:
    img:
      optim:
        jekyll:
          jpegrecompress: false

gems:
  - jekyll-assets
# if you want to use Bootstrap 3.x since jekyll-assets incorrectly try
# to load boostrap-sass and the author seems to prefer removing it altogether
# you need to add it manually here:
# - bootstrap-sass

exclude:
  - "README.md"
  - "CHANGELOG.md"
  - "CNAME"
  - "Gemfile"
  - "Gemfile.lock"
  - .gitignore
  - .bundle
  - .git
  - vendor
{{< / highlight >}}

{{< highlight shell >}}
user@desktop:~ $ JEKYLL_ENV=local bundle exec jekyll serve -d /path/to/temporaryroot -V
user@server:~ $ JEKYLL_ENV=production bundle exec jekyll build -d /path/to/webroot
{{< / highlight >}}

### Changes

A few changes are needed in your theme/layout to make full use of jekyll-assets.

1/ The module expects to find assets in a (relatively long) list of predefined locations (assets/css, assets/fonts, assets/images,..., _assets/*, css, fonts, images, ...).
If you have file in any other location, you should move them, or extend the `assets.sources` list.

RQ: the usual css/main.css + _sass/* split doesn't seem to work well with jekyll-assets, all files should be moved in a css/ directory.

I personnaly choosed to move every css/sass/images/fonts in an `_assets` subdirectory to match every other 'special' jekyll folders.

2/ Assets have to be included with a new syntax:

{{< highlight liquid >}}
{% raw %}{% asset main.css %}

{% asset profil.jpg @optim %}{% endraw%}
{{< / highlight >}}

## Layout optimisation

A recurring whining of SEO optimisation tools is related to loading of external JS/CSS ressources (being it the 'main' css or extra fonts, scripts..).

The ideal solution according to thoses tools is to move loading of every css/js at the end of the page, and inline "critical" css in the <head> block to reduce the post-loading 'flickering'.

Sample 'base' layout for jekyll:
{{< highlight liquid >}}{% raw %}
---
layout: compress
---

<!DOCTYPE html>
<html>
  <head>
    {% include head.html %}
    {% asset inline.css @inline %}
  </head>
  <body>
    <div class="container">
      <div class="row">
        {% if page.hide_sidebar or site.data.theme.hide_sidebar %}
          <div class="col-sm-12">
            {{ content }}
          </div>
        {% else %}
          <div class="col-sm-8">
            {{ content }}
          </div>
          <div class="col-sm-4">
            {% include sidebar.html %}
          </div>
        {% endif %}
      </div>
      <div class="row footer">
        <div class="col-sm-12 text-center">
          {% include footer.html %}
        </div>
      </div>
    </div>
    {% asset main.css %}
    {% include scripts.html %}
    {% include fonts.html %}
  </body>
</html>
{% endraw%}{{< / highlight >}}


## Conclusion

After all this you should high-score PSI and other !
