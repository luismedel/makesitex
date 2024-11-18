#!/usr/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2018-2022 Sunaina Pai
# Copyright (c) 2023      Luis Medel
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import glob
import json
import os
import re
import sys
import typing as t
from datetime import datetime

import click
from braceexpand import braceexpand
from jinja2 import Environment, FileSystemLoader, Template, select_autoescape


def log(msg: str, color: str = "white", is_err: bool = False) -> None:
    """Logs a message."""
    click.secho(msg, fg=color, err=is_err)


def log_info(msg: str) -> None:
    log(f"[i] {msg}", color="blue")


def log_warn(msg: str) -> None:
    log(f"[w] {msg}", color="yellow")


def log_error(msg: str) -> None:
    log(f"[!] {msg}", color="red", is_err=True)


def log_critical(msg: str) -> t.Never:
    """Logs a critical error and exit."""
    log(msg, color="red", is_err=True)
    sys.exit(1)


def to_bool(value: t.Any) -> bool:
    if isinstance(value, bool):
        return value
    elif isinstance(value, int):
        return value != 0
    elif isinstance(value, str):
        return value.lower() in (
            "true",
            "yes",
            "ok",
            "si",
            "sí",
            "bai",
            "oui",
            "da",
            "1",
        )
    else:
        return False


def fread(filename: str) -> str:
    try:
        with open(filename, "r") as f:
            return f.read()
    except Exception as ex:
        log_critical(f"Error reading from {filename}: {str(ex)}")


def fwrite(filename: str, text: str) -> None:
    basedir = os.path.dirname(filename)
    os.makedirs(basedir, exist_ok=True)
    if os.path.isfile(filename):
        log_warn(f"Overwriting existing file {filename}")
    try:
        with open(filename, "w") as f:
            f.write(text)
    except Exception as ex:
        log_critical(f"Error writing to {filename}: {str(ex)}")


def expand_files(pattern: str, max_results: int = 0) -> t.List[str]:
    """Expands a file pattern into a list of existing files"""
    result: t.List[str] = []
    for p in braceexpand(pattern):
        result.extend([f for f in glob.glob(p) if os.path.isfile(f)])
    return result[:max_results] if max_results else result


def truncate(text: str, words: int = 25) -> str:
    """Remove tags and truncate text to the specified number of words."""
    clean = text.replace('"', "'").replace("\n", " ")
    return " ".join(re.sub("(?s)<.*?>", " ", clean).split()[:words])


def read_header(text: str) -> t.Tuple[t.Dict[str, t.Any], int]:
    """Parses the header and returns a dict with the values and the end position."""
    values = {}
    end = 0

    lines = text.split("\n")
    if lines[0].strip() == "---":
        end += len(lines[0]) + 1

        i = 1
        while lines[i].strip() != "---":
            end += len(lines[i]) + 1
            m = re.match(r"^([^:]+):(.*)$", lines[i])
            if m:
                values[m.group(1).strip()] = m.group(2).strip()
            i += 1
        end += len(lines[i]) + 1

    return values, end


def format_time(date_str: str, format: str) -> str:
    """Reformats a textual date using the specified format string"""
    PATTERNS: t.Tuple[str, ...] = (
        "%Y-%m-%d",
        "%Y%m%d",
    )

    d: datetime
    for pat in PATTERNS:
        try:
            d = datetime.strptime(date_str, pat)
            return d.strftime(format)
        except ValueError:
            continue
    log_warn(f"Can't parse date {date_str}")
    return ""


