import json
from pathlib import Path

from backend.ingest.extract_pdf import extract
from backend.ingest.embed_store import main as embed_store_main

root = Path(__file__).resolve().parent
pdf_path = root / "knowledge" / "general_physician" / "who_dcm_vol2.pdf"
jsonl_path = root / "knowledge_pages.jsonl"

print('pdf exists:', pdf_path.exists())
if not pdf_path.exists():
    raise FileNotFoundError(pdf_path)

pages = extract(pdf_path)
print('extracted pages:', len(pages))
with open(jsonl_path, 'w', encoding='utf-8') as f:
    for page in pages:
        f.write(json.dumps(page, ensure_ascii=False) + '\n')
print('written jsonl:', jsonl_path.exists(), jsonl_path.stat().st_size)

import sys
sys.argv = [sys.argv[0], str(jsonl_path), 'general']
result = embed_store_main()
print('embed_store exit:', result)
