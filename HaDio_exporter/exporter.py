"""Hackaday.io project exporter for Hugo page bundles.

This script downloads a Hackaday.io project (overview page and logs) and
converts the content to Markdown suitable for a Hugo page bundle. Assets such
as images are downloaded into the bundle directory and referenced locally.

Dependencies: requests, beautifulsoup4
"""

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup, NavigableString, Tag


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/115.0 Safari/537.36"
)
REQUEST_TIMEOUT = 20
MAX_DOWNLOAD_RETRIES = 3
RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
CONTENT_TYPE_EXTENSION = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


@dataclass
class LogEntry:
    title: str
    date: datetime
    content: str
    is_markdown: bool = False


def slugify(value: str) -> str:
    value = enforce_ascii(value.lower())
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "project"


REPLACEMENTS = {
    "\u2013": "-",
    "\u2014": "-",
    "\u2012": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
    "\u00a0": " ",
    "\u2212": "-",
    "\u2192": "->",
    "\u2190": "<-",
    "\u2191": "^",
    "\u2193": "v",
    "\u00b0": " deg",
    "\u00b2": "^2",
    "\u00b3": "^3",
    "\u2122": " (TM)",
    "\u00ae": " (R)",
    "\u00b5": "u",
    "\u03bc": "mu",
}


def enforce_ascii(value: str) -> str:
    if not value:
        return ""
    for src, dst in REPLACEMENTS.items():
        value = value.replace(src, dst)
    normalized = unicodedata.normalize("NFKD", value)
    ascii_bytes = normalized.encode("ascii", "ignore")
    return ascii_bytes.decode("ascii")


