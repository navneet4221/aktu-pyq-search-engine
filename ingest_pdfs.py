"""
Extract text from PDFs in data/papers and split it into question records.
This is a starter parser: inspect questions.json after each run because paper layouts vary.
"""
import csv
import json
import re
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).parent
PAPERS_DIR = ROOT / "data" / "papers"
OUTPUT_DIR = ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "questions.json"
METADATA_FILE = ROOT / "papers_metadata.csv"

# Matches common formats such as "Q.1", "Q1.", "1.", "1)" and "1(a)" at line starts.
QUESTION_START = re.compile(
    r"(?im)^[ \t]*(?:Q(?:uestion)?[ \t]*\.?[ \t]*)?\d{1,2}[ \t]*(?:[.)]|[ \t]*\([a-zA-Z]\))[ \t]*"
)

def load_metadata():
    metadata = {}
    if not METADATA_FILE.exists():
        return metadata
    with METADATA_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            filename = (row.get("filename") or "").strip()
            if filename:
                metadata[filename.lower()] = row
    return metadata

def extract_pages(pdf_path):
    pages = []
    with fitz.open(pdf_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            pages.append((page_number, page.get_text("text").strip()))
    return pages

def split_questions(text):
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    matches = list(QUESTION_START.finditer(text))
    if not matches:
        # If the parser cannot detect question numbers, keep the page as one searchable unit.
        return [text] if len(text) >= 25 else []
    parts = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        part = text[start:end].strip()
        part = re.sub(r"\s+", " ", part)
        if len(part) >= 20:
            parts.append(part)
    return parts

def main():
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(PAPERS_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found. Add PDFs to: {PAPERS_DIR}")
        return

    metadata = load_metadata()
    records = []
    for pdf_path in pdfs:
        meta = metadata.get(pdf_path.name.lower(), {})
        subject = (meta.get("subject") or pdf_path.stem.replace("_", " ")).strip()
        year = (meta.get("year") or "Unknown").strip()
        semester = (meta.get("semester") or "Unknown").strip()
        source_url = (meta.get("source_url") or "").strip()
        paper_name = (meta.get("paper") or pdf_path.name).strip()
        extracted_count = 0

        try:
            pages = extract_pages(pdf_path)
        except Exception as exc:
            print(f"Could not read {pdf_path.name}: {exc}")
            continue

        for page_number, page_text in pages:
            if not page_text:
                continue
            for question in split_questions(page_text):
                records.append({
                    "question": question,
                    "subject": subject,
                    "year": year,
                    "semester": semester,
                    "paper": paper_name,
                    "source_file": pdf_path.name,
                    "source_url": source_url,
                    "page": page_number,
                })
                extracted_count += 1

        print(f"{pdf_path.name}: extracted {extracted_count} searchable units")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(records)} searchable units to {OUTPUT_FILE}")
    print("IMPORTANT: Open questions.json and manually inspect the extracted text before your demo.")

if __name__ == "__main__":
    main()
