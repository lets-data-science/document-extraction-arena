"""Restore one checkpoint without losing the learner's previous work."""
import argparse
from pathlib import Path
from datetime import datetime, timezone
import shutil
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('name',choices=['normalize','matching','report']);args=ap.parse_args()
target=root/'learner'/f'{args.name}.py'
if target.exists():
    backup=root/'.backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup.mkdir(parents=True)
    shutil.copy2(target,backup/target.name)
shutil.copy2(root/'checkpoints'/target.name,target)
print(f'Restored learner/{target.name}. Previous work, if present, is in .backups/. Run the focused tests again.')
