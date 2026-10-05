#!/usr/bin/env python3
import html as html_lib
import json
import os
import re
from datetime import date, datetime, time
from urllib.parse import quote

ROOT = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(ROOT, "pdfs")
OUTPUT_HTML = os.path.join(ROOT, "index.html")
OUTPUT_JSON = os.path.join(ROOT, "menu.json")

SITE_TITLE = "Mathe Arbeitsblätter"
SITE_TAGLINE = ""


def human_size(num: int) -> str:
    value = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{int(num)} B"


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+-", "-", name.lower()).strip("-")
    return slug or "item"


def esc(s: str) -> str:
    return html_lib.escape(str(s), quote=True)


def scan(folder: str, rel: str) -> dict:
    """Recursively collect folders and PDF files into a tree dict."""
    node = {
        "name": os.path.basename(folder),
        "slug": slugify(os.path.basename(folder)),
        "rel": rel.replace(os.sep, "/"),
        "folders": [],
        "files": [],
        "num_files": 0
    }
    entries = sorted(os.scandir(folder), key=lambda e: (not e.is_dir(), e.name.lower()))
    for entry in entries:
        child_rel = rel + "/" + entry.name if rel else entry.name
        if entry.is_dir():
            newNode = scan(entry.path, child_rel)
            node["folders"].append(newNode)
            node["num_files"] += newNode["num_files"]
        elif entry.name.lower().endswith(".pdf"):
            try:
                size = human_size(entry.stat().st_size)
            except OSError:
                size = "?"
            node["files"].append({
                "name": entry.name,
                "url": "pdfs/" + child_rel,
                "size": size,
            })
            node["num_files"] += 1
    return node


def collect_cards(node: dict, trail: list) -> list:
    """Flatten all PDFs under a folder into (file, breadcrumb) pairs."""
    cards = []
    for f in node["files"]:
        cards.append((f, " / ".join(trail + [node["name"]])))
    for sub in node["folders"]:
        cards.extend(collect_cards(sub, trail + [node["name"]]))
    return cards


def section(node: dict) -> str:
    cards = collect_cards(node, [])
    if not cards:
        return ""
    rows = []
    for f, trail in cards:
        rows.append(
            "<article class=\"card\">"
            f'<h3>{esc(f["name"])}</h3>'
            f'<p class="meta">{esc(trail)} &middot; {esc(f["size"])}</p>'
            f'<a class="btn" href="{esc(f["url"])}" download>Download PDF</a>'
            "</article>"
        )
    return (
        f'<section id="{node["slug"]}">'
        f'<h2>{esc(node["name"])}</h2>'
        f'<div class="grid">{"\n"}{"\n".join(rows)}{"\n"}</div>'
        "</section>"
    )


