#!/usr/bin/env python3
import html as html_lib
import json
import os
import re
from datetime import date, datetime, time
from urllib.parse import quote
from html_template import HTML_TEMPLATE

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
        "filePairs": [],
        "num_files": 0
    }
    entries = sorted(os.scandir(folder), key=lambda e: (not e.is_dir(), e.name.lower()))

    fileEntries = []

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

            fileEntries.append({
                "name": entry.name,
                "url": "pdfs/" + child_rel,
                "url_rel": entry.name,
                "size": size,
                "advanced": False,
            })

    advancedEntries = {}
    for entry in fileEntries:
        extensionlessName = entry["name"][:-4]
        SUFFIXES_AUFGABEN = ["Aufgaben"]
        SUFFIXES_LÖSUNGEN = ["Lösungen"]
        entry_name_split = re.split(' |-|\\.|,|;', extensionlessName)
        if entry_name_split[-1] in SUFFIXES_AUFGABEN:
            entryNameSuffixless = extensionlessName[:-len(entry_name_split[-1])]
            if entryNameSuffixless in advancedEntries.keys():
                advancedEntries[entryNameSuffixless]["AufgabenURL"] = entry["name"]
            else:
                advancedEntries[entryNameSuffixless] = {
                    "name": entryNameSuffixless,
                    "advanced": True,
                    "AufgabenURL": entry["name"]
                }
            
        if entry_name_split[-1] in SUFFIXES_LÖSUNGEN:
            entryNameSuffixless = extensionlessName[:-len(entry_name_split[-1])]
            if entryNameSuffixless in advancedEntries.keys():
                advancedEntries[entryNameSuffixless]["LösungenURL"] = entry["name"]
            else:
                advancedEntries[entryNameSuffixless] = {
                    "name": entryNameSuffixless,
                    "advanced": True,
                    "LösungenURL": entry["name"]
                }

    filesAdded = set()

    for advancedEntry in advancedEntries.values():
        if not ("LösungenURL" in advancedEntry and "AufgabenURL" in advancedEntry):
            continue

        node["filePairs"].append(advancedEntry)
        node["num_files"] += 2
        filesAdded.add(advancedEntry["LösungenURL"])
        filesAdded.add(advancedEntry["AufgabenURL"])


    for entry in fileEntries:
        if entry["name"] in filesAdded:
            continue
        node["files"].append(entry)
        node["num_files"] += 1
    
    return node



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
            .replace("__VERSION__", static_elements["__VERSION__"])
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
        cards = []
        for f in node["files"]:
            cards.append((f, node["name"]))

        if cards:
            rows = []
            for f, trail in cards:
                rows.append(
                    "<article class=\"card\">"
                    f'<h3>{esc(f["name"])}</h3>'
                    f'<p class="meta">{esc(trail)} &middot; {esc(f["size"])}</p>'
                    f'<a class="btn" href="{esc(f["url_rel"])}" download>Download PDF</a>'
                    "</article>"
                )
            parts.append(
                f'<section id="{node["slug"]}">' + 
                f'<h2>{esc(node["name"])}</h2>' + 
                f'<div class="grid">{"\n"}{"\n".join(rows)}{"\n"}</div>' + 
                "</section>"
            )

    if node["filePairs"]:
        rows = []
        for filePair in node["filePairs"]:
            rows.append(
                "<article class=\"card\">"
                f'<h3>{esc(filePair["name"])}</h3>'
                f'<a class="btn" href="{esc(filePair["AufgabenURL"])}" download>⤓ Aufgaben</a>'
                f'<a class="btn" href="{esc(filePair["LösungenURL"])}" download>⤓ Lösungen</a>'
                "</article>"
            )
        parts.append(
            f'<section id="{node["slug"]}">'
            f'<h2>{esc(node["name"])}</h2>'
            f'<div class="grid">{"\n"}{"\n".join(rows)}{"\n"}</div>'
            "</section>"
        )
        
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
        "__VERSION__": "v0.1.2.0",
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