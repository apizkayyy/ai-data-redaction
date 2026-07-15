"""
PDF Data Masking Service
========================
Two-layer PII detection pipeline:

  Layer 1 — Microsoft Presidio (local, fast, pattern + NER based)
            Detects: names, phones, emails, IC numbers, credit cards,
                     bank accounts, passports, addresses/locations, IBANs

  Layer 2 — OpenAI (cloud, semantic, catches edge cases Presidio misses)
            Catches: non-standard IC formats, ambiguous addresses, local
                     Malaysian name patterns, contextual financial data

Results from both layers are merged and deduplicated before redaction.
Black filled rectangles are drawn over all matched bounding boxes.

Usage (module):
    from masking_service import mask_pdf
    result = mask_pdf("in.pdf", "out.pdf", verbose=True)

Usage (CLI):
    python masking_service.py input.pdf output.pdf [--no-openai] [--no-presidio]
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Suppress noisy network-unavailable warnings from tldextract / Presidio
warnings.filterwarnings("ignore")
logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)
logging.getLogger("presidio_analyzer").setLevel(logging.ERROR)

import pdfplumber
from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import black, white
from reportlab.pdfgen import canvas

# Data structures
@dataclass
class WordBox:
    text: str
    page: int           # 0-based
    x0: float      #left side
    y0: float           # PDF coordinate (origin bottom-left)
    x1: float      #right side
    y1: float      #top side
    page_height: float


@dataclass
class RedactionRegion:
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    entity_type: str
    original_text: str
    source: str         # "presidio", "openai", or "both"

# Step 1 – Extract words with bounding boxes
def extract_words(pdf_path: str) -> list[WordBox]:
    """Extract every word and its PDF coordinate bounding box via pdfplumber."""
    words: list[WordBox] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            ph = float(page.height)
            for w in page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False):
                words.append(WordBox(
                    text=w["text"],
                    page=page_num,
                    x0=float(w["x0"]),
                    y0=ph - float(w["bottom"]),  # flip: pdfplumber top → PDF bottom
                    x1=float(w["x1"]),
                    y1=ph - float(w["top"]),
                    page_height=ph,
                ))
    return words


def build_page_text(words: list[WordBox]) -> dict[int, str]:
    """Reconstruct full text per page, preserving word order."""
    pages: dict[int, list[str]] = {}
    for w in words:
        pages.setdefault(w.page, []).append(w.text)
    return {p: " ".join(tokens) for p, tokens in sorted(pages.items())}

# Step 2a – Presidio layer
# Entity types we care about (Presidio built-in + our custom ones)
PRESIDIO_ENTITIES = [
    "PERSON",
    "PHONE_NUMBER",
    "MY_PHONE",
    "EMAIL_ADDRESS",
    "MY_IC_NUMBER",
    "PASSPORT_GENERIC",
    "CREDIT_CARD",
    "BANK_ACCOUNT",
    "LOCATION",
    "IBAN_CODE",
    "US_BANK_NUMBER",   # catches generic bank numbers too
]

# Map Presidio entity types → our canonical labels
ENTITY_TYPE_MAP = {
    "PERSON":           "PERSON_NAME",
    "PHONE_NUMBER":     "PHONE",
    "MY_PHONE":         "PHONE",
    "EMAIL_ADDRESS":    "EMAIL",
    "MY_IC_NUMBER":     "ID_NUMBER",
    "PASSPORT_GENERIC": "ID_NUMBER",
    "CREDIT_CARD":      "FINANCIAL",
    "BANK_ACCOUNT":     "FINANCIAL",
    "US_BANK_NUMBER":   "FINANCIAL",
    "IBAN_CODE":        "FINANCIAL",
    "LOCATION":         "ADDRESS",
}

COMMON_NON_PERSON_WORDS = {
    "Bill",
    "Invoice",
    "Address",
    "Email",
    "Phone",
    "Passport",
    "Account",
    "Date",
    "Customer",
}

def build_presidio_engine():
    """Build and return a configured AnalyzerEngine with custom recognizers."""
    from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern

    engine = AnalyzerEngine()

    custom_recognizers = [
        # Malaysian IC: YYMMDD-SS-GGGG
        PatternRecognizer(
            supported_entity="MY_IC_NUMBER",
            patterns=[Pattern(name="MY_IC", regex=r"\b\d{6}-\d{2}-\d{4}\b", score=0.85)],
        ),
        # Malaysian phone numbers
        PatternRecognizer(
            supported_entity="MY_PHONE",
            patterns=[
                Pattern(name="MY_PHONE_INTL",  regex=r"\+?60[\s\-]?\d{1,2}[\s\-]?\d{3,4}[\s\-]?\d{4}\b", score=0.80),
                Pattern(name="MY_PHONE_LOCAL",  regex=r"\b0\d{1,2}[\s\-]?\d{7,8}\b", score=0.70),
            ],
        ),
        # Generic bank account (e.g. 1234-5678-9012 or 12345678901234)
        PatternRecognizer(
            supported_entity="BANK_ACCOUNT",
            patterns=[
                Pattern(name="BANK_DASHED", regex=r"\b\d{4}-\d{4}-\d{4,10}\b", score=0.70),
                Pattern(name="BANK_PLAIN",  regex=r"\b\d{10,16}\b",             score=0.50),
            ],
        ),
        # Generic passport (e.g. A12345678, AB1234567)
        PatternRecognizer(
            supported_entity="PASSPORT_GENERIC",
            patterns=[
                Pattern(name="PASSPORT_GEN", regex=r"\b[A-Z]{1,2}\d{6,9}\b", score=0.60),
            ],
        ),
    ]

    for rec in custom_recognizers:
        engine.registry.add_recognizer(rec)

    return engine


def detect_with_presidio(
    page_texts: dict[int, str],
    min_score: float = 0.4,
) -> list[dict]:
    """
    Run Presidio on each page's text and return a list of entity dicts:
      {"entity_type": <canonical>, "text": <matched string>, "page": <0-based int>}
    """
    engine = build_presidio_engine()
    entities: list[dict] = []

    for page_num, text in page_texts.items():
        if not text.strip():
            continue
        results = engine.analyze(text=text, language="en", entities=PRESIDIO_ENTITIES)
        for r in results:
            if r.score < min_score:
                continue
            matched_text = text[r.start:r.end].strip()
            if not matched_text:
                continue
            canonical = ENTITY_TYPE_MAP.get(r.entity_type, r.entity_type)
            entities.append({
                "entity_type": canonical,
                "text":        matched_text,
                "page":        page_num,
                "score":       round(r.score, 3),
                "source":      "presidio",
            })

    return entities

# Step 2b – OpenAI layer

OPENAI_SYSTEM_PROMPT = """\
You are a data-privacy assistant specialising in Malaysian and South-East Asian documents.