def clean_whitespace(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class AssetDownloader:
    def __init__(self, bundle_path: Path, session: requests.Session):
        self.bundle_path = bundle_path
        self.session = session
        self._by_url: Dict[str, str] = {}
        self._used_names: Dict[str, int] = {}
        self.failures: List[str] = []

    def download(self, url: str, preferred_filename: Optional[str] = None) -> str:
        if not url:
            raise ValueError("Empty asset URL")
        if url.startswith("//"):
            url = "https:" + url
        filename = self._by_url.get(url)
        if filename:
            return filename

        parsed = urlparse(url)
        basename = os.path.basename(parsed.path)
        basename = unquote(basename)
        if not basename:
            basename = "asset"

        if preferred_filename:
            preferred_root, preferred_ext = os.path.splitext(preferred_filename)
            if preferred_ext:
                root = preferred_root
                ext = preferred_ext
            else:
                root = preferred_filename
                ext = ""
        else:
            root, ext = os.path.splitext(basename)

        ext = ext.lower()
        if ext not in VALID_IMAGE_EXTENSIONS:
            ext = ""

        response = None
        for attempt in range(MAX_DOWNLOAD_RETRIES):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                status = response.status_code
                if status in RETRYABLE_STATUS_CODES and attempt < MAX_DOWNLOAD_RETRIES - 1:
                    time.sleep(1 + attempt)
                    continue
                response.raise_for_status()
                break
            except requests.RequestException:
                if attempt >= MAX_DOWNLOAD_RETRIES - 1:
                    raise
                time.sleep(1 + attempt)
        if response is None:
            raise requests.RequestException(f"Failed to download asset: {url}")

        if not ext:
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            ext = CONTENT_TYPE_EXTENSION.get(content_type, "")

        filename_candidate = root + (ext or "")
        filename = self._ensure_unique_name(filename_candidate)
        target_path = self.bundle_path / filename

        if not target_path.exists():
            target_path.write_bytes(response.content)

        self._by_url[url] = filename
        return filename

    def _ensure_unique_name(self, name: str) -> str:
        name = sanitize_filename(name)
        root, ext = os.path.splitext(name)
        ext = ext or ""
        count = self._used_names.get(name)
        if count is None:
            self._used_names[name] = 1
            return name
        while True:
            candidate = f"{root}_{count}{ext}"
            if not (self.bundle_path / candidate).exists() and candidate not in self._used_names:
                self._used_names[candidate] = count + 1
                self._used_names[name] = count + 1
                return candidate
            count += 1


def sanitize_filename(name: str) -> str:
    name = enforce_ascii(name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    name = name.strip("._") or "asset"
    return name


BLOCK_LEVEL_TAGS = {
    "p",
    "div",
    "section",
    "ul",
    "ol",
    "li",
    "figure",
    "pre",
    "table",
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
}


class MarkdownConverter:
    def __init__(self, asset_downloader: AssetDownloader, base_url: str):
        self.assets = asset_downloader
        self.base_url = base_url
        self._heading_offset = 0

    def convert(self, html_fragment: str, heading_offset: int = 0) -> str:
        previous_offset = self._heading_offset
        self._heading_offset = heading_offset
        soup = BeautifulSoup(html_fragment, "html.parser")
        parts: List[str] = []
        for child in soup.children:
            piece = self._convert_node(child)
            if piece:
                parts.append(piece)
        text = "".join(parts)
        text = self._collapse_blank_lines(text)
        self._heading_offset = previous_offset
        return text.strip()

    def _convert_node(self, node) -> str:
        if isinstance(node, NavigableString):
            text = enforce_ascii(html.unescape(str(node)))
            return text
        if not isinstance(node, Tag):
            return ""

        if node.name in {"script", "style"}:
            return ""
        classes = set(node.get("class", []))
        if "read-more-tag" in classes or "redactor-selection-marker" in classes:
            return ""

        name = node.name.lower()
        if name == "p":
            has_block_child = any(
                isinstance(child, Tag) and child.name and child.name.lower() in BLOCK_LEVEL_TAGS
                for child in node.children
            )
            if has_block_child:
                return self._convert_children(node)
            content = self._convert_children(node).strip()
            if not content:
                return ""
            return f"{content}\n\n"
        if name in {"div", "section"}:
            content = self._convert_children(node).strip()
            if not content:
                return ""
            return f"{content}\n\n"
        if name == "br":
            return "\n"
        if name in {"strong", "b"}:
            content = self._convert_children(node).strip()
            if not content:
                return ""
            return f"**{content}**"
        if name in {"em", "i"}:
            content = self._convert_children(node).strip()
            if not content:
                return ""
            return f"*{content}*"
        if name == "a":
            href = node.get("href")
            content = self._convert_children(node).strip()
            if href:
                href = self._resolve_url(href)
            if href:
                label = content or href
                return f"[{label}]({href})"
            return content
        if name in {"ul", "ol"}:
            lines = []
            for index, item in enumerate(node.find_all("li", recursive=False), start=1):
                bullet = "- " if name == "ul" else f"{index}. "
                lines.append(self._format_list_item(item, bullet))
            return "\n".join(filter(None, lines)) + "\n\n"
        if name == "li":
            return self._format_list_item(node, "- ") + "\n"
        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(name[1]) + self._heading_offset
            if level > 6:
                level = 6
            content = self._convert_children(node).strip()
            return f"{'#' * level} {content}\n\n"
        if name == "figure":
            img = node.find("img")
            caption = node.find("figcaption")
            image_markdown = self._convert_image(img, caption)
            extra_parts: List[str] = []
            for child in node.children:
                if child is img or child is caption:
                    continue
                if isinstance(child, Tag) and child.name == "figcaption":
                    continue
                extra = self._convert_node(child)
                if extra:
                    extra_parts.append(extra)
            return (image_markdown or "") + ("".join(extra_parts))
        if name == "img":
            return self._convert_image(node, None)
        if name == "iframe":
            return self._convert_iframe(node)
        if name == "blockquote":
            content = self._convert_children(node).strip()
            if not content:
                return ""
            quote_lines = [f"> {line}" for line in content.splitlines()]
            return "\n".join(quote_lines) + "\n\n"
        if name == "sup":
            content = self._convert_children(node).strip()
            return f"^{content}"
        if name == "sub":
            content = self._convert_children(node).strip()
            return f"~{content}~"
        if name == "pre":
            code = self._collect_code_text(node)
            language = self._detect_language(node)
            return f"```{language}\n{code}\n```\n\n"
        if name == "code":
            content = self._convert_children(node).strip()
            return f"`{content}`"
        if name in {"span"}:
            return self._convert_children(node)

        return self._convert_children(node)

    def _convert_children(self, node: Tag) -> str:
        parts: List[str] = []
        for child in node.children:
            piece = self._convert_node(child)
            if piece:
                parts.append(piece)
        return "".join(parts)

    def _format_list_item(self, node: Tag, bullet: str) -> str:
        content = self._convert_children(node).strip()
        if not content:
            return ""
        lines = content.splitlines()
        formatted = bullet + lines[0]
        if len(lines) > 1:
            rest = ["  " + line for line in lines[1:]]
            formatted += "\n" + "\n".join(rest)
        return formatted

    def _convert_image(self, img: Optional[Tag], caption: Optional[Tag]) -> str:
        if not img:
            return ""
        src = img.get("src") or img.get("data-src")
        if not src:
            return ""
        src = self._resolve_url(src)
        alt = img.get("alt", "").strip()
        caption_text = self._convert_children(caption).strip() if caption else ""
        display_text = alt or caption_text
        try:
            filename = self.assets.download(src)
        except requests.RequestException:
            self.assets.failures.append(src)
            if src.lower().endswith(".gif"):
                alt_attr = f' alt="{display_text}"' if display_text else ""
                return f"<img src=\"{src}\"{alt_attr} />\n\n"
            title_suffix = f' "{caption_text}"' if caption_text and caption_text != display_text else ""
            return f"![{display_text}]({src}{title_suffix})\n\n"

        if filename.lower().endswith(".gif"):
            alt_attr = f' alt="{display_text}"' if display_text else ""
            return f"<img src=\"{filename}\"{alt_attr} />\n\n"
        title_suffix = f' "{caption_text}"' if caption_text and caption_text != display_text else ""
        return f"![{display_text}]({filename}{title_suffix})\n\n"

    def _convert_iframe(self, iframe: Tag) -> str:
        src = iframe.get("src", "").strip()
        if not src:
            return ""
        src = self._resolve_url(src)
        youtube_match = re.search(r"youtube\.com/embed/([A-Za-z0-9_-]+)", src)
        if youtube_match:
            video_id = youtube_match.group(1)
            return f"{{{{< youtube {video_id} >}}}}\n\n"
        return f"[Embedded content]({src})\n\n"

    def _collect_code_text(self, pre: Tag) -> str:
        text = pre.get_text(separator="", strip=False)
        text = text.replace("\r", "")
        return enforce_ascii(text)

    def _detect_language(self, pre: Tag) -> str:
        classes = pre.get("class", [])
        for cls in classes:
            if cls == "hljs":
                continue
            if cls.startswith("language-"):
                return cls.split("-", 1)[1]
            if cls.isalpha():
                return cls
        return "text"

    def _resolve_url(self, url: str) -> str:
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return urljoin(self.base_url, url)
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return urljoin(self.base_url, url)

    def _collapse_blank_lines(self, text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"^[ \t]+$", "", text, flags=re.MULTILINE)
        return text.strip()


class HackadayExporter:
    def __init__(
        self,
        project_url: str,
        output_dir: Path,
        force: bool = False,
        retry_missing: bool = False,
    ):
        self.project_url = project_url
        self.output_dir = output_dir
        self.force = force
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
        })
        self.session.cookies.set("hio_locale", "en")
        parsed = urlparse(project_url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.project_id = self._extract_project_id(parsed.path)
        self.project_path = parsed.path.rstrip("/")
        self.project_slug = ""
        self.project_title = ""
        self.summary = ""
        self.created_date: Optional[datetime] = None
        self.hero_url: Optional[str] = None
        self.sections: List[Tuple[str, str]] = []
        self.logs: List[LogEntry] = []
        self.asset_downloader: Optional[AssetDownloader] = None
        self.converter: Optional[MarkdownConverter] = None
        self.summary_lines: List[str] = []
        self._log_cache: Dict[str, str] = {}
        self.log_urls: List[str] = []
        self.retry_missing = retry_missing
        self.missing_log_numbers: set[int] = set()
        self.existing_logs: Dict[int, LogEntry] = {}
        self.missing_log_urls: set[str] = set()

    def export(self) -> Path:
        project_soup = self._fetch_soup(self.project_url)
        self._parse_project(project_soup)

        bundle_slug = slugify(self.project_title)
        self.project_slug = bundle_slug
        bundle_dir = self.output_dir / bundle_slug
        if bundle_dir.exists() and not (self.force or self.retry_missing):
            raise SystemExit(f"Bundle {bundle_dir} already exists. Use --force to overwrite.")
        bundle_dir.mkdir(parents=True, exist_ok=True)

        if self.retry_missing:
            self._prepare_retry_state(bundle_dir)

        self.asset_downloader = AssetDownloader(bundle_dir, self.session)
        self.converter = MarkdownConverter(self.asset_downloader, self.base_url)

        if self.hero_url:
            try:
                hero_filename = self.asset_downloader.download(self.hero_url, preferred_filename="featured")
            except requests.RequestException:
                hero_filename = None
                self.summary_lines.append(f"Failed to download hero image {self.hero_url}")
        else:
            hero_filename = None

        self._parse_logs()

        section_markdown = self._render_sections()
        logs_markdown = self._render_logs()

        body_parts: List[str] = []
        summary_text = clean_whitespace(enforce_ascii(self.summary))
        if summary_text:
            body_parts.append(f"*{summary_text}*")
        if section_markdown:
            body_parts.append(section_markdown)
        if logs_markdown:
            body_parts.append(logs_markdown)
        link_text = enforce_ascii(self.project_title)
        body_parts.append(f"> Exported from Hackaday.io [{link_text}]({self.project_url})")
        body = "\n\n".join(body_parts).strip()
        body = re.sub(r"\n (?=\S)", "\n", body)
        body = enforce_ascii(body) + "\n"

        index_path = bundle_dir / "index.md"
        frontmatter = self._build_frontmatter(hero_filename)
        with index_path.open("w", encoding="utf-8") as handle:
            handle.write(frontmatter)
            handle.write("\n")
            handle.write(body)

        self._write_summary(bundle_dir)
        return index_path

    def _fetch_soup(self, url: str, referer: Optional[str] = None) -> BeautifulSoup:
        headers = {}
        if referer:
            headers["Referer"] = referer
        response = self.session.get(url, timeout=REQUEST_TIMEOUT, headers=headers or None)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def _parse_project(self, soup: BeautifulSoup) -> None:
        title_tag = soup.find("h1")
        if not title_tag:
            raise SystemExit("Unable to find project title")
        self.project_title = clean_whitespace(title_tag.get_text())

        description_tag = soup.select_one(".headline p.description")
        if description_tag:
            self.summary = clean_whitespace(description_tag.get_text())
        else:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            self.summary = clean_whitespace(meta_desc["content"]) if meta_desc else ""

        hero_container = soup.select_one(".headline")
        if hero_container and hero_container.has_attr("style"):
            match = re.search(r"background-image:\s*url\(([^)]+)\)", hero_container["style"])
            if match:
                hero_url = match.group(1).strip().strip('"').strip("'")
                self.hero_url = self._resolve_asset_url(hero_url)

        time_section = soup.select_one(".section-project-time .project-time")
        if time_section:
            created_match = re.search(r"created on (\d{2}/\d{2}/\d{4})", time_section.get_text())
            if created_match:
                date_str = created_match.group(1)
                try:
                    self.created_date = datetime.strptime(date_str, "%m/%d/%Y")
                except ValueError:
                    pass

        content_sections = soup.select(".project-menu-content > section")
        for section in content_sections:
            classes = set(section.get("class", []))
            if "section-buildlogs" in classes or "section-share" in classes:
                continue
            title_tag = section.find("h2", class_="section-title")
            title = clean_whitespace(title_tag.get_text()) if title_tag else ""
            if title_tag:
                title_tag.extract()
            for unwanted in section.select(".detail-btns, .log-btns"):
                unwanted.decompose()
            content_nodes = section.select(".post-content")
            if not content_nodes:
                continue
            html_parts: List[str] = []
            for node in content_nodes:
                fragment = node.decode_contents().strip()
                if fragment:
                    html_parts.append(fragment)
            raw_html = "\n".join(html_parts)
            if not raw_html:
                continue
            self.sections.append((title or "Section", raw_html))

        log_links: List[str] = []
        for anchor in soup.select("ol li a[href*='/log/']"):
            href = anchor.get("href")
            if not href:
                continue
            resolved = self._resolve_asset_url(href)
            if resolved not in log_links:
                log_links.append(resolved)
        self.log_urls = log_links

    def _render_sections(self) -> str:
        if not self.sections or not self.converter:
            return ""
        rendered_parts: List[str] = []
        for title, raw_html in self.sections:
            markdown = self.converter.convert(raw_html)
            if not markdown:
                continue
            rendered_parts.append(f"## {enforce_ascii(title)}\n\n{markdown.strip()}\n")
        return "\n".join(rendered_parts).strip()

    def _parse_logs(self) -> None:
        urls: List[str] = []
        seen: set[str] = set()
        for url in self.log_urls:
            log_id = self._extract_log_id(url)
            key = log_id or url
            if key not in seen:
                urls.append(url)
                seen.add(key)

        list_url = f"{self.base_url}{self.project_path}/logs?sort=oldest"
        try:
            soup = self._fetch_soup(list_url, referer=self.project_url)
            for link in soup.select(".section-buildlogs ul.buildlogs-list li h3.element-title a[href*='/log/']"):
                href = link.get("href")
                if not href:
                    continue
                resolved = self._resolve_asset_url(href)
                log_id = self._extract_log_id(resolved)
                key = log_id or resolved
                if key not in seen:
                    urls.append(resolved)
                    seen.add(key)
            next_link = soup.select_one(".pagination a.next-button")
            while next_link:
                next_href = next_link.get("href") or ""
                next_url = self._resolve_asset_url(next_href)
                if not next_url:
                    break
                try:
                    soup = self._fetch_soup(next_url, referer=list_url)
                except requests.HTTPError as exc:
                    if exc.response.status_code == 403:
                        time.sleep(2)
                        try:
                            soup = self._fetch_soup(next_url, referer=list_url)
                        except requests.RequestException:
                            self.summary_lines.append(f"Failed to enumerate logs page: {next_url}")
                            break
                    else:
                        raise
                for link in soup.select(".section-buildlogs ul.buildlogs-list li h3.element-title a[href*='/log/']"):
                    href = link.get("href")
                    if not href:
                        continue
                    resolved = self._resolve_asset_url(href)
                    log_id = self._extract_log_id(resolved)
                    key = log_id or resolved
                    if key not in seen:
                        urls.append(resolved)
                        seen.add(key)
                list_url = next_url
                next_link = soup.select_one(".pagination a.next-button")
        except requests.RequestException:
            self.summary_lines.append("Failed to enumerate paginated log list; relying on discovered links only.")

        entries: List[LogEntry] = []
        for order, url in enumerate(urls, start=1):
            entry = self._fetch_log_entry(url, order)
            if entry:
                entries.append(entry)
        self.logs = entries
        if not self.logs:
            self.summary_lines.append("No project logs found")
        else:
            self.summary_lines.append(f"Imported {len(self.logs)} project logs.")

    def _render_logs(self) -> str:
        if not self.logs:
            return ""
        if not self.converter:
            return ""
        blocks: List[str] = ["## Project Logs"]
        for index, entry in enumerate(self.logs, start=1):
            header = f"### {index}) {enforce_ascii(entry.title)}"
            timestamp = f"<small>{entry.date.strftime('%Y-%m-%d %H:%M')}</small>"
            if entry.is_markdown:
                content = entry.content.strip()
            else:
                content = self.converter.convert(entry.content, heading_offset=3).strip()
            if not content:
                continue
            blocks.append(f"{header}\n{timestamp}\n\n{content}\n")
        return "\n".join(blocks).strip()

    def _build_frontmatter(self, hero_filename: Optional[str]) -> str:
        parts = ["+++", f'title = "{toml_escape(enforce_ascii(self.project_title))}"']
        summary = enforce_ascii(self.summary)
        if summary:
            parts.append(f'summary = "{toml_escape(clean_whitespace(summary))}"')
        date_value = self.created_date or datetime.utcnow()
        parts.append(f'date = "{date_value.isoformat()}"')
        parts.append("draft = false")
        parts.append(f'hackaday_url = "{toml_escape(self.project_url)}"')
        if hero_filename:
            parts.append(f'featured = "{toml_escape(hero_filename)}"')
            parts.append("showHero = true")
            parts.append('heroStyle = "background"')
            parts.append("layoutBackgroundBlur = false")
        parts.append("+++")
        return "\n".join(parts)

    def _write_summary(self, bundle_dir: Path) -> None:
        summary_path = bundle_dir / "export-summary.txt"
        lines: List[str] = []
        lines.append(f"Export summary for {self.project_url}")
        lines.append("")
        if self.summary_lines:
            lines.extend(self.summary_lines)
        else:
            lines.append("All assets downloaded successfully.")
        if self.asset_downloader and self.asset_downloader.failures:
            lines.append("")
            lines.append("Failed to download the following assets (left as remote URLs):")
            lines.extend(sorted(set(self.asset_downloader.failures)))
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _prepare_retry_state(self, bundle_dir: Path) -> None:
        summary_path = bundle_dir / "export-summary.txt"
        index_path = bundle_dir / "index.md"
        if not summary_path.exists() or not index_path.exists():
            self.retry_missing = False
            return

        summary_lines = summary_path.read_text(encoding="utf-8").splitlines()
        missing_numbers: set[int] = set()
        missing_urls: set[str] = set()
        number_pattern = re.compile(r"Failed to fetch log #(\d+)")
        url_pattern = re.compile(r"Failed to fetch full log content: (http\S+)")
        for line in summary_lines:
            match = number_pattern.search(line)
            if match:
                missing_numbers.add(int(match.group(1)))
            match_url = url_pattern.search(line)
            if match_url:
                missing_urls.add(match_url.group(1).strip())

        self.missing_log_numbers = missing_numbers
        self.missing_log_urls = missing_urls

        existing_logs: Dict[int, LogEntry] = {}
        try:
            text = index_path.read_text(encoding="utf-8")
        except OSError:
            self.retry_missing = False
            return

        if "## Project Logs" not in text:
            self.retry_missing = False
            return

        _, logs_section = text.split("## Project Logs", 1)
        segments = logs_section.split("\n### ")
        for segment in segments[1:]:
            header_line, _, remainder = segment.partition("\n")
            header_line = header_line.strip()
            header_match = re.match(r"(\d+)\)\s+(.*)", header_line)
            if not header_match:
                continue
            number = int(header_match.group(1))
            title = clean_whitespace(header_match.group(2))
            remainder = remainder.lstrip("\n")
            timestamp_line, _, body = remainder.partition("\n\n")
            timestamp_match = re.search(r"<small>(.*?)</small>", timestamp_line)
            date_text = timestamp_match.group(1) if timestamp_match else ""
            try:
                date_value = datetime.strptime(date_text, "%Y-%m-%d %H:%M") if date_text else datetime.utcnow()
            except ValueError:
                try:
                    date_value = datetime.strptime(date_text.split()[0], "%Y-%m-%d") if date_text else datetime.utcnow()
                except (ValueError, IndexError):
                    date_value = datetime.utcnow()
            content_markdown = body.strip()
            existing_logs[number] = LogEntry(title=title, date=date_value, content=content_markdown, is_markdown=True)

        self.existing_logs = existing_logs

        if not self.missing_log_numbers and not self.missing_log_urls:
            self.retry_missing = False


    def _resolve_asset_url(self, url: str) -> str:
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return urljoin(self.base_url, url)
        return url

    def _fetch_log_content(self, url: str, referer: Optional[str] = None) -> str:
        if not url:
            return ""
        cached = self._log_cache.get(url)
        if cached is not None:
            return cached
        soup = None
        for attempt in range(3):
            try:
                soup = self._fetch_soup(url, referer=referer or self.project_url)
                break
            except requests.HTTPError as exc:
                if exc.response.status_code != 403 or attempt == 2:
                    self.summary_lines.append(f"Failed to fetch full log content: {url}")
                    self._log_cache[url] = ""
                    return ""
                time.sleep(1 + attempt)
            except requests.RequestException:
                if attempt == 2:
                    self.summary_lines.append(f"Failed to fetch full log content: {url}")
                    self._log_cache[url] = ""
                    return ""
                time.sleep(1 + attempt)
        if soup is None:
            self._log_cache[url] = ""
            return ""
        container = soup.select_one(".post-content")
        if not container:
            container = soup.find("article")
        html_fragment = container.decode_contents() if container else ""
        self._log_cache[url] = html_fragment
        return html_fragment

    def _fetch_log_entry(self, url: str, order: int) -> Optional[LogEntry]:
        if self.retry_missing and order not in self.missing_log_numbers and url not in self.missing_log_urls:
            existing = self.existing_logs.get(order)
            if existing:
                return existing
        soup = None
        for attempt in range(3):
            try:
                soup = self._fetch_soup(url, referer=self.project_url)
                break
            except requests.HTTPError as exc:
                if exc.response.status_code == 403 and attempt < 2:
                    time.sleep(2 + attempt)
                    continue
                self.summary_lines.append(f"Failed to fetch log #{order}: {url}")
                return None
            except requests.RequestException:
                if attempt < 2:
                    time.sleep(2 + attempt)
                    continue
                self.summary_lines.append(f"Failed to fetch log #{order}: {url}")
                return None
        if soup is None:
            return None

        title_tag = soup.select_one(".headline h1") or soup.find("h1")
        date_tag = soup.select_one(".description-metainfo .time-card") or soup.select_one(".time-card")
        content_container = soup.select_one(".post-content") or soup.find("article")

        if not content_container:
            self.summary_lines.append(f"Missing content for log #{order}: {url}")
            return None

        title = clean_whitespace(title_tag.get_text()) if title_tag else f"Log {order}"
        date_text = clean_whitespace(date_tag.get_text()) if date_tag else ""
        try:
            date_value = datetime.strptime(date_text, "%m/%d/%Y at %H:%M") if date_text else datetime.utcnow()
        except ValueError:
            try:
                date_value = datetime.strptime(date_text.split()[0], "%m/%d/%Y")
            except (ValueError, IndexError):
                self.summary_lines.append(f"Unrecognized date format for {url}: {date_text}")
                date_value = datetime.utcnow()

        html_fragment = content_container.decode_contents()
        self._log_cache[url] = html_fragment
        if self.retry_missing:
            self.missing_log_numbers.discard(order)
            self.missing_log_urls.discard(url)
        return LogEntry(title=title, date=date_value, content=html_fragment, is_markdown=False)

    def _extract_log_id(self, url: str) -> Optional[str]:
        if not url:
            return None
        parsed = urlparse(url)
        parts = [segment for segment in parsed.path.split("/") if segment]
        try:
            idx = parts.index("log")
        except ValueError:
            return None
        if idx + 1 >= len(parts):
            return None
        slug = parts[idx + 1]
        return slug.split("-", 1)[0]

    @staticmethod
    def _extract_project_id(path: str) -> str:
        parts = [segment for segment in path.split("/") if segment]
        if len(parts) < 2 or parts[0] != "project":
            raise SystemExit("Invalid Hackaday project URL")
        id_part = parts[1]
        match = re.match(r"(\d+)", id_part)
        if not match:
            raise SystemExit("Unable to determine project ID from URL")
        return match.group(1)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a Hackaday.io project to a Hugo page bundle")
    parser.add_argument("url", help="Hackaday.io project URL")
    parser.add_argument("--output-dir", default="content/projects/", help="Target directory for the Hugo bundles")
    parser.add_argument("--force", action="store_true", help="Overwrite existing bundle directory")
    parser.add_argument(
        "--retry-missing",
        action="store_true",
        help="Retry fetching logs and assets that previously failed without re-downloading existing content",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    output_dir = Path(args.output_dir).expanduser().resolve()
    exporter = HackadayExporter(
        args.url,
        output_dir=output_dir,
        force=args.force,
        retry_missing=args.retry_missing,
    )
    try:
        index_path = exporter.export()
    except requests.HTTPError as exc:
        raise SystemExit(f"HTTP error: {exc}") from exc
    except requests.RequestException as exc:
        raise SystemExit(f"Network error: {exc}") from exc
    print(f"Exported to {index_path}")


if __name__ == "__main__":
    main()