def read_content(
    filename: str, site_params: t.Dict[str, t.Any]
) -> t.Dict[str, t.Any] | None:
    """Reads content and metadata from file into a dictionary."""
    try:
        # Read file content.
        text = fread(filename)
        content: t.Dict[str, t.Any] = dict(site_params)

        # Read metadata and save it in a dictionary.
        date_slug = os.path.basename(filename).split(".")[0]
        match = re.search(r"^(?:(\d\d\d\d-\d\d-\d\d)-)?(.+)$", date_slug)
        if match:
            content.update(
                {
                    "date": match.group(1) or "1970-01-01",
                    "slug": match.group(2),
                }
            )

        # Read header and separate content
        header, end = read_header(text)
        content.update(header)
        text = text[end:]

        # Update the dictionary with content and RFC 2822 date.
        content.update(
            {
                "content": text,
                "short_date": format_time(content["date"], "%Y-%m-%d"),
                "human_date": format_time(
                    content["date"], content["date_human_format"]
                ),
                "rfc_2822_date": format_time(
                    content["date"], "%a, %d %b %Y %H:%M:%S +0000"
                ),
            }
        )

        return content
    except Exception as ex:
        log_critical(f"Unable to read contents from {filename}: {str(ex)}")
        return None


def render_template(tpl: t.Union[Template, str], params: t.Dict[str, t.Any]) -> str:
    if isinstance(tpl, str):
        tpl = Template(tpl)
    return tpl.render(**params)


def render_page(
    path: str, site_params: t.Dict[str, t.Any]
) -> t.Dict[str, t.Any] | None:
    """Generate a page from page content."""

    filename = next(iter(expand_files(path, max_results=1)), None)
    if not filename:
        log_info(f"No files match pattern {path}")
        return None

    page_params = read_content(filename, site_params)
    if not page_params:
        return None

    # Populate placeholders in content
    rendered_content = render_template(page_params["content"], page_params)
    page_params["content"] = rendered_content

    # Convert Markdown content to HTML.
    if filename.endswith((".md", ".mkd", ".mkdn", ".mdown", ".markdown")):
        try:
            import markdown

            page_params["content"] = markdown.markdown(
                page_params["content"],
                extensions=[
                    "fenced_code",
                    "pymdownx.tilde",
                    "pymdownx.tasklist",
                    "mdx_inline_graphviz",
                ],
            )
        except ImportError as e:
            log_critical(f"Cannot render Markdown in {path}: {str(e)}")

    return page_params


def make_pages(
    pattern: str,
    dest_path_pattern: str,
    default_layout: Template,
    site_params: t.Dict[str, t.Any],
    jinja_env: Environment,
) -> t.List[t.Dict[str, t.Any]]:
    """Generate pages from page content."""
    items: t.List[t.Dict[str, t.Any]] = []

    for src_path in expand_files(pattern):
        output_dict = render_page(src_path, site_params)
        if not output_dict:
            continue

        items.append(output_dict)

        custom_template: str | None = output_dict.get("template")
        layout = (
            jinja_env.get_template(custom_template)
            if custom_template
            else default_layout
        )
        output = render_template(layout, output_dict)

        dest_path = render_template(dest_path_pattern, output_dict)
        log_info(f"Rendering {src_path} > {dest_path} ...")
        fwrite(dest_path, output)

    return list(sorted(items, key=lambda x: x["date"], reverse=True))


def make_index(
    front_content: t.Dict[str, t.Any] | None,
    pages: t.List[t.Dict[str, t.Any]],
    dest_path_pattern: str,
    list_layout: Template,
    item_layout: Template,
    site_params: t.Dict[str, t.Any],
) -> None:
    """Generate an index page for a content directory."""
    items = []
    for page_dict in pages:
        item_params = dict(site_params, **page_dict)
        item_params["summary"] = (
            page_dict.get("summary")
            or page_dict.get("description")
            or truncate(page_dict["content"])
        )
        item = render_template(item_layout, item_params)
        items.append(item)

    if front_content:
        site_params["front_content"] = front_content.get("content", "")
    site_params["content"] = "".join(items)
    output = render_template(list_layout, site_params)

    dest_path = render_template(dest_path_pattern, site_params)
    log_info(f"Rendering {len(items)} items ...")
    fwrite(dest_path, output)


