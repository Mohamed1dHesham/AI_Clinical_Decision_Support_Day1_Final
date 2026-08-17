import hashlib
import re
from pathlib import Path
from typing import Dict, List, Tuple

from pypdf import PdfReader

from src.config import CHUNK_OVERLAP_TOKENS, CHUNK_TARGET_TOKENS, DOCUMENTS, PDA_HEADINGS

TOKEN_RE = re.compile(r"\S+")
PAGE_NUMBER_RE = re.compile(r"^\d{1,3}$")
NG136_HEADINGS = {
    "1.1 Measuring blood pressure",
    "1.2 Diagnosing hypertension",
    "1.3 Assessing cardiovascular risk and target organ damage",
    "1.4 Treating and monitoring hypertension",
    "1.5 Identifying who to refer for same-day specialist review",
    "Overview",
    "Who is it for?",
    "Recommendations",
    "Terms used in this guideline",
    "Recommendations for research",
    "Key recommendations for research",
    "Other recommendations for research",
    "Rationale and impact",
}


def clean_text(text: str, preserve_lines: bool = False) -> str:
    """Clean PDF extraction artifacts without destroying useful line structure."""
    text = text.replace("\u00ad", "").replace("\r", "\n")
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        lines.append(line)
    text = "\n".join(lines).strip()
    if preserve_lines:
        return text
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(?<![.!?:;])\n(?!\n)", " ", text)
    return text.strip()


def _is_noise(line: str, document_id: str) -> bool:
    if not line or PAGE_NUMBER_RE.fullmatch(line):
        return True
    if "© NICE" in line or "Subject to Notice of rights" in line or "www.nice.org.uk" in line:
        return True
    if document_id == "HTN-PDA-2019":
        if re.fullmatch(r"ACE inhibitor ARB CCB Diuretic\d*", line):
            return True
    return False


def _strip_ng136_toc_suffix(line: str) -> str:
    """Turn a contents entry into its heading text, e.g. '... ..... 10' -> '...'"""
    line = re.sub(r"\.{3,}\s*\d{1,3}\s*$", "", line).strip()
    return re.sub(r"\s+", " ", line)


def _is_ng136_heading(line: str) -> bool:
    normalized = _strip_ng136_toc_suffix(line)
    return normalized in NG136_HEADINGS


def _is_heading(line: str, document_id: str) -> bool:
    if document_id == "HTN-NG136":
        # Never treat a table-of-contents entry as a real page heading.
        if "..." in line:
            return False
        return _is_ng136_heading(line)
    return line.strip() in PDA_HEADINGS


def _normalize_heading_candidate(lines: List[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(x.strip() for x in lines)).strip()


def _heading_match(lines: List[str], document_id: str) -> Tuple[int, str, str]:
    """Return (number_of_lines, heading, remainder) for a heading at the start."""
    if not lines:
        return 0, "", ""

    max_width = min(4, len(lines))
    if document_id == "HTN-NG136":
        # NG136 has a few headings wrapped over two lines.
        for width in range(max_width, 0, -1):
            candidate = _normalize_heading_candidate(lines[:width])
            if candidate in NG136_HEADINGS:
                return width, candidate, ""
        return 0, "", ""

    for width in range(max_width, 0, -1):
        candidate = _normalize_heading_candidate(lines[:width])
        for heading in PDA_HEADINGS:
            if candidate == heading:
                return width, heading, ""
            if candidate.startswith(heading + " "):
                return width, heading, candidate[len(heading):].strip()

    first = lines[0].strip()
    for heading in PDA_HEADINGS:
        if first.startswith(heading + " "):
            return 1, heading, first[len(heading):].strip()
    return 0, "", ""


def infer_sections(text: str, document_id: str, initial_section: str = "Front matter") -> List[Tuple[str, str]]:
    """Split a page into document-aware sections while carrying headings across pages."""
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    blocks: List[Tuple[str, str]] = []
    current = initial_section
    buf: List[str] = []
    i = 0

    while i < len(lines):
        if _is_noise(lines[i], document_id):
            i += 1
            continue
        width, heading, remainder = _heading_match(lines[i:], document_id)
        if width:
            if buf:
                blocks.append((current, " ".join(buf)))
                buf = []
            current = heading
            if remainder:
                buf.append(remainder)
            i += width
            continue
        buf.append(lines[i])
        i += 1

    if buf:
        blocks.append((current, " ".join(buf)))
    return blocks


def _token_count(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def sliding_chunks(text: str, target_tokens: int = CHUNK_TARGET_TOKENS,
                   overlap_tokens: int = CHUNK_OVERLAP_TOKENS) -> List[str]:
    """Create approximately token-sized chunks while preferring sentence boundaries."""
    if not text.strip():
        return []
    words = TOKEN_RE.findall(text)
    if len(words) <= target_tokens:
        return [text.strip()]

    chunks: List[str] = []
    start = 0
    while start < len(words):
        target_end = min(start + target_tokens, len(words))
        end = target_end
        candidate = " ".join(words[start:end])

        if end < len(words):
            boundaries = [m.start() for m in re.finditer(r"[.!?](?:\s|$)", candidate)]
            if boundaries:
                boundary = max(boundaries)
                if boundary >= int(len(candidate) * 0.65):
                    candidate = candidate[:boundary + 1].strip()
                    end = start + _token_count(candidate)

        candidate = candidate.strip()
        if candidate:
            chunks.append(candidate)
        if end >= len(words):
            break
        start = max(start + 1, end - overlap_tokens)
    return chunks


def make_chunk_id(document_id: str, page: int, section: str, chunk_index: int, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{document_id}-P{page:03d}-C{chunk_index:03d}-{digest}"


def load_documents() -> List[Dict]:
    all_chunks: List[Dict] = []
    for doc_cfg in DOCUMENTS:
        path: Path = doc_cfg["path"]
        if not path.exists():
            raise FileNotFoundError(f"Missing PDF: {path}")

        reader = PdfReader(str(path))
        current_section = "Front matter"
        for page_idx, page in enumerate(reader.pages, start=1):
            raw = page.extract_text() or ""
            line_preserved = clean_text(raw, preserve_lines=True)
            if not line_preserved:
                continue

            sections = infer_sections(line_preserved, doc_cfg["document_id"], current_section)
            if sections:
                current_section = sections[-1][0]

            local_idx = 0
            for section, section_text in sections:
                section_text = clean_text(section_text)
                for chunk_text in sliding_chunks(section_text):
                    chunk_id = make_chunk_id(doc_cfg["document_id"], page_idx, section, local_idx, chunk_text)
                    all_chunks.append({
                        "id": chunk_id,
                        "text": chunk_text,
                        "metadata": {
                            "document_id": doc_cfg["document_id"],
                            "document_name": doc_cfg["title"],
                            "source": doc_cfg["source"],
                            "version": doc_cfg["version"],
                            "section": section,
                            "page_number": page_idx,
                            "chunk_id": chunk_id,
                            "token_count": _token_count(chunk_text),
                        },
                    })
                    local_idx += 1
    return all_chunks


if __name__ == "__main__":
    chunks = load_documents()
    print(f"Created {len(chunks)} chunks")
