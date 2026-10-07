import json
import os
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from takeoff import ENGINE_VERSION
from takeoff.engine import calculate, digest, export, extract, file_digest
from .models import Drawing, Job


def storage_path(relative):
    root = Path(settings.MEDIA_ROOT).resolve()
    path = (root / relative).resolve()
    if root not in path.parents:
        raise ValueError('유효하지 않은 저장 경로입니다.')
    return path


def enqueue(drawing, user, kind, snapshot):
    snapshot = {**snapshot, 'drawing_id': str(drawing.id), 'source_sha256': drawing.sha256, 'engine_version': ENGINE_VERSION}
    key = digest({'kind': kind, 'snapshot': snapshot})
    job, _ = Job.objects.get_or_create(request_key=key, defaults={'drawing': drawing, 'requested_by': user, 'kind': kind, 'snapshot': snapshot})
    return job


def process_job(job_id):
    changed = Job.objects.filter(pk=job_id, status='queued').update(status='running', started_at=timezone.now(),
                finished_at=None, error='')
    if not changed:
        return False
    job = Job.objects.select_related('drawing').get(pk=job_id)
    job.attempts += 1
    job.save(update_fields=['attempts'])
    staging = None
    try:
        source = storage_path(job.drawing.storage_name)
        if file_digest(source) != job.snapshot['source_sha256']:
            raise ValueError('보관된 원본의 해시가 변경되었습니다. 실행을 중단했습니다.')
        if job.snapshot['engine_version'] != ENGINE_VERSION:
            raise ValueError('엔진 버전이 변경되었습니다. 새 작업을 요청하세요.')
        if job.kind == 'extract':
            extraction = extract(source)
            Drawing.objects.filter(pk=job.drawing_id).update(extraction=extraction)
            job.result = {'entity_count': len(extraction['entities']), 'warnings': extraction['warnings']}
        else:
            extraction = extract(source)
            result = calculate(extraction, job.snapshot['decisions'], job.snapshot['unit'], job.snapshot['unit_evidence'], job.snapshot['rules'])
            result['provenance'] = {'drawing_id': str(job.drawing_id), 'project_id': job.drawing.project_id,
                                    'original_name': job.drawing.original_name, 'review_revision': job.snapshot['revision']}
            root = Path(settings.MEDIA_ROOT)
            root.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix='.job-', dir=root))
            export(source, staging / 'artifacts', extraction, result)
            relative = f'results/{job.id}/attempt-{job.attempts}'
            target = storage_path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.rename(staging / 'artifacts', target)
            job.artifact_dir = relative
            job.result = result
        job.status = 'succeeded'
        job.error = ''
    except Exception as exc:
        job.status = 'failed'
        job.error = f'{type(exc).__name__}: {str(exc)[:1500]}'
    finally:
        if staging:
            shutil.rmtree(staging, ignore_errors=True)
    job.finished_at = timezone.now()
    job.save(update_fields=['status', 'error', 'result', 'artifact_dir', 'finished_at'])
    return job.status == 'succeeded'
