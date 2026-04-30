from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse

import requests

from ..extensions import db
from ..models import OrderDocument

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


INGEST_STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "orders" / "ingestion_state.json"
OFFICIAL_DOCS_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads" / "orders" / "official"

OFFICIAL_SOURCE_URLS = (
    "https://www.marines.mil/News/Messages/",
    "https://www.marines.mil/News/Publications/",
    "https://www.marines.mil/",
    "https://www.esd.whs.mil/DD/",
)
APPROVED_INGEST_DOMAINS = tuple(
    sorted(
        {
            (urlparse(url).netloc or '').strip().lower()
            for url in OFFICIAL_SOURCE_URLS
            if (urlparse(url).netloc or '').strip()
        }
    )
)

ORDER_KEYWORDS = (
    "mco",
    "mcbul",
    "maradmin",
    "almar",
    "navmc",
    "order",
    "directive",
    "instruction",
    "publication",
    "message",
    "memorandum",
)

REJECT_KEYWORDS = (
    "indeed",
    "linkedin",
    "job",
    "jobs",
    "career",
    "careers",
    "vacancy",
    "apply now",
    "recruit",
    "recruiting",
)


@dataclass
class Candidate:
    url: str
    source_page: str
    title_hint: str
    score: int


def _requests_headers() -> dict:
    return {
        "User-Agent": "MCPD-Portal-OrdersIngest/1.0 (+https://mclbpd.com)",
        "Accept": "text/html,application/pdf,*/*",
    }


def _ensure_paths() -> None:
    OFFICIAL_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    INGEST_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_state() -> dict:
    _ensure_paths()
    if not INGEST_STATE_PATH.exists():
        return {"last_run_utc": "", "last_success_utc": "", "last_error": "", "ingested_total": 0}
    try:
        payload = json.loads(INGEST_STATE_PATH.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    _ensure_paths()
    INGEST_STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_ingestion_state() -> dict:
    return _load_state()


def _fetch(url: str, timeout: int = 25):
    return requests.get(url, headers=_requests_headers(), timeout=timeout, allow_redirects=True)


def _strip_html(text: str) -> str:
    content = re.sub(r"(?is)<script.*?>.*?</script>", " ", text or "")
    content = re.sub(r"(?is)<style.*?>.*?</style>", " ", content)
    content = re.sub(r"(?is)<[^>]+>", " ", content)
    content = re.sub(r"\s+", " ", content)
    return content.strip()


def _extract_title(html: str, fallback: str = "") -> str:
    for pattern in (r"(?is)<meta\s+property=[\"']og:title[\"']\s+content=[\"']([^\"']+)", r"(?is)<title[^>]*>(.*?)</title>", r"(?is)<h1[^>]*>(.*?)</h1>"):
        match = re.search(pattern, html or "")
        if match:
            title = _strip_html(match.group(1))
            if title:
                return title[:220]
    return fallback[:220]


def _is_official_source_url(url: str) -> bool:
    host = (urlparse(url or "").netloc or "").strip().lower()
    if not host:
        return False
    return any(host == approved or host.endswith(f".{approved}") for approved in APPROVED_INGEST_DOMAINS)


def _is_candidate_link(url: str) -> bool:
    lower = (url or "").lower()
    if not lower.startswith("http"):
        return False
    if not _is_official_source_url(lower):
        return False
    if any(token in lower for token in REJECT_KEYWORDS):
        return False
    if any(token in lower for token in ("logout", "signin", "login", "javascript:")):
        return False
    if lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".xml")):
        return False
    if lower.endswith(".pdf"):
        return True
    return any(keyword in lower for keyword in ORDER_KEYWORDS)


def _is_candidate_text(text: str) -> bool:
    sample = (text or "").lower()
    if any(token in sample for token in REJECT_KEYWORDS):
        return False
    return any(keyword in sample for keyword in ORDER_KEYWORDS)


def _looks_like_real_order_content(text: str, title: str, url: str) -> bool:
    sample = " ".join([title or "", text[:4000] if text else "", url or ""]).lower()
    if any(token in sample for token in REJECT_KEYWORDS):
        return False
    strong_signals = (
        "maradmin",
        "almar",
        "mco ",
        "mcbul",
        "navmc",
        "memorandum",
        "order number",
        "issuing authority",
        "section ",
        "paragraph ",
        "chapter ",
    )
    return any(token in sample for token in strong_signals)


def _is_article_link(url: str) -> bool:
    lower = (url or "").lower()
    if not lower.startswith("http"):
        return False
    if not _is_official_source_url(lower):
        return False
    return any(token in lower for token in ("/article/", "/messages-display/", "/publications-display/", "/news/"))


