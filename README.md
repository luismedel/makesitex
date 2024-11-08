
# makesitex

makesitex

A static site generator (yes, another one), building on the excellent work of Sunaina Pai’s [makesite](https://github.com/sunainapai/makesite).

Over time, I made substantial modifications to the original script—some out of necessity, others for pure fun. At this point, it no longer makes sense to refer to it as makesite, but it would also feel wrong to give it an entirely different name, so: makesitex.

The main differences between makesitex and the original makesite are:

- Greater flexibility with `site.json` for easy customization without modifying code.
- Use of Jinja2 templates instead of custom value expansion.
- Improved code robustness (although subjective).
- And, well... it’s mine.

## Usage

Clone this project. If you plan to use the provided build scripts, install [bluish](https://github.com/luismedel/bluish).

```sh
git clone https://github.com/luismedel/makesitex
cd makesitex
pip3 install bluish
```

### Build the example site

The Bluish `site` action builds the example site into the `public` directory, handling any necessary package installations.

```sh
blu site
```

Your site is now generated in the `./public` directory.

To preview the site locally, you can start a web server and access it at http://localhost:8000 with the `serve` command:

```sh
blu serve
```

> Note: Autoreload is not supported at this time.

## Folder Structure

The main folders in `makesitex` are:

- `content/`: Contains the markdown or HTML files for each page or post.
- `content/<dir>/`: Each subdirectory is considered a content directory with its own configuration (see below).
- `layout/`: Holds the template files, including `list.html` for index pages and `feed.xml` for RSS.
- `public/`: This is the output directory where the generated site is stored after running `blu site`.
- `static/`: Contains the static files that need to be copied into the `public/` directory.

## Basic config

You can define any attributes you need in `site.json` and use them directly in the site templates.

The only essential attribute is content_dirs, which lists content directories and any specific settings for each one. However, if you’re just creating a flat site, this can be omitted.

The root itself acts as an implicit content directory.

Example `site.json`:

```json
{
    "author": "Luis Medel",
    "site_subtitle": "Another makesitex site",
    "site_description": "",

    "menu": [
        ["/home", ""],
        ["/blog", "blog"],
        ["/software", "https://github.com/luismedel"]
    ],

    "content_dirs": {
        "drafts": {
            "generate_rss": false
        },
        "blog": {
            "title": "My blog",
            "slug": "blog",
            "generate_index": true,
            "generate_rss": true
        }
    }
}
```

In addition to the properties defined in site.json, makesitex provides a few useful variables for your site:

- `{{ short_date }}`: Displays date in `yyyy-mm-dd` format.
- `{{ human_date }}`: Localized date format (default is `%d %b, %Y`). Customize via `date_human_format` in `site.json`.
- `{{ current_year }}`: Displays the current year, `datetime.now().year`.

## Home

Add your homepage content to the `content/_index.{md|html}` file.

## Content directories

For each content_dir entry in site.json:

- Set `generate_index` to `true` to create an index page (using the `layout/list.html` template) listing all files in that directory. To add custom content to this listing, place an `_index.{md|html}` file in the directory.
- Set `generate_rss` to `true` to generate an RSS feed (based on the `layout/feed.xml` template, though modification is generally unnecessary unless you need specific XML adjustments).

All files within a content directory are processed. However, without an index or RSS feed, they will be undiscoverable.

## Publishing on Gitlab pages

Use the included `.gitlab-ci.yml` configuration file.

```yaml
image: luismedel/bluish-alpine:latest

variables:
  GIT_SUBMODULE_STRATEGY: recursive

pages:
  script:
    - blu site
  artifacts:
    paths:
      - public
  only:
    - master
```

## Publishing on Github pages

Use the included `.github/workflows/site-deploy.yml` configuration file.

```yaml
name: CD

on:
  push:
    branches: [ "master" ]
  pull_request:
    branches: [ "master" ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: luismedel/setup-bluish@v3
      - run: blu site
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: ./public

  deploy:
    needs: build
    runs-on: ubuntu-latest

    permissions:
      pages: write
      id-token: write

    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

## Example site?

[Yes!](https://luismedel.github.io/makesitex/)

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
