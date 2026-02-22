import fitz
import os
from tqdm import tqdm

def extract_text(path):
    """rip text from a pdf, best effort"""
    try:
        doc = fitz.open(path)
        out = ""
        for pg in doc:
            out += pg.get_text()
        doc.close()
        return out.strip()
    except Exception as exc:
        # some pdfs are just broken beyond repair
        return f"[couldn't read {path}: {exc}]"

def scan_inbox(inbox_dir):
    papers = {}
    files = sorted(f for f in os.listdir(inbox_dir) if f.lower().endswith(".pdf"))
    for f in tqdm(files, desc="Extracting PDFs", unit="paper"):
        papers[f] = extract_text(os.path.join(inbox_dir, f))
    return papers