def _extract_links(html: str, base_url: str) -> list[str]:
    links: list[str] = []
    for href in re.findall(r'(?is)href=["\']([^"\']+)["\']', html or ""):
        href = href.strip()
        if not href:
            continue
        full = urljoin(base_url, href).split("#")[0]
        if _is_candidate_link(full):
            links.append(full)
    deduped = []
    seen = set()
    for link in links:
        if link in seen:
            continue
        seen.add(link)
        deduped.append(link)
    return deduped


def _extract_link_pairs(html: str, base_url: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for match in re.finditer(r'(?is)<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html or ""):
        href = (match.group(1) or "").strip()
        label = _strip_html(match.group(2) or "")
        if not href:
            continue
        full = urljoin(base_url, href).split("#")[0]
        if not full.startswith("http"):
            continue
        pairs.append((full, label[:220]))
    deduped: list[tuple[str, str]] = []
    seen = set()
    for url, label in pairs:
        key = (url, label)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((url, label))
    return deduped


def _candidate_score(url: str, source_page: str) -> int:
    lower = url.lower()
    score = 0
    if lower.endswith(".pdf"):
        score += 40
    if "maradmin" in lower:
        score += 26
    if "almar" in lower:
        score += 22
    if "mco" in lower:
        score += 24
    if "mcbul" in lower:
        score += 20
    if "navmc" in lower:
        score += 16
    if "publication" in lower or "message" in lower:
        score += 8
    if "marines.mil" in source_page:
        score += 6
    if "esd.whs.mil" in source_page:
        score += 5
    return score


def _collect_candidates(fetch_limit: int = 120) -> list[Candidate]:
    candidates: list[Candidate] = []
    seen = set()
    article_seen = set()
    for source_page in OFFICIAL_SOURCE_URLS:
        try:
            resp = _fetch(source_page)
            if resp.status_code >= 400:
                continue
            html = resp.text or ""
        except Exception:
            continue
        links = _extract_links(html, source_page)
        pairs = _extract_link_pairs(html, source_page)
        page_title = _extract_title(html, source_page)
        for link in links:
            if link in seen:
                continue
            seen.add(link)
            candidates.append(
                Candidate(
                    url=link,
                    source_page=source_page,
                    title_hint=page_title,
                    score=_candidate_score(link, source_page),
                )
            )
        for link, label in pairs:
            if not (_is_candidate_link(link) or _is_candidate_text(label)):
                continue
            if link in seen:
                continue
            seen.add(link)
            candidates.append(
                Candidate(
                    url=link,
                    source_page=source_page,
                    title_hint=label or page_title,
                    score=_candidate_score(link, source_page) + (10 if _is_candidate_text(label) else 0),
                )
            )
            if len(candidates) >= fetch_limit:
                break
        # Article-follow pass: some pages do not expose PDF links directly.
        for link, label in pairs:
            if len(candidates) >= fetch_limit:
                break
            if not _is_article_link(link):
                continue
            if link in article_seen:
                continue
            article_seen.add(link)
            try:
                article_resp = _fetch(link, timeout=30)
                if article_resp.status_code >= 400:
                    continue
                article_html = article_resp.text or ""
            except Exception:
                continue
            article_pairs = _extract_link_pairs(article_html, link)
            article_title = _extract_title(article_html, label or page_title)
            for child_link, child_label in article_pairs:
                if not (_is_candidate_link(child_link) or _is_candidate_text(child_label)):
                    continue
                if child_link in seen:
                    continue
                seen.add(child_link)
                candidates.append(
                    Candidate(
                        url=child_link,
                        source_page=link,
                        title_hint=child_label or article_title,
                        score=_candidate_score(child_link, link) + (10 if _is_candidate_text(child_label or article_title) else 0),
                    )
                )
                if len(candidates) >= fetch_limit:
                    break
    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[: max(10, min(fetch_limit, 500))]


def _guess_order_type(text: str, url: str) -> str:
    sample = f"{(text or '').lower()} {(url or '').lower()}"
    if "maradmin" in sample:
        return "MARADMIN"
    if "almar" in sample:
        return "ALMAR"
    if "mcbul" in sample:
        return "MCBUL"
    if re.search(r"\bmco\b", sample):
        return "MCO"
    if "navmc" in sample:
        return "NAVMC"
    if "directive" in sample or "instruction" in sample or "dod" in sample:
        return "DOD_DIRECTIVE"
    return "USMC_ORDER"


def _extract_order_number(text: str, url: str) -> str:
    sample = f"{text}\n{url}"
    patterns = (
        r"\b(MCO\s+\d{3,5}(?:\.\d+)?[A-Z]?)\b",
        r"\b(MCBUL\s+\d{3,5}(?:\.\d+)?[A-Z]?)\b",
        r"\b(MARADMIN\s+\d{1,4}/\d{2,4})\b",
        r"\b(ALMAR\s+\d{1,4}/\d{2,4})\b",
        r"\b(NAVMC\s+\d{3,6})\b",
        r"\b(DoD\s+Directive\s+\d{3,5}(?:\.\d+)?)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, sample, flags=re.I)
        if match:
            return re.sub(r"\s+", " ", match.group(1).strip().upper())

    # Fallback for common Marines URL slugs, e.g. /maradmin-431-24/ or /almar-012-23/
    url_sample = (url or "").lower()
    slug_match = re.search(r"/(maradmin|almar)-(\d{1,4})-(\d{2,4})(?:/|$)", url_sample)
    if slug_match:
        kind = slug_match.group(1).upper()
        number = str(int(slug_match.group(2)))
        year = slug_match.group(3)
        return f"{kind} {number}/{year}"
    return ""


def _extract_issue_date(text: str) -> datetime | None:
    sample = text[:1500]
    for pattern, fmt in (
        (r"\b(\d{4}-\d{2}-\d{2})\b", "%Y-%m-%d"),
        (r"\b(\d{2}/\d{2}/\d{4})\b", "%m/%d/%Y"),
    ):
        match = re.search(pattern, sample)
        if not match:
            continue
        try:
            return datetime.strptime(match.group(1), fmt)
        except ValueError:
            continue
    return None


def _topic_tags_for_text(text: str) -> str:
    sample = (text or "").lower()
    tags: list[str] = []
    tag_rules = {
        "grooming": ("haircut", "grooming", "beard", "appearance", "tattoo"),
        "uniform": ("uniform", "dress", "insignia"),
        "leave": ("leave", "liberty", "tdy", "travel"),
        "barracks": ("barracks", "housing", "quarters"),
        "drug_policy": ("drug", "controlled substance", "urinalysis"),
        "fitness": ("pt", "physical fitness", "pft", "cft"),
        "traffic": ("traffic", "vehicle", "driving", "registration"),
        "security": ("security", "access", "credential", "gate"),
        "reporting": ("report", "memorandum", "paperwork"),
    }
    for tag, tokens in tag_rules.items():
        if any(token in sample for token in tokens):
            tags.append(tag)
    return ", ".join(tags)


def _safe_file_name_from_url(url: str, fallback_ext: str = ".pdf") -> str:
    path_name = os.path.basename(urlparse(url).path) or ""
    ext = Path(path_name).suffix.lower() if path_name else ""
    if ext not in {".pdf", ".html", ".htm", ".txt"}:
        ext = fallback_ext
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    stem = re.sub(r"[^a-z0-9]+", "-", Path(path_name).stem.lower()).strip("-") or "order"
    return f"official-{stem}-{digest}{ext}"


def _extract_pdf_text(path: Path, max_pages: int = 30) -> str:
    if not PdfReader:
        return ""
    try:
        reader = PdfReader(str(path))
        chunks: list[str] = []
        for page in reader.pages[:max_pages]:
            chunks.append((page.extract_text() or "").strip())
        return "\n".join(chunk for chunk in chunks if chunk).strip()
    except Exception:
        return ""


def _download_candidate(candidate: Candidate) -> dict | None:
    url = candidate.url
    if not _is_official_source_url(url) or not _is_official_source_url(candidate.source_page):
        return None
    try:
        resp = _fetch(url, timeout=40)
    except Exception:
        return None
    if resp.status_code >= 400:
        return None

    content_type = (resp.headers.get("Content-Type") or "").lower()
    is_pdf = url.lower().endswith(".pdf") or "application/pdf" in content_type

    filename = _safe_file_name_from_url(url, fallback_ext=".pdf" if is_pdf else ".html")
    file_path = OFFICIAL_DOCS_DIR / filename
    if is_pdf:
        file_path.write_bytes(resp.content)
        extracted_text = _extract_pdf_text(file_path)
        title = ""
    else:
        html = resp.text or ""
        file_path.write_text(html, encoding="utf-8", errors="ignore")
        extracted_text = _strip_html(html)
        title = _extract_title(html, "")

    if not title:
        title = candidate.title_hint or Path(filename).stem.replace("-", " ").title()

    sample_text = f"{title}\n{extracted_text[:3000]}"
    if not _looks_like_real_order_content(extracted_text, title, url):
        return None
    order_number = _extract_order_number(sample_text, url)
    order_type = _guess_order_type(sample_text, url)
    issue_date = _extract_issue_date(extracted_text)
    topic_tags = _topic_tags_for_text(sample_text)
    summary = (extracted_text[:650] or title).strip()

    return {
        "url": url,
        "file_path": str(file_path),
        "title": title[:200],
        "order_number": order_number or None,
        "source_type": order_type,
        "issue_date": issue_date,
        "summary": summary,
        "extracted_text": extracted_text[:120000],
        "topic_tags": topic_tags or None,
    }


def _upsert_order_document(payload: dict) -> tuple[bool, bool]:
    title = (payload.get("title") or "").strip()
    if not title:
        return False, False

    source_type = (payload.get("source_type") or "USMC_ORDER").strip().upper()
    order_number = (payload.get("order_number") or "").strip() or None
    summary = (payload.get("summary") or "").strip() or None
    extracted_text = (payload.get("extracted_text") or "").strip() or None
    file_path = (payload.get("file_path") or "").strip()
    topic_tags = (payload.get("topic_tags") or "").strip() or None
    source_url = (payload.get("url") or "").strip()
    issue_date = payload.get("issue_date")

    existing = None
    if order_number:
        existing = OrderDocument.query.filter_by(source_type=source_type, order_number=order_number).first()
    if existing is None:
        existing = OrderDocument.query.filter_by(source_type=source_type, title=title).first()

    if existing:
        changed = False
        if summary and summary != (existing.summary or ""):
            existing.summary = summary
            changed = True
        if extracted_text and extracted_text != (existing.extracted_text or ""):
            existing.extracted_text = extracted_text
            changed = True
        if issue_date and issue_date != existing.issue_date:
            existing.issue_date = issue_date
            changed = True
        if topic_tags and topic_tags != (existing.topic_tags or ""):
            existing.topic_tags = topic_tags
            changed = True
        if file_path and file_path != (existing.file_path or ""):
            existing.file_path = file_path
            changed = True
        if source_url and source_url not in (existing.source_group or ""):
            existing.source_group = f"USMC Official | {source_url}"
            changed = True
        if changed:
            existing.last_indexed_at = datetime.utcnow()
            existing.parser_confidence = 0.82
        return False, changed

    document = OrderDocument(
        title=title,
        category="USMC Official Publications",
        source_type=source_type,
        source_group=f"USMC Official | {source_url}" if source_url else "USMC Official",
        order_number=order_number,
        issue_date=issue_date,
        revision_date=issue_date,
        source_version=issue_date.strftime("%Y-%m-%d") if issue_date else "unknown",
        version_label=issue_date.strftime("%Y-%m-%d") if issue_date else None,
        issuing_authority="United States Marine Corps",
        audience_tags="Marines, Civilian Police, Command",
        topic_tags=topic_tags,
        summary=summary,
        extracted_text=extracted_text,
        parser_confidence=0.82,
        file_path=file_path,
        uploaded_by=None,
        last_indexed_at=datetime.utcnow(),
        is_active=True,
    )
    db.session.add(document)
    return True, False


def run_official_orders_ingestion(max_new: int = 20, fetch_limit: int = 120) -> dict:
    _ensure_paths()
    state = _load_state()
    state["last_run_utc"] = datetime.utcnow().isoformat()
    inserted = 0
    updated = 0
    scanned = 0
    errors: list[str] = []

    try:
        candidates = _collect_candidates(fetch_limit=fetch_limit)
        for candidate in candidates:
            if inserted >= max_new:
                break
            scanned += 1
            payload = _download_candidate(candidate)
            if not payload:
                continue
            created, changed = _upsert_order_document(payload)
            if created:
                inserted += 1
            elif changed:
                updated += 1
        db.session.commit()
        state["last_success_utc"] = datetime.utcnow().isoformat()
        state["last_error"] = ""
    except Exception as exc:  # pragma: no cover
        db.session.rollback()
        errors.append(str(exc))
        state["last_error"] = str(exc)

    state["ingested_total"] = int(state.get("ingested_total") or 0) + inserted
    state["last_scanned"] = scanned
    state["last_inserted"] = inserted
    state["last_updated"] = updated
    state["next_due_utc"] = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    _save_state(state)

    return {
        "ok": not errors,
        "scanned": scanned,
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
        "state": state,
    }