def make_site(
    all: bool,
    config: str,
    layout: str,
    content: str,
    output: str,
    overwrite_output: bool,
):
    try:
        os.makedirs(output, exist_ok=overwrite_output)
    except Exception as ex:
        log_critical(f"Error creating output directory {output}: {str(ex)}")

    # Default parameters.
    site_params: dict[str, t.Any] = {
        "author": "Admin",
        "site_subtitle": "",
        "site_description": "",
        "date_human_format": "%d %b, %Y",
        "current_year": datetime.now().year,
    }

    # If site.json exists, load it.
    if os.path.isfile(config):
        log_info(f"Reading configuration from {config}")
        site_params.update(json.loads(fread(config)))
    else:
        log_warn(f"Configuration file {config} not found. Using defaults.")

    log_info(f"Generating site with params: {json.dumps(site_params, indent=2)}")

    # Load default layouts.
    jinja_env = Environment(
        loader=FileSystemLoader(layout), autoescape=select_autoescape()
    )

    page_layout = jinja_env.get_template("page.html")
    post_layout = jinja_env.get_template("post.html")
    list_layout = jinja_env.get_template("list.html")
    item_layout = jinja_env.get_template("item.html")
    feed_xml = jinja_env.get_template("feed.xml")
    item_xml = jinja_env.get_template("item.xml")

    # Create site pages.
    make_pages(
        f"{content}/[!_]*.{{md,html}}",
        f"{output}/{{{{ slug }}}}/index.html",
        page_layout,
        site_params,
        jinja_env,
    )
    make_pages(
        f"{content}/_index.{{md,html}}",
        f"{output}/index.html",
        page_layout,
        site_params,
        jinja_env,
    )

    content_dirs = site_params.get("content_dirs", {}).items()
    for d, meta in content_dirs:
        output_subdir: str = meta.get("slug", d)
        title: str = meta.get("title", d.capitalize())

        log_info(f"Rendering content dir {title} => {output_subdir} ...")

        generate_index: bool = to_bool(meta.get("generate_index"))
        generate_rss: bool = to_bool(meta.get("generate_rss"))

        dir_params = dict(dir=output_subdir, title=title, current_content_dir=meta, **site_params)

        exclusion_prefix = "" if all else "[!_]"

        content_pages = make_pages(
            f"{content}/{d}/{exclusion_prefix}*.{{md,html}}",
            f"{output}/{output_subdir}/{{{{ slug }}}}/index.html",
            post_layout,
            dir_params,
            jinja_env,
        )

        if generate_index:
            log_info("Generating index ...")

            front_content = render_page(
                f"{content}/{d}/_index.{{md,html}}", site_params
            )
            if front_content:
                log_info(f"Found front content for {title}")

            make_index(
                front_content,
                content_pages,
                f"{output}/{output_subdir}/index.html",
                list_layout,
                item_layout,
                dir_params,
            )
        else:
            # Render existing index (if any)
            make_pages(
                f"{content}/{d}/_index.{{md,html}}",
                f"{output}/{output_subdir}/index.html",
                page_layout,
                site_params,
                jinja_env,
            )

        if generate_rss:
            log_info("Generating RSS ...")

            make_index(
                None,
                content_pages,
                f"{output}/{output_subdir}/rss.xml",
                feed_xml,
                item_xml,
                dir_params,
            )


@click.command()
@click.option("--all", is_flag=True, help="Generate all content, including drafts.")
@click.option(
    "--config",
    type=click.Path(dir_okay=False),
    default="site.json",
    help="Path to the configuration file.",
)
@click.option(
    "--layout",
    type=click.Path(file_okay=False, exists=True),
    default="layout",
    help="Path to the layout directory.",
)
@click.option(
    "--content",
    type=click.Path(file_okay=False, exists=True),
    default="content",
    help="Path to the content directory.",
)
@click.option(
    "--output",
    type=click.Path(file_okay=False),
    default="public",
    help="Path to the output directory.",
)
@click.option("--overwrite-output", is_flag=True, help="Overwrite output directory.")
def main(
    all: bool,
    config: str,
    layout: str,
    content: str,
    output: str,
    overwrite_output: bool,
) -> None:
    log_info("Generating site ...")
    make_site(all, config, layout, content, output, overwrite_output)


if __name__ == "__main__":
    main()