Identify ALL occurrences of these sensitive entity types in the text below:
- PERSON_NAME   : full or partial personal names (including Malay/Chinese/Indian names)
- PHONE         : phone or fax numbers in any format
- EMAIL         : email addresses
- ID_NUMBER     : IC (NRIC), passport, MyKad, national ID numbers
- FINANCIAL     : bank account numbers, credit/debit card numbers, BIC/SWIFT codes
- ADDRESS       : street addresses, unit numbers, postcodes, city/state

Return ONLY a valid JSON array – no markdown, no explanation.
Each element: { "entity_type": "<type>", "text": "<exact text>" }
If nothing sensitive is found, return: []
"""

def detect_with_openai(page_texts: dict[int, str]) -> list[dict]:
    """
    Send each page's text to OpenAI and collect entity dicts.
    Returns: [{"entity_type": ..., "text": ..., "page": ..., "source": "openai"}]

    Requires OPENAI_API_KEY to be set in the environment.
    """
    from dotenv import load_dotenv

    load_dotenv()

    from openai import OpenAI

    client = OpenAI()   # reads OPENAI_API_KEY from environment automatically
    entities: list[dict] = []

    for page_num, text in page_texts.items():
        if not text.strip():
            continue

        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            max_completion_tokens=5000,
            messages=[
                {"role": "system", "content": OPENAI_SYSTEM_PROMPT},
                {"role": "user",   "content": f"[Page {page_num + 1}]\n\n{text}"},
            ],
        )

        raw = response.choices[0].message.content.strip()

        # Strip accidental Markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            page_entities = json.loads(raw)
        except json.JSONDecodeError:
            continue  # skip page if model returns bad JSON

        if not isinstance(page_entities, list):
            continue

        for e in page_entities:
            if not isinstance(e, dict):
                continue
            text_val = e.get("text", "").strip()
            if not text_val:
                continue
            entities.append({
                "entity_type": e.get("entity_type", "UNKNOWN"),
                "text":        text_val,
                "page":        page_num,
                "source":      "openai",
            })

    return entities


# Step 3 – Merge & deduplicate entities from both layers
def merge_entities(
    presidio_entities: list[dict],
    openai_entities: list[dict],
) -> list[dict]:
    """
    Combine results from both detectors.
    De-duplicate: if the same text on the same page appears in both, keep one
    entry marked source="both".
    """
    seen: dict[tuple, dict] = {}

    for e in presidio_entities:
        key = (e["page"], e["text"].lower())
        if key not in seen:
            seen[key] = dict(e)

    for e in openai_entities:
        key = (e["page"], e["text"].lower())
        if key in seen:
            seen[key]["source"] = "both"
        else:
            seen[key] = dict(e)

    return list(seen.values())

# Step 4 – Map entity strings → bounding boxes
def _union_bbox(boxes: list[WordBox]) -> tuple[float, float, float, float]:
    return (
        min(b.x0 for b in boxes),
        min(b.y0 for b in boxes),
        max(b.x1 for b in boxes),
        max(b.y1 for b in boxes),
    )


def find_redaction_regions(
    words: list[WordBox],
    entities: list[dict],
    padding: float = 2.0,
) -> list[RedactionRegion]:
    """
    Slide a token window over the word list to find which words on which page
    match each entity string, then compute a merged bounding box.
    """
    page_words: dict[int, list[WordBox]] = {}
    for w in words:
        page_words.setdefault(w.page, []).append(w)

    regions: list[RedactionRegion] = []

    for entity in entities:
        entity_text: str       = entity.get("text", "").strip()
        entity_type: str       = entity.get("entity_type", "UNKNOWN")
        source: str            = entity.get("source", "unknown")
        target_page: Optional[int] = entity.get("page")  # None = search all pages

        if not entity_text:
            continue

        entity_tokens = entity_text.split()
        n = len(entity_tokens)

        pages_to_search = (
            [target_page] if target_page is not None else list(page_words.keys())
        )

        for pg in pages_to_search:
            pw = page_words.get(pg, [])
            for i in range(len(pw) - n + 1):
                window = pw[i: i + n]
                if [t.text.lower() for t in window] == [t.lower() for t in entity_tokens]:
                    x0, y0, x1, y1 = _union_bbox(window)
                    regions.append(RedactionRegion(
                        page=pg,
                        x0=x0 - padding,
                        y0=y0 - padding,
                        x1=x1 + padding,
                        y1=y1 + padding,
                        entity_type=entity_type,
                        original_text=entity_text,
                        source=source,
                    ))

    return regions


# Step 5 – Draw redaction bars
def apply_redactions(
    input_path: str,
    output_path: str,
    regions: list[RedactionRegion],
) -> None:
    """Overlay solid black rectangles on every redaction region and save."""
    reader = PdfReader(input_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    # Group by page
    page_regions: dict[int, list[RedactionRegion]] = {}
    for r in regions:
        page_regions.setdefault(r.page, []).append(r)

    for page_num, redactions in page_regions.items():
        page_obj = writer.pages[page_num]
        mb = page_obj.mediabox
        pw, ph = float(mb.width), float(mb.height)

        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(pw, ph))
        c.setFillColor(black)
        c.setStrokeColor(black)

        for r in redactions:
            c.rect(r.x0, r.y0, r.x1 - r.x0, r.y1 - r.y0, fill=1, stroke=0)

        c.save()
        packet.seek(0)

        overlay_page = PdfReader(packet).pages[0]
        page_obj.merge_page(overlay_page)

    with open(output_path, "wb") as f:
        writer.write(f)

# Public API
def mask_pdf(
    input_path: str,
    output_path: str,
    use_presidio: bool = True,
    use_openai: bool = True,
    presidio_min_score: float = 0.4,
    verbose: bool = False,
) -> dict:
    """
    Full masking pipeline.

    Parameters
    ----------
    input_path          : Path to the source PDF.
    output_path         : Where to write the redacted PDF.
    use_presidio        : Enable Presidio layer (default True).
    use_openai          : Enable OpenAI layer (default True).
    presidio_min_score  : Minimum Presidio confidence score to keep (0–1).
    verbose             : Print progress to stdout.

    Returns
    -------
    dict with keys: status, input, output, pages, entities_detected,
                    redactions_applied, redactions (list), layer_counts (dict)
    """
    input_path  = str(Path(input_path).resolve())
    output_path = str(Path(output_path).resolve())

    if not use_presidio and not use_openai:
        raise ValueError("At least one detection layer (presidio or openai) must be enabled.")

    def log(msg: str):
        if verbose:
            print(msg)

    # 1. Extract words
    log("[1/5] Extracting words and bounding boxes …")
    words = extract_words(input_path)
    page_texts = build_page_text(words)
    log(f"{len(words)} words across {len(page_texts)} page(s)")

    # 2a. Presidio
    presidio_entities: list[dict] = []
    if use_presidio:
        log("[2/5] Running Presidio PII detection …")
        presidio_entities = detect_with_presidio(page_texts, min_score=presidio_min_score)
        log(f"Presidio found {len(presidio_entities)} entity instance(s)")
    else:
        log("[2/5] Presidio layer skipped")

    # 2b. OpenAI
    openai_entities: list[dict] = []
    if use_openai:
        log("[3/5] Running OpenAI PII detection …")
        openai_entities = detect_with_openai(page_texts)
        log(f"OpenAI found {len(openai_entities)} entity instance(s)")
    else:
        log("[3/5] OpenAI layer skipped")

    # 3. Merge
    log("[4/5] Merging and deduplicating results …")
    merged = merge_entities(presidio_entities, openai_entities)
    log(f"{len(merged)} unique entities after deduplication")

    # 4. Locate bounding boxes
    regions = find_redaction_regions(words, merged)
    log(f"{len(regions)} bounding box region(s) matched")

    # 5. Apply redactions
    log("[5/5] Drawing redaction bars and saving …")
    apply_redactions(input_path, output_path, regions)
    log(f"Saved → {output_path}")

    # Build layer breakdown
    layer_counts = {
        "presidio_only": sum(1 for e in merged if e.get("source") == "presidio"),
        "openai_only":   sum(1 for e in merged if e.get("source") == "openai"),
        "both":          sum(1 for e in merged if e.get("source") == "both"),
    }

    return {
        "status":             "ok",
        "input":              input_path,
        "output":             output_path,
        "pages":              len(page_texts),
        "entities_detected":  len(merged),
        "redactions_applied": len(regions),
        "layer_counts":       layer_counts,
        "redactions": [
            {
                "page":        r.page + 1,
                "entity_type": r.entity_type,
                "text":        r.original_text,
                "source":      r.source,
                "bbox":        [round(r.x0, 2), round(r.y0, 2), round(r.x1, 2), round(r.y1, 2)],
            }
            for r in regions
        ],
    }


# CLI

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redact PII from a PDF using Presidio + OpenAI.")
    parser.add_argument("input",         help="Source PDF file")
    parser.add_argument("output",        help="Destination masked PDF file")
    parser.add_argument("--no-presidio", action="store_true", help="Disable Presidio layer")
    parser.add_argument("--no-openai",   action="store_true", help="Disable OpenAI layer")
    parser.add_argument("--min-score",   type=float, default=0.4,
                        help="Presidio min confidence score (default 0.4)")
    args = parser.parse_args()

    result = mask_pdf(
        input_path=args.input,
        output_path=args.output,
        use_presidio=not args.no_presidio,
        use_openai=not args.no_openai,
        presidio_min_score=args.min_score,
        verbose=True,
    )

    print("\n=== Masking Report ===")
    print(json.dumps(result, indent=2))