# ---------------------------------------------------------------------------
# The page template. __UPPER_CASE__ placeholders are replaced in main().
# CSS braces are fine here because this is a plain string, not an f-string.
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         margin: 0; background: #f6f7f9; color: #1f2933; }
  header.top { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #fff;
               padding: 2rem; text-align: center; }
  header.top h1 { margin: 0 0 .4rem 0; }
  header.top p  { margin: 0; opacity: .9; }
  .header-link { display: block; color: #fff; text-decoration: none; }
  .header-link:hover h1 { text-decoration: underline; }

  /* ---------- navigation bar ---------- */
  nav.main-nav { background: #fff; border-bottom: 1px solid #e5e7eb;
                 position: sticky; top: 0; z-index: 50; }
  .nav-toggle { display: none; }
  ul.menu { list-style: none; margin: 0; padding: 0; display: flex;
            flex-wrap: wrap; gap: .25rem; }
  .menu > li { position: relative; }
  .menu button.parent { background: none; border: none; cursor: pointer;
    font: inherit; color: #1f2933; padding: .65rem 1rem; border-radius: 6px; }
  .menu button.parent:hover { background: #eef2ff; }
  .menu a.folder-link { background: none; text-decoration: none;
    cursor: pointer; font: inherit; color: #1f2933;
    display: inline-block;
    padding: .65rem 1rem; border-radius: 6px; }
  .menu a.folder-link:hover { background: #eef2ff; }
  .caret { display: inline-block; font-size: .7em; opacity: .7; }
  .menu li.open button.parent { color: #2563eb; }

  /* dropdown / submenu boxes */
  ul.dropdown { display: none; position: absolute; top: 100%; left: 0;
    min-width: 230px; background: #fff; border: 1px solid #e5e7eb;
    box-shadow: 0 6px 16px rgba(15, 23, 42, .14); list-style: none;
    padding: .3rem .5rem; z-index: 60; }
  .menu li:hover > ul.dropdown,
  .menu li.open > ul.dropdown { display: block; }
  ul.dropdown li { position: relative; }
  ul.dropdown li:hover > ul.dropdown,
  ul.dropdown li.open > ul.dropdown { display: block; left: 100%; top: -.25rem; }
  ul.dropdown li { min-width: 220px; }
  .dropdown a { display: block; padding: .45rem .8rem; font-size: .9rem;
                color: #1f2933; text-decoration: none; border-radius: 5px; white-space: nowrap; }
  .dropdown a:hover { background: #eef2ff; color: #2563eb; }
  .dropdown button.parent { display: block; width: 100%; text-align: left; padding: .45rem .8rem; }
  .dropdown .empty { display: block; padding: .45rem .8rem; color: #9aa4b2; font-style: italic; }

  /* ---------- content ---------- */
  main { max-width: 1000px; margin: 0 auto; padding: 2rem 1.5rem; }
  section h2 { margin-top: 2.2rem; border-bottom: 2px solid #e5e7eb;
               padding-bottom: .4rem; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
          gap: 1.1rem; }
  .card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
          padding: 1rem 1.1rem; box-shadow: 0 2px 6px rgba(15,23,42,.06); }
  .card h3 { margin: 0 0 .3rem 0; font-size: 1rem; overflow-wrap: anywhere; }
  .card .meta { margin: 0 0 .8rem 0; color: #6b7686; font-size: .85rem; }
  .btn { display: inline-block; background: #2563eb; color: #fff;
         text-decoration: none; padding: .5rem 1rem; border-radius: 6px;
         font-weight: 600; font-size: .9rem; }
  .btn:hover { background: #1d4ed8; }
  footer { text-align: center; color: #8a94a3; padding: 2rem 0; }

  /* ---------- mobile ---------- */
  @media (max-width: 860px) {
    .nav-toggle { display: inline-block; background: #2563eb; color: #fff;
      border: none; border-radius: 6px; padding: .5rem .9rem;
      cursor: pointer; font: inherit; }
    ul.menu { display: none; position: absolute; left: 0; top: 100%;
              width: 100%; background: #fff; }
    nav.main-nav.open ul.menu { display: block; }
    .menu > li { display: block; width: 100%; }
    ul.dropdown { position: static; box-shadow: none; }
  }
</style>
</head>
<body>
<header class="top">
  <a class="header-link" href="__HEADERLINK__">
    <h1>&#128196; __TITLE__</h1>
    <p>__TAGLINE__</p>
  </a>
</header>

<nav class="main-nav" aria-label="Documents">
  <button type="button" class="nav-toggle" id="navToggle" aria-expanded="false">&#9776; Menu</button>
  <ul class="menu" id="menu">
__NAV__
  </ul>
</nav>

<main>
__SECTIONS__
</main>

<footer>&copy; __YEAR__ Tim Stanglow</footer>

<script>
  // Click-to-toggle (touch + keyboard), complements CSS :hover for mice.
  const menuItems = document.querySelectorAll('li.has-sub');
  function closeAll(except) {
    menuItems.forEach(function (li) {
      if (li === except) return;
      li.classList.remove('open');
      const b = li.querySelector(':scope > button.parent');
      if (b) b.setAttribute('aria-expanded', 'false');
    });
  }
  menuItems.forEach(function (li) {
    const btn = li.querySelector(':scope > button.parent');
    if (!btn) return;
    btn.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      const willOpen = !li.classList.contains('open');
      closeAll(li);
      li.classList.toggle('open', willOpen);
      btn.setAttribute('aria-expanded', String(willOpen));
    });
  });
  document.addEventListener('click', function () { closeAll(null); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeAll(null);
  });

  // Mobile hamburger
  const navEl = document.querySelector('nav.main-nav');
  document.getElementById('navToggle').addEventListener('click', function (e) {
    e.stopPropagation();
    navEl.classList.toggle('open');
    this.setAttribute('aria-expanded', String(navEl.classList.contains('open')));
  });
</script>
</body>
</html>
"""


def nav_item(node: dict, depth: int, currentPageDepth: int) -> str:
    """A <li> for one folder: a link to its page; hover/click shows subfolder dropdowns."""

    href_start = ""
    if currentPageDepth == 0:
        href_start = "pdfs/"
    else:
        href_start = "../" * currentPageDepth
    href = href_start + quote(node["rel"], safe="/") + "/index.html"

    # Recursive: this folder's dropdown contains entries for every subfolder.
    seperator = "\n" + "  "*(depth+2)
    kids = seperator.join(nav_item(sub, depth + 1, currentPageDepth) for sub in node["folders"])

    if not kids:
        # Leaf folder: plain link to its page, no dropdown, no caret.
        return f'<li><a class="folder-link" href="{esc(href)}">{esc(node["name"])}</a></li>'

    caret = "▾" if depth == 0 else "▸"
    return (
        f'<li class="has-sub">'
        f'<a class="folder-link" href="{esc(href)}">{esc(node["name"])} <span class="caret">{caret}</span></a>'
        f'<ul class="dropdown">{seperator}{kids}{seperator}</ul>'
        f'</li>'
    )


def build_nav(tree: dict, currentPageDepth: int = 0) -> str:
    parts = ["__NAVBACK__"]
    parts.extend([nav_item(f, 0, currentPageDepth) for f in tree["folders"]])
    if not parts:
        return '<li><span class="empty">No PDFs found yet</span></li>'
    return "\n  ".join(parts)
    

def maxDepth(node: dict) -> int:
    curMax = 1
    for folder in node["folders"]:
        curMax = max(maxDepth(folder)+1, curMax)
    return curMax


def render_page(node: dict, static_elements: dict) -> str:    
    depth: int = node["rel"].count("/") + 1
    if node["rel"] == "":
        depth = 0
    
    headerLink = "../" * (depth+1) + "index.html"
    if depth == 0:
        headerLink = "index.html"

    title = static_elements["__TITLE__"] + " - " + node["name"]
    if depth == 0:
        title = static_elements["__TITLE__"]
    tagline = static_elements["__TAGLINE__"] + node["rel"]

    page = (HTML_TEMPLATE
            .replace("__NAV__", static_elements["navs"][depth])
            .replace("__NAVBACK__", navBackLink(node, depth))
            .replace("__HEADERLINK__", headerLink)
            .replace("__TITLE__", title)
            .replace("__TAGLINE__", tagline)
            .replace("__YEAR__", static_elements["__YEAR__"])
            .replace("__SECTIONS__", build_page_content(node, depth)))
    return page

def navBackLink(node: dict, depth: int) -> str:
    if depth >=2:
        return '<li><a class="folder-link" href="../index.html">&#8592;</a></li>'
    if depth == 1:
        return '<li><a class="folder-link" href="../../index.html">&#8592;</a></li>'
    if depth == 0:
        return '<li><a class="folder-link" href="./index.html">&#8592;</a></li>'


def build_page_content(node: dict, depth: int) -> str:
    parts = []
    if node["folders"]:
        parts.append('<section id="categories"><h2>Kategorien</h2><div class="grid">')
        parts.extend([link(f, depth) for f in node["folders"]])
        parts.append('</div></section>')

    if node["files"]:
        parts.append(section({"name": "Arbeitsblätter", "slug": "documents",
                              "folders": [], "files": node["files"]}))
        
    return "\n".join(p for p in parts if p)


def link(node: dict, depth: int) -> str:
    """A card for one subfolder: name, worksheet count, and a button to its page."""
    href = ""
    if depth == 0:
        href = "pdfs/" + quote(node["rel"], safe="/") + "/index.html"
    else:
        href = "../" * depth + quote(node["rel"], safe="/") + "/index.html"
    count = node["num_files"]
    label = "Arbeitsblatt" if count == 1 else "Arbeitsblätter"

    return (
        '<article class="card">'
        f'<h3>{esc(node["name"])}</h3>'
        f'<p class="meta">{count} {label}</p>'
        f'<a class="btn" href="{esc(href)}">Ordner öffnen</a>'
        "</article>"
    )
    
    return node["name"]


def render_folder(node: dict, static_elements: dict) -> None:

    page = render_page(node, static_elements)

    folder_html_path = os.path.join("pdfs", node["rel"], "index.html")

    with open(folder_html_path, "w", encoding="utf-8") as fh:
        fh.write(page)

    for sub in node["folders"]:
        render_folder(sub, static_elements)

    return


def main() -> None:
    if not os.path.isdir(PDF_DIR):
        raise SystemExit(f"Folder not found: {PDF_DIR}. Create it and add PDFs first.")
    tree = scan(PDF_DIR, "")

    treeDepth = maxDepth(tree)
    static_elements = {
        "__TITLE__": esc(SITE_TITLE),
        "__TAGLINE__": esc(SITE_TAGLINE),
        "__YEAR__": str(date.today().year),
        "navs": [build_nav(tree, i) for i in range(treeDepth)]
    }

    page = render_page(tree, static_elements)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as fh:
        fh.write(page)

    for folder in tree["folders"]:
        render_folder(folder, static_elements)    

    with open(OUTPUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(tree, fh, indent=2)

    print(f"{datetime.now().strftime("%H:%M")}: OK -> wrote {OUTPUT_HTML}, and {OUTPUT_JSON}")


if __name__ == "__main__":
    main()