"""Verify original source evidence without making an API request."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'evidence-manifest.json').read_text())
errors=[]
for name,digest in manifest['sha256'].items():
    file=ROOT/name
    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=digest:
        errors.append(name)
if errors:raise SystemExit('Evidence differs: '+', '.join(errors))
print(f"Verified {len(manifest['sha256'])} original evidence files; no provider request.")
