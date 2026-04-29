"""
Export Jira Cloud issues to Markdown files.

**Automated field titles (no manual typing by default)**
  - With the default --layout flat, every `##` heading for story text is the **field’s display
    name** returned by Jira in the issue JSON (`names` + rendered / ADF), not a string you type.
  - The script pulls *all* rich-text and comment data through the API — no per-project list of
    titles is required in normal use.

**Optional “grouped” layout** (cosmetic / UI-like nesting)
  - If you omit --group-include, a **built-in** set of common name fragments (description,
    acceptance criteria, user story, …) is used to decide what nests under --group-title.
  - You only set --group-include when you need to *override* that automatic list for your team.

**Threaded comments & images**
  - Replies are read from the API’s `parentId` (replies are nested under the parent in Markdown
    using block-quotes). Root comments are shown first in time order.
  - Inline images in description/comments (ADF) become `![alt](https://.../rest/api/3/attachment/content/ID)`.
    Use **--embed-images** to download those files into `<export_stem>_files/` and reference them
    with relative paths so viewers work offline (uses the same API token as the script).

Prerequisites:
  - pip install requests
  - Optional: pip install html2text  (nicer description formatting)
  - Atlassian account email + API token: https://id.atlassian.com/manage-profile/security/api-tokens
  - Set environment variables (PowerShell):
      $env:JIRA_EMAIL = "you@wiley.com"
      $env:JIRA_API_TOKEN = "your_token"
  Optional: JIRA_BASE (default https://wiley-global.atlassian.net)

Examples:
  # Single issue (fully automatic: auth + key only)
  python jira_cloud_export_stories_to_md.py --key CT-9341

  # JQL: multiple issues (e.g. project stories)
  python jira_cloud_export_stories_to_md.py --jql "project = CT AND type = Story AND key = CT-9341" --out ./jira_stories

  # Skip comments (faster)
  python jira_cloud_export_stories_to_md.py --key CT-9341 --skip-comments

  # Optional nested "Key details" with built-in matching (no --group-include)
  python jira_cloud_export_stories_to_md.py --key CT-9341 --layout grouped --group-title "Key details"

  # Download inline images into <stem>_files/ and use relative ![]() paths
  python jira_cloud_export_stories_to_md.py --key CT-9341 --out ./jira_export --embed-images
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import unescape

import requests

# When --layout grouped and --group-include is not set, match field *display* names
# (from Jira’s `names` map) that contain any of these substrings (case-insensitive).
BUILTIN_GROUP_SUBSTRINGS: tuple[str, ...] = (
    "description",
    "acceptance criteria",
    "user story",
    "background",
    "out of scope",
    "prerequisites",
    "goal",
    "objective",
)

# Optional: pip install html2text  (cleaner than stripping tags)
try:
    import html2text

    _h = html2text.HTML2Text()
    _h.ignore_links = False
    _h.body_width = 0
except ImportError:
    _h = None


def _config() -> tuple[str, str, str]:
    base = os.environ.get("JIRA_BASE", "https://wiley-global.atlassian.net").rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "").strip()
    # API token is a single string (no line breaks). Remove stray CR/LF from Notepad or wrapped paste.
    token = (
        os.environ.get("JIRA_API_TOKEN", "")
        .strip()
        .replace("\n", "")
        .replace("\r", "")
    )
    if not email or not token:
        print(
            "Set JIRA_EMAIL and JIRA_API_TOKEN (e.g. https://id.atlassian.com/manage-profile/security/api-tokens).",
            file=sys.stderr,
        )
        sys.exit(1)
    return base, email, token


def _session(base: str, email: str, token: str) -> requests.Session:
    s = requests.Session()
    s.auth = (email, token)
    s.headers["Accept"] = "application/json"
    return s


def _api_get(
    s: requests.Session, base: str, path: str, params: dict | None = None
) -> dict:
    url = f"{base}/rest/api/3{path}"
    r = s.get(url, params=params or {}, timeout=60)
    if r.status_code != 200:
        print(f"GET {url} -> {r.status_code}\n{r.text[:2000]}", file=sys.stderr)
        r.raise_for_status()
    return r.json()


def _jira_attachment_url(jira_base: str, file_id: str) -> str:
    """Jira Cloud REST: download URL pattern (ADF id may not match; prefer attachment['content'])."""
    b = (jira_base or "").rstrip("/")
    return f"{b}/rest/api/3/attachment/content/{file_id}"


def _media_image_url(
    attrs: dict,
    jira_base: str,
    attachments: list[dict] | None,
) -> str | None:
    """
    Resolve ADF media node to a real download URL. Jira often uses UUIDs in the editor; the
    working URL is usually fields.attachment[].content, not /attachment/content/{uuid}.
    """
    u = (attrs.get("url") or "").strip()
    if u.startswith("http://") or u.startswith("https://"):
        return u
    mid = attrs.get("id")
    if mid is None:
        return None
    mids = str(mid)
    if attachments:
        for att in attachments:
            if not isinstance(att, dict):
                continue
            aid = att.get("id")
            if aid is not None and str(aid) == mids:
                cu = (att.get("content") or "").strip()
                if cu:
                    return cu
        fn = (attrs.get("filename") or attrs.get("alt") or "").strip().lower()
        if fn:
            for att in attachments:
                if not isinstance(att, dict):
                    continue
                afn = (att.get("filename") or "").strip().lower()
                if afn and (afn == fn or fn in afn or afn in fn):
                    cu = (att.get("content") or "").strip()
                    if cu:
                        return cu
    return _jira_attachment_url((jira_base or "").rstrip("/"), mids)


def _fetch_attachment_json(
    s: requests.Session, jira_base: str, attachment_id: str, version: int = 3
) -> dict | None:
    """GET /rest/api/{2|3}/attachment/{id} — JSON with 'content' download URL."""
    base = (jira_base or "").rstrip("/")
    q = urllib.parse.quote(attachment_id, safe="")
    ver = 3 if version == 3 else 2
    url = f"{base}/rest/api/{ver}/attachment/{q}"
    try:
        r = s.get(url, timeout=60, headers={"Accept": "application/json"})
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _resolve_attachment_download_url_from_404(
    s: requests.Session, jira_base: str, failed_url: str
) -> str | None:
    """When /attachment/content/{id} 404s, try GET /attachment/{id} metadata (v3 then v2)."""
    m = re.search(r"/attachment/content/([^/?#]+)", failed_url)
    if not m:
        return None
    att_id = urllib.parse.unquote(m.group(1))
    for v in (3, 2):
        meta = _fetch_attachment_json(s, jira_base, att_id, v)
        if meta and isinstance(meta, dict) and (meta.get("content") or "").strip():
            return (meta.get("content") or "").strip()
    return None


_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _uuid_from_string(s: str) -> str | None:
    m = _UUID_RE.search(s or "")
    return m.group(0).lower() if m else None


def _index_img_srcs_by_uuid_from_html(html: str, jira_base: str) -> dict[str, str]:
    """
    Jira’s rendered HTML often contains <img> with a working src (incl. api.atlassian.com);
    the same UUID may 404 on /rest/api/3/attachment/content/{uuid} when built from ADF.
    """
    out: dict[str, str] = {}
    if not (html and html.strip()):
        return out
    b = (jira_base or "").rstrip("/")
    for m in re.finditer(
        r"""<img[^>]+?src\s*=\s*["']([^"']+)["']""", html, re.I | re.DOTALL
    ):
        src = m.group(1).strip()
        if src.startswith("/"):
            src = f"{b}{src}"
        elif src.startswith("//"):
            src = f"https:{src}"
        if not src.startswith("http"):
            continue
        for u in _UUID_RE.findall(src):
            out.setdefault(u.lower(), src)
    return out


def _build_image_url_fallback_map(
    jira_base: str,
    data: dict,
    comments: list[dict] | None,
) -> dict[str, str]:
    """Map UUID (lowercase) -> img src URL from rendered description + comment HTML."""
    out: dict[str, str] = {}
    rf = data.get("renderedFields")
    if isinstance(rf, dict):
        for _k, val in rf.items():
            if isinstance(val, str) and "<img" in val.lower():
                out.update(_index_img_srcs_by_uuid_from_html(val, jira_base))
    if comments:
        for c in comments:
            if not isinstance(c, dict):
                continue
            rb = c.get("renderedBody")
            if isinstance(rb, str) and "<img" in rb.lower():
                out.update(_index_img_srcs_by_uuid_from_html(rb, jira_base))
    return out


# Max file size to embed (avoid huge binaries)
_EMBED_IMAGES_MAX_BYTES = 25 * 1024 * 1024
_IMG_CONTENT_TYPE_TO_EXT: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
}


def _jira_path_looks_embeddable(urlpath: str) -> bool:
    p = (urlpath or "").lower()
    if "/rest/api/3/attachment/content/" in p or "/rest/api/2/attachment/content/" in p:
        return True
    if "/rest/api/3/attachment/thumbnail/" in p or "/rest/api/2/attachment/thumbnail/" in p:
        return True
    if "/secure/attachment/" in p:
        return True
    return False


def _url_allowed_for_jira_image_embed(url: str, jira_base: str) -> bool:
    """Allow site host, or api.atlassian.com when path is Jira attachment (common for content URL)."""
    try:
        u = urllib.parse.urlparse(url)
        if u.scheme not in ("http", "https") or not u.netloc:
            return False
        b = urllib.parse.urlparse(
            jira_base if "://" in (jira_base or "") else f"https://{jira_base or ''}"
        )
        p = u.path or ""
        if u.netloc == b.netloc:
            return _jira_path_looks_embeddable(p)
        if u.netloc in ("api.atlassian.com", "api.atlassian.net"):
            return "/attachment/content/" in p or "/attachment/thumbnail/" in p
        return False
    except Exception:
        return False


def _url_ok_for_image_download(
    url: str, jira_base: str, img_fallback: dict[str, str] | None
) -> bool:
    """Allow standard Jira image URLs, or a URL we indexed from Jira’s own rendered HTML."""
    if _url_allowed_for_jira_image_embed(url, jira_base):
        return True
    if img_fallback and any(v == url for v in img_fallback.values()):
        return True
    return False


def _ext_from_content_type(ct: str) -> str:
    c = (ct or "").split(";")[0].strip().lower()
    if c in _IMG_CONTENT_TYPE_TO_EXT:
        return _IMG_CONTENT_TYPE_TO_EXT[c]
    if "png" in c:
        return ".png"
    if "jpeg" in c or c.endswith("/jpg"):
        return ".jpg"
    if "gif" in c:
        return ".gif"
    if "svg" in c:
        return ".svg"
    if "webp" in c:
        return ".webp"
    return ".bin"


def _embed_images_in_markdown(
    md: str,
    s: requests.Session,
    jira_base: str,
    assets_dir: Path,
    rel_asset_dir: str,
    img_fallback: dict[str, str] | None = None,
) -> tuple[str, int]:
    """
    Replace ![](https://jira/...) with local files under assets_dir, using paths relative
    to the .md (rel_asset_dir/filename). Only same-host Jira attachment / secure URLs.
    """
    if not (md and md.strip()):
        return md, 0
    jira_base = (jira_base or "").rstrip("/")
    assets_dir.mkdir(parents=True, exist_ok=True)
    used: dict[str, str] = {}
    n_downloaded = [0]
    pattern = re.compile(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)")

    def repl(m: re.Match[str]) -> str:
        alt = m.group(1)
        url = m.group(2).strip()
        if not _url_ok_for_image_download(url, jira_base, img_fallback):
            return m.group(0)
        pth = urllib.parse.urlparse(url).path
        if not _jira_path_looks_embeddable(pth) and "api.atlassian" not in url:
            if not (img_fallback and url in img_fallback.values()):
                return m.group(0)
        if url in used:
            return f"![{alt}]({used[url]})"
        try:
            resp = s.get(
                url, timeout=120, stream=True, headers={"Accept": "*/*"}
            )
            if resp.status_code == 404:
                resp.close()
                alt_url = _resolve_attachment_download_url_from_404(
                    s, jira_base, url
                )
                if (not alt_url or alt_url == url) and img_fallback:
                    uq = _uuid_from_string(url)
                    if uq and uq in img_fallback:
                        alt_url = img_fallback[uq]
                if not alt_url or alt_url == url:
                    print(
                        f"Warning: image {url[:90]} (no attachment metadata URL)",
                        file=sys.stderr,
                    )
                    return m.group(0)
                if not _url_ok_for_image_download(alt_url, jira_base, img_fallback):
                    print(
                        f"Warning: image {url[:90]} (fallback URL not allowed)",
                        file=sys.stderr,
                    )
                    return m.group(0)
                resp = s.get(
                    alt_url, timeout=120, stream=True, headers={"Accept": "*/*"}
                )
            if resp.status_code != 200:
                print(
                    f"Warning: image {url[:90]}... -> {resp.status_code}",
                    file=sys.stderr,
                )
                try:
                    resp.close()
                except Exception:
                    pass
                return m.group(0)
            buf = bytearray()
            for chunk in resp.iter_content(65536):
                if chunk:
                    buf.extend(chunk)
                if len(buf) > _EMBED_IMAGES_MAX_BYTES:
                    print(
                        f"Warning: image too large, skip: {url[:90]}",
                        file=sys.stderr,
                    )
                    resp.close()
                    return m.group(0)
            ct = (resp.headers.get("content-type") or "").split(";")[0]
            resp.close()
            data = bytes(buf)
        except Exception as ex:
            print(f"Warning: image download failed: {ex}", file=sys.stderr)
            return m.group(0)
        n_downloaded[0] += 1
        idx = n_downloaded[0]
        fname = f"img_{idx:04d}{_ext_from_content_type(ct)}"
        fpath = assets_dir / fname
        try:
            fpath.write_bytes(data)
        except OSError as ex:
            n_downloaded[0] -= 1
            print(f"Warning: could not write {fpath}: {ex}", file=sys.stderr)
            return m.group(0)
        rel = f"{rel_asset_dir.rstrip('/').replace(chr(92), '/')}/{fname}"
        used[url] = rel
        return f"![{alt}]({rel})"

    new_md = pattern.sub(repl, md)
    return new_md, n_downloaded[0]


def _html_to_markdown(html: str | None) -> str:
    if not html:
        return ""
    if _h is not None:
        return _h.handle(html).strip()
    # Fallback: very rough tag strip
    t = re.sub(r"(?i)<br\s*/?>", "\n", html)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+\n", "\n", unescape(t)).strip()


def _append_imgs_from_html(html: str, jira_base: str) -> str:
    """
    Jira’s rendered body often contains <img src="...">. html2text may drop them; append as Markdown
    so viewers can load the same URL (may require Jira login).
    """
    if not (html and jira_base and html.strip().lower().count("<img")):
        return ""
    b = jira_base.rstrip("/")
    extra: list[str] = []
    for m in re.finditer(
        r"<img\b[^>]*?>", html, re.I | re.DOTALL
    ):
        tag = m.group(0)
        sm = re.search(r'\bsrc\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        if not sm:
            continue
        src = sm.group(1).strip()
        if src.startswith("/"):
            src = f"{b}{src}"
        elif src.startswith("//"):
            src = f"https:{src}"
        if not src.startswith("http"):
            continue
        am = re.search(r'\balt\s*=\s*["\']([^"\']*)["\']', tag, re.I)
        alt = (am.group(1) if am else "image") or "image"
        extra.append(f"\n\n![{alt}]({src})")
    return "".join(extra)


def _apply_text_marks(node: dict) -> str:
    text = str(node.get("text", ""))
    marks = node.get("marks") or []
    if not isinstance(marks, list):
        return text
    out = text
    for m in marks:
        if not isinstance(m, dict):
            continue
        if m.get("type") == "link":
            href = (m.get("attrs") or {}).get("href", "") or ""
            if href:
                out = f"[{out}]({href})"
        elif m.get("type") in ("code", "strong", "em", "underline", "strike"):
            t = m.get("type")
            if t == "strong":
                out = f"**{out}**"
            elif t == "em":
                out = f"*{out}*"
            elif t == "code":
                out = f"`{out}`"
    return out


def _adf_to_markdownish(
    adf: dict | None,
    jira_base: str | None = None,
    attachments: list[dict] | None = None,
) -> str:
    """Best-effort Markdown from Atlassian Document Format (API v3). Pass jira_base and issue attachments for image URLs."""
    if not adf or not isinstance(adf, dict):
        return ""

    parts: list[str] = []
    jira = (jira_base or "").rstrip("/") if jira_base else ""
    atts = attachments if isinstance(attachments, list) else []

    def walk(node: object, list_depth: int = 0) -> None:
        if isinstance(node, dict):
            t = node.get("type")
            if t == "text" and "text" in node:
                parts.append(_apply_text_marks(node))
            elif t == "hardBreak":
                parts.append("\n")
            elif t == "emoji":
                a = node.get("attrs") or {}
                e = a.get("text") or a.get("shortName") or ""
                if e:
                    parts.append(str(e))
            elif t == "mention":
                a = node.get("attrs") or {}
                label = a.get("text") or a.get("displayName") or a.get("id") or "user"
                parts.append(f"@{label}")
            elif t in ("media",):
                a = node.get("attrs") or {}
                url = ""
                if jira:
                    url = (_media_image_url(a, jira, atts) or "").strip()
                alt = a.get("alt") or a.get("filename") or "image"
                if url:
                    parts.append(f"\n\n![{alt}]({url})\n\n")
                elif a.get("id") is not None:
                    parts.append(f"\n[attachment:{a.get('id')}]\n\n")
            elif t in ("mediaSingle", "mediaGroup", "mediaInline"):
                for c in node.get("content") or ():
                    walk(c, list_depth)
                parts.append("\n")
            elif t in ("heading",):
                level = 1
                try:
                    level = int((node.get("attrs") or {}).get("level", 1))
                except (TypeError, ValueError):
                    level = 1
                parts.append("\n" + ("#" * min(level, 6)) + " ")
                for c in node.get("content") or ():
                    walk(c, list_depth)
                parts.append("\n\n")
            elif t in ("paragraph", "blockquote"):
                for c in node.get("content") or ():
                    walk(c, list_depth)
                parts.append("\n\n")
            elif t in ("bulletList", "orderedList"):
                for c in node.get("content") or ():
                    walk(c, list_depth)
            elif t == "listItem":
                parts.append("  " * list_depth + "- ")
                for c in node.get("content") or ():
                    walk(c, list_depth + 1)
                parts.append("\n")
            elif t in ("codeBlock",):
                a = node.get("attrs") or {}
                lang = a.get("language", "") or ""
                body = a.get("text", "")
                if not body and (node.get("content")):
                    ch: list[str] = []

                    def code_collect(n: object) -> None:
                        if isinstance(n, dict) and n.get("type") == "text":
                            ch.append(str(n.get("text", "")))
                        elif isinstance(n, dict) and n.get("content"):
                            for x in n["content"] or ():
                                code_collect(x)
                        elif isinstance(n, list):
                            for x in n:
                                code_collect(x)

                    for c in node.get("content") or ():
                        code_collect(c)
                    body = "".join(ch)
                fence = "```"
                parts.append(f"\n{fence}{lang}\n{body}\n{fence}\n\n")
            elif t in ("decisionList", "decisionItem", "panel", "layoutSection", "column", "table", "tableRow", "tableCell", "tableHeader", "extension", "bodiedExtension"):
                for c in node.get("content") or ():
                    walk(c, list_depth)
                parts.append("\n")
            elif t == "doc":
                for c in node.get("content") or ():
                    walk(c, list_depth)
            else:
                for c in node.get("content") or ():
                    walk(c, list_depth)
        elif isinstance(node, list):
            for c in node:
                walk(c, list_depth)

    walk(adf, 0)
    s = "".join(parts)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def _adf_to_plain(adf: dict | None) -> str:
    return _adf_to_markdownish(adf, None, None)


def _format_simple_field(f: dict, key: str) -> str | None:
    """Human-readable one-line value for common Jira field shapes, or None."""
    v = f.get(key)
    if v is None:
        return None
    if isinstance(v, str) and v.strip():
        return v
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list) and v:
        if all(isinstance(x, str) for x in v):
            return ", ".join(v)
        if all(isinstance(x, dict) and "name" in x for x in v):
            return ", ".join(str(x.get("name")) for x in v)
    if isinstance(v, dict):
        for k in ("displayName", "name", "value", "key"):
            if v.get(k) is not None:
                return str(v.get(k))
    return None


def _parse_csv_patterns(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def _field_display_matches_any(display_name: str, substrings: list[str]) -> bool:
    """True if the field *display name* contains any of the substrings (case-insensitive)."""
    t = (display_name or "").strip().lower()
    for sub in substrings:
        subl = sub.strip().lower()
        if subl and subl in t:
            return True
    return False


def _split_grouped_rich_text(
    sections: list[tuple[str, str]], include_substrings: list[str]
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """
    First list: fields whose display name matches --group-include.
    Second list: all other long-form fields (each becomes ## on its own in flat, or after the group in grouped).
    """
    grouped: list[tuple[str, str]] = []
    other: list[tuple[str, str]] = []
    for title, body in sections:
        if _field_display_matches_any(title, include_substrings):
            grouped.append((title, body))
        else:
            other.append((title, body))

    def grouped_order(item: tuple[str, str]) -> tuple[int, str]:
        title = item[0].strip().lower()
        if title == "description":
            return (0, title)
        if "acceptance" in title:
            return (1, title)
        return (2, item[0].lower())

    grouped.sort(key=grouped_order)
    other.sort(key=lambda x: x[0].lower())
    return grouped, other


def _order_flat_rich_text(sections: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Default layout: Description first, then all other fields alphabetically by display name."""
    desc = [x for x in sections if x[0].strip().lower() == "description"]
    rest = sorted(
        (x for x in sections if x[0].strip().lower() != "description"),
        key=lambda x: x[0].lower(),
    )
    return desc + rest


def _format_attachments_md(f: dict, jira_browse_base: str) -> list[str]:
    lines: list[str] = []
    atts = f.get("attachment") or []
    if not isinstance(atts, list) or not atts:
        lines.append("_(none)_")
        return lines
    for a in atts:
        if not isinstance(a, dict):
            continue
        fn = a.get("filename") or "file"
        url = a.get("content") or ""
        if not url and a.get("self"):
            url = a.get("self")
        size = a.get("size")
        mime = a.get("mimeType") or ""
        created = a.get("created") or ""
        author = ((a.get("author") or {}) or {}).get("displayName") or ""
        meta_bits = [x for x in (author, created) if x]
        if isinstance(size, int):
            meta_bits.append(f"{size} bytes")
        if mime:
            meta_bits.append(mime)
        meta = " — ".join(meta_bits) if meta_bits else ""
        # content URL is API URL; works with same auth in browser when logged in; still useful in MD
        safe_fn = fn.replace("]", "\\]")
        if url:
            lines.append(f"- [{safe_fn}]({url}){(' ' + meta) if meta else ''}")
        else:
            lines.append(f"- {safe_fn}{(' ' + meta) if meta else ''}")
    return lines


def _enrich_subtasks(
    s: requests.Session, base: str, parent_key: str, f: dict
) -> list[dict]:
    subs = f.get("subtasks") or []
    if not isinstance(subs, list) or not subs:
        return []
    missing = [
        st for st in subs if not ((st.get("fields") or {}).get("summary")) and st.get("key")
    ]
    if not missing:
        return subs
    try:
        data = _api_get(
            s,
            base,
            "/search",
            params={
                "jql": f'parent = "{parent_key}"',
                "fields": "summary,status,issuetype",
                "maxResults": 100,
            },
        )
    except Exception:
        try:
            data = _api_get(
                s,
                base,
                "/search",
                params={
                    "jql": f"parent = {parent_key}",
                    "fields": "summary,status,issuetype",
                    "maxResults": 100,
                },
            )
        except Exception:
            return subs
    by_key = {i.get("key"): i for i in (data.get("issues") or []) if i.get("key")}
    if not by_key:
        st_keys = [st.get("key") for st in subs if st.get("key")]
        if st_keys:
            inj = ", ".join(f'"{k}"' for k in st_keys)
            try:
                data = _api_get(
                    s,
                    base,
                    "/search",
                    params={
                        "jql": f"key in ({inj})",
                        "fields": "summary,status,issuetype,parent",
                        "maxResults": 100,
                    },
                )
                by_key = {
                    i.get("key"): i
                    for i in (data.get("issues") or [])
                    if i.get("key")
                }
            except Exception:
                by_key = {}
    out: list[dict] = []
    for st in subs:
        k = st.get("key")
        if k and k in by_key:
            merged_fields = {**(st.get("fields") or {}), **(by_key[k].get("fields") or {})}
            out.append({**st, "fields": merged_fields})
        else:
            out.append(st)
    return out


def _format_subtasks_md(subs: list[dict], jira_browse_base: str) -> list[str]:
    if not subs:
        return ["_(none)_"]
    lines: list[str] = []
    for st in subs:
        if not isinstance(st, dict):
            continue
        k = st.get("key") or ""
        sf = st.get("fields") or {}
        summ = sf.get("summary") or ""
        st_name = ((sf.get("status") or {}) or {}).get("name") or ""
        it = ((sf.get("issuetype") or {}) or {}).get("name") or ""
        url = f"{jira_browse_base.rstrip('/')}/browse/{k}" if k else ""
        bits = [f"[{k}]({url})"] if k else []
        if summ:
            bits.append(summ)
        head = " ".join(bits) if bits else k
        extra = " — ".join(x for x in (it, st_name) if x)
        if extra:
            lines.append(f"- {head} ({extra})")
        else:
            lines.append(f"- {head}")
    return lines


def _format_issue_links_md(f: dict, jira_browse_base: str) -> list[str]:
    links = f.get("issuelinks") or []
    if not isinstance(links, list) or not links:
        return ["_(none)_"]
    lines: list[str] = []
    for il in links:
        if not isinstance(il, dict):
            continue
        typ = (il.get("type") or {}) or {}
        inward = il.get("inwardIssue")
        outward = il.get("outwardIssue")
        if inward:
            rel = (typ.get("inward") or typ.get("name") or "relates to").strip()
            iss = inward
        elif outward:
            rel = (typ.get("outward") or typ.get("name") or "relates to").strip()
            iss = outward
        else:
            continue
        k = iss.get("key") or ""
        sf = iss.get("fields") or {}
        summ = sf.get("summary") or ""
        url = f"{jira_browse_base.rstrip('/')}/browse/{k}" if k else ""
        if k and url:
            line = f"- **{rel}** [{k}]({url})"
            if summ:
                line += f" — {summ}"
            lines.append(line)
        elif k:
            line = f"- **{rel}** `{k}`"
            if summ:
                line += f" — {summ}"
            lines.append(line)
    return lines if lines else ["_(none)_"]


def _comment_body_to_md(
    c: dict,
    jira_base: str | None = None,
    attachments: list[dict] | None = None,
) -> str:
    body = c.get("body")
    if isinstance(body, dict) and body.get("type") == "doc":
        return _adf_to_markdownish(body, jira_base, attachments) or "_(empty)_"
    if isinstance(body, str):
        return body
    return "_(empty)_"


def _build_comment_tree(comments: list[dict]) -> list[dict]:
    """
    Flat comment list -> forest of roots using parentId (Jira Cloud threaded replies).
    See: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-comments/
    """
    by_id: dict[str, dict] = {}
    for c in comments:
        if not isinstance(c, dict) or c.get("id") is None:
            continue
        sid = str(c.get("id"))
        by_id[sid] = {**c, "children": []}
    child_ids: set[str] = set()
    for c in comments:
        if not isinstance(c, dict) or c.get("id") is None:
            continue
        sid = str(c.get("id"))
        node = by_id.get(sid)
        if not node:
            continue
        raw_p = c.get("parentId")
        if raw_p is None and isinstance(c.get("parent"), dict):
            raw_p = (c.get("parent") or {}).get("id")
        pid = str(raw_p) if raw_p is not None else None
        if pid and pid in by_id:
            child_ids.add(sid)
            by_id[pid]["children"].append(node)
    roots = [n for i, n in by_id.items() if i not in child_ids]

    def sort_key(n: dict) -> tuple[str, str]:
        return (n.get("created") or "", str(n.get("id", "")))

    for n in by_id.values():
        (n.get("children") or []).sort(key=sort_key)
    roots.sort(key=sort_key)
    return roots


def _format_comment_node(
    c: dict,
    depth: int,
    jira_browse: str,
    issue_key: str,
    jira_base: str,
    attachments: list[dict] | None,
) -> list[str]:
    """One comment + nested replies (depth 0 = root, 1+ = blockquoted with > )."""
    if not isinstance(c, dict):
        return []
    auth = ((c.get("author") or {}) or {}).get("displayName") or "?"
    created = c.get("created") or ""
    cid = c.get("id")
    anchor = f"{jira_browse.rstrip('/')}/browse/{issue_key}"
    if cid is not None:
        anchor = f"{anchor}?focusedCommentId={cid}"
    head = f"**{auth}** · {created}  [Jira]({anchor})"
    if depth > 0:
        head = f"**↳** {head}"
    body = _comment_body_to_md(c, jira_base, attachments)
    block = f"{head}\n\n{body}"
    pfx = "> " * depth if depth else ""
    lines_out: list[str] = []
    for line in block.splitlines():
        lines_out.append(f"{pfx}{line}" if pfx else line)
    for ch in c.get("children") or []:
        lines_out.extend(
            _format_comment_node(
                ch, depth + 1, jira_browse, issue_key, jira_base, attachments
            )
        )
    return lines_out


def _fetch_all_comments(
    s: requests.Session,
    base: str,
    issue_key: str,
    *,
    expand_rendered: bool = False,
) -> list[dict]:
    """
    Load all comments. When expand_rendered is True, tries expand=renderedBody first
    (HTML with working <img src> for --embed-images fallbacks), then falls back to
    standard params (same as before: orderBy, then minimal params).
    """
    qk = urllib.parse.quote(issue_key, safe="")
    api_url = f"{base}/rest/api/3/issue/{qk}/comment"
    page = 100
    strategies: list[dict] = [
        {"orderBy": "created", "expand": "renderedBody"},
        {"orderBy": "created"},
        {},
    ]
    if not expand_rendered:
        strategies = [
            {"orderBy": "created"},
            {},
        ]
    all_c: list[dict] = []
    start = 0
    chosen: dict | None = None
    while True:
        if chosen is None and start == 0:
            last_r: requests.Response | None = None
            for extra in strategies:
                params = {"startAt": 0, "maxResults": page, **extra}
                last_r = s.get(api_url, params=params, timeout=60)
                if last_r.status_code == 200:
                    chosen = extra
                    data = last_r.json()
                    break
            else:
                if last_r is not None:
                    print(
                        f"GET {api_url} -> {last_r.status_code}\n{last_r.text[:2000]}",
                        file=sys.stderr,
                    )
                    last_r.raise_for_status()
                return []
        else:
            assert chosen is not None
            params = {"startAt": start, "maxResults": page, **chosen}
            r = s.get(api_url, params=params, timeout=60)
            if r.status_code != 200:
                print(
                    f"GET {api_url} -> {r.status_code}\n{r.text[:2000]}",
                    file=sys.stderr,
                )
                r.raise_for_status()
            data = r.json()
        chunk = data.get("comments") or []
        all_c.extend(chunk)
        total = data.get("total")
        if total is not None:
            if start + len(chunk) >= int(total) or not chunk:
                break
        else:
            if not chunk or len(chunk) < page:
                break
        start += len(chunk)
    return all_c


def _format_comments_md(
    comments: list[dict],
    jira_browse_base: str,
    issue_key: str,
    jira_base: str,
    attachments: list[dict] | None = None,
) -> list[str]:
    if not comments:
        return ["_(none)_"]
    tree = _build_comment_tree(comments)
    lines: list[str] = []
    for r in tree:
        lines.extend(
            _format_comment_node(
                r, 0, jira_browse_base, issue_key, jira_base, attachments
            )
        )
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def _extra_adf_sections(
    f: dict,
    names: dict,
    already_field_ids: set[str],
    jira_base: str | None = None,
    attachments: list[dict] | None = None,
) -> list[tuple[str, str]]:
    """
    If a rich-text custom field has no entry in renderedFields, still try ADF in `fields`
    (e.g. some tenant configs).
    """
    out: list[tuple[str, str]] = []
    for kid, v in f.items():
        if kid in already_field_ids or kid in (
            "description",
            "summary",
            "issuetype",
            "status",
            "priority",
            "assignee",
            "reporter",
            "created",
            "updated",
            "labels",
            "resolution",
        ):
            continue
        if not isinstance(v, dict) or v.get("type") != "doc":
            continue
        if not (v.get("content")):
            continue
        title = names.get(kid) or kid
        body = _adf_to_markdownish(v, jira_base, attachments)
        if body:
            out.append((title, body))
    out.sort(key=lambda t: t[0].lower())
    return out


def _issue_to_md(
    data: dict,
    jira_browse_base: str,
    *,
    subtasks: list[dict] | None = None,
    comments: list[dict] | None = None,  # None = do not print ## Comments; [] = no comments
    layout: str = "flat",
    group_title: str = "Key details",
    group_include: list[str] | None = None,
    omit_empty_structural: bool = False,
) -> str:
    key = data.get("key", "")
    f = data.get("fields") or {}
    names = data.get("names") or {}
    issue_atts = f.get("attachment") if isinstance(f.get("attachment"), list) else []
    summ = f.get("summary") or ""
    st = (f.get("status") or {}).get("name") or ""
    it = (f.get("issuetype") or {}).get("name") or ""
    assignee = (f.get("assignee") or {}) or None
    assignee_n = (assignee or {}).get("displayName", "") or "Unassigned"
    reporter = (f.get("reporter") or {}) or None
    reporter_n = (reporter or {}).get("displayName", "") or ""
    resolution = (f.get("resolution") or {}) or None
    resolution_n = (resolution or {}).get("name", "") or ""
    priority = (f.get("priority") or {}).get("name") or ""
    created = f.get("created") or ""
    updated = f.get("updated") or ""
    self_url = f"{jira_browse_base.rstrip('/')}/browse/{key}"

    rendered = data.get("renderedFields") or {}
    if not isinstance(rendered, dict):
        rendered = {}

    # Build Description body
    body_md = ""
    if rendered.get("description"):
        raw_d = str(rendered["description"])
        body_md = _html_to_markdown(raw_d)
        body_md = body_md + _append_imgs_from_html(raw_d, jira_browse_base)
    else:
        desc = f.get("description")
        if isinstance(desc, str):
            body_md = desc
        else:
            body_md = _adf_to_markdownish(
                desc if isinstance(desc, dict) else None,
                jira_browse_base,
                issue_atts,
            )

    # Rich-text field sections: use Jira’s display names from `names` (same as UI field labels)
    desc_label = (names.get("description") or "Description").strip() or "Description"
    content_sections: list[tuple[str, str]] = [
        (desc_label, body_md or "_(empty)_")
    ]
    other_ids: list[str] = [
        k
        for k in rendered
        if k != "description" and isinstance(rendered.get(k), str) and (rendered[k] or "").strip()
    ]
    other_ids.sort(key=lambda kid: (names.get(kid) or kid).lower())
    for kid in other_ids:
        raw = str(rendered[kid])
        hmd = _html_to_markdown(raw) + _append_imgs_from_html(raw, jira_browse_base)
        content_sections.append((names.get(kid) or kid, hmd))
    already_for_body = set(other_ids) | {"description"}
    for title, adf_body in _extra_adf_sections(
        f, names, already_for_body, jira_browse_base, issue_atts
    ):
        content_sections.append((title, adf_body))

    if layout == "grouped":
        include = (
            group_include
            if group_include is not None
            else list(BUILTIN_GROUP_SUBSTRINGS)
        )
        grouped_rich, other_rich_sections = _split_grouped_rich_text(
            content_sections, include
        )
    else:
        grouped_rich, other_rich_sections = ([], [])

    labels = f.get("labels") or []
    if isinstance(labels, list):
        labels_s = ", ".join(str(x) for x in labels)
    else:
        labels_s = str(labels)

    top_lines: list[str] = [
        f"# {key}: {summ}",
        "",
        f"- **Jira:** [{key}]({self_url})",
        f"- **Type:** {it}",
        f"- **Status:** {st}",
    ]
    if resolution_n:
        top_lines.append(f"- **Resolution:** {resolution_n}")
    top_lines.extend(
        [
            f"- **Priority:** {priority}",
            f"- **Assignee:** {assignee_n}",
        ]
    )
    if reporter_n:
        top_lines.append(f"- **Reporter:** {reporter_n}")
    top_lines.extend(
        [
            f"- **Created:** {created}",
            f"- **Updated:** {updated}",
        ]
    )
    if labels_s:
        top_lines.append(f"- **Labels:** {labels_s}")
    for sec_title, val in _extra_metadata_lines(f, names):
        top_lines.append(f"- **{sec_title}:** {val}")

    out: list[str] = list(top_lines)

    # Rich text: default flat (## per field). Optional grouped: ## group_title + ### for matched fields.
    if layout == "grouped":
        if grouped_rich:
            out.extend(["", f"## {group_title.strip() or 'Key details'}", ""])
            for sec_title, text in grouped_rich:
                out.append(f"### {sec_title}")
                out.append("")
                out.append(text)
                out.append("")
        for title, text in other_rich_sections:
            out.extend([f"## {title}", "", text, ""])
    else:
        for title, text in _order_flat_rich_text(content_sections):
            out.extend([f"## {title}", "", text, ""])

    atts = f.get("attachment") or []
    has_atts = isinstance(atts, list) and len(atts) > 0
    has_subs = bool(subtasks)
    has_links = bool(
        f.get("issuelinks")
        and isinstance(f.get("issuelinks"), list)
        and len(f.get("issuelinks") or []) > 0
    )
    has_comments = bool(comments)

    if not (omit_empty_structural and not has_atts):
        out.extend(
            [
                "## Attachments",
                "",
                *_format_attachments_md(f, jira_browse_base),
                "",
            ]
        )
    if not (omit_empty_structural and not has_subs):
        out.extend(
            [
                "## Subtasks",
                "",
                *_format_subtasks_md(subtasks or [], jira_browse_base),
                "",
            ]
        )
    if not (omit_empty_structural and not has_links):
        out.extend(
            [
                "## Linked work items",
                "",
                *_format_issue_links_md(f, jira_browse_base),
                "",
            ]
        )

    if comments is not None and not (omit_empty_structural and not has_comments):
        out.extend(
            [
                "## Comments",
                "",
                *_format_comments_md(
                    comments,
                    jira_browse_base,
                    key,
                    jira_browse_base,
                    issue_atts,
                ),
            ]
        )
    return "\n".join(out).rstrip() + "\n"


def _extra_metadata_lines(
    f: dict, names: dict, max_extra: int = 40
) -> list[tuple[str, str]]:
    """Emit simple (name, value) for remaining custom / visible fields not already in the header."""
    done = {
        "summary",
        "issuetype",
        "status",
        "priority",
        "assignee",
        "reporter",
        "created",
        "updated",
        "labels",
        "resolution",
        "description",
        "attachment",
        "subtasks",
        "issuelinks",
        "comment",
        "worklog",
    }
    out: list[tuple[str, str]] = []
    for kid, v in f.items():
        if kid in done or v is None:
            continue
        if (
            kid.startswith("customfield_")
            and isinstance(v, dict)
            and v.get("type") == "doc"
        ):
            continue  # long text exported as section
        s = _format_simple_field(f, kid)
        if s:
            label = names.get(kid) or kid
            out.append((label, s))
    out.sort(key=lambda t: t[0].lower())
    return out[:max_extra]


def _filename_safe(name: str) -> str:
    s = re.sub(r'[<>:"/\\|?*]', "_", name)[:200]
    return s or "issue"


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Jira Cloud issues to Markdown")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--key", "-k", help="Issue key, e.g. CT-9341")
    g.add_argument("--jql", "-j", help="JQL to search (max 50 by default)")
    parser.add_argument(
        "--out", "-o", type=Path, default=Path("jira_export"), help="Output directory"
    )
    parser.add_argument(
        "--max", "-m", type=int, default=50, help="Max results for --jql"
    )
    parser.add_argument(
        "--dump-raw",
        action="store_true",
        help="Also write <KEY>_raw.json next to the .md (debugging)",
    )
    parser.add_argument(
        "--skip-comments",
        action="store_true",
        help="Do not call the comments API (no ## Comments section)",
    )
    layout_default = (os.environ.get("JIRA_EXPORT_LAYOUT") or "flat").lower()
    if layout_default not in ("flat", "grouped"):
        layout_default = "flat"
    parser.add_argument(
        "--layout",
        choices=["flat", "grouped"],
        default=layout_default,
        help="flat: one ## per rich-text field; section titles are always Jira’s field display "
        "names from the API (default). "
        "grouped: optional nesting under --group-title using BUILTIN patterns or --group-include.",
    )
    parser.add_argument(
        "--group-title",
        default=os.environ.get("JIRA_EXPORT_GROUP_TITLE", "Key details"),
        help="With --layout grouped: parent ## heading (default: Key details).",
    )
    env_gi = os.environ.get("JIRA_EXPORT_GROUP_INCLUDE")
    parser.add_argument(
        "--group-include",
        default=env_gi if env_gi and env_gi.strip() else None,
        metavar="PATTERNS",
        help="With --layout grouped: optional override — comma-separated substrings; if a field's "
        "display name from Jira contains any (case-insensitive), it is nested as ### under "
        "--group-title. If you omit this flag (and the env), built-in common patterns are used. "
        "With flat, ignored.",
    )
    parser.add_argument(
        "--omit-empty",
        action="store_true",
        help="Skip empty Attachments / Subtasks / Linked work items / Comments sections",
    )
    parser.add_argument(
        "--embed-images",
        action="store_true",
        help="Download images from ![](jira attachment/secure URLs) into <markdown_stem>_files/, "
        "rewrite Markdown to relative paths (same session auth; max ~25 MB per file).",
    )
    args = parser.parse_args()

    base, email, token = _config()
    s = _session(base, email, token)
    jira_browse = os.environ.get("JIRA_BASE", "https://wiley-global.atlassian.net").rstrip(
        "/"
    )
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    issues: list[dict] = []
    if args.key:
        data = _api_get(
            s,
            base,
            f"/issue/{urllib.parse.quote(args.key, safe='')}",
            params={
                "fields": "*all",
                "expand": "names,renderedFields",
            },
        )
        issues = [data]
    else:
        jql = args.jql
        search = _api_get(
            s,
            base,
            "/search",
            params={
                "jql": jql,
                "maxResults": args.max,
                # *all: include custom fields (e.g. Acceptance criteria); narrow fields drop them
                "fields": "*all",
                "expand": "names,renderedFields",
            },
        )
        issues = list(search.get("issues") or [])

    for data in issues:
        key = data.get("key", "UNKNOWN")
        f = data.get("fields") or {}
        summ = f.get("summary") or key
        sub_list = _enrich_subtasks(s, base, key, f)
        comm: list[dict] | None = None
        if not args.skip_comments:
            comm = []
            try:
                comm = _fetch_all_comments(
                    s, base, key, expand_rendered=bool(args.embed_images)
                )
            except Exception as ex:
                print(f"Warning: could not load comments for {key}: {ex}", file=sys.stderr)
        group_list: list[str] | None = None
        if args.layout == "grouped":
            override = args.group_include
            if override and str(override).strip():
                group_list = _parse_csv_patterns(str(override)) or list(
                    BUILTIN_GROUP_SUBSTRINGS
                )
            else:
                group_list = list(BUILTIN_GROUP_SUBSTRINGS)
        md = _issue_to_md(
            data,
            jira_browse,
            subtasks=sub_list,
            comments=comm,
            layout=args.layout,
            group_title=args.group_title,
            group_include=group_list,
            omit_empty_structural=args.omit_empty,
        )
        name = f"{key}_{_filename_safe(summ)}.md"
        path = out_dir / name
        if args.embed_images:
            assets = out_dir / f"{path.stem}_files"
            rel = f"{path.stem}_files"
            img_fb = _build_image_url_fallback_map(
                jira_browse, data, comm
            )
            md, n_img = _embed_images_in_markdown(
                md, s, jira_browse, assets, rel, img_fallback=img_fb or None
            )
            if n_img:
                print(f"Embedded {n_img} image(s) under {assets}")
        path.write_text(md, encoding="utf-8")
        print(f"Wrote {path}")
        if args.dump_raw:
            raw_path = out_dir / f"{key}_raw.json"
            raw_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"Wrote {raw_path}")

    stamp = out_dir / "_export_info.txt"
    stamp.write_text(
        f"Exported at: {datetime.now(timezone.utc).isoformat()}\nCount: {len(issues)}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
