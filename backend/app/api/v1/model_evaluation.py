"""Admin-only measured evaluation and synthetic dataset downloads."""
import json
from collections import Counter
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.core.security import get_current_admin_id

router = APIRouter(prefix='/api/v1/admin/model', tags=['model-evaluation'])
ROOT = Path(__file__).resolve().parents[3] / 'ml'

@router.get('/evaluation')
def evaluation(_: str = Depends(get_current_admin_id)):
    path = ROOT/'artifacts/evaluation.json'
    if not path.is_file():
        raise HTTPException(503, 'Run python -m ml.evaluate to generate the report.')
    result = json.loads(path.read_text())
    counts = {}
    for split in ['train','validation','test']:
        rows = [json.loads(s) for s in (ROOT/'data'/f'{split}.jsonl').read_text().splitlines()]
        counts[split] = dict(Counter(r['intent'] for r in rows))
    result['dataset_counts'] = counts
    return result

@router.get('/dataset/{split}')
def dataset(split: Literal['train','validation','test'], _: str = Depends(get_current_admin_id)):
    path = ROOT/'data'/f'{split}.jsonl'
    if not path.is_file():
        raise HTTPException(404, 'Dataset not found.')
    return FileResponse(path, media_type='application/x-ndjson', filename=f'campussphere-{split}.jsonl')
