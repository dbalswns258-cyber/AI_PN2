"""Create local private state outside the repository; never overwrite an existing key."""
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
data = Path(os.environ.get('AI_PN2_DATA_DIR', root.parent / 'ai-pn2-data')).resolve()
if data == root or root in data.parents:
    raise SystemExit('자료 저장 경로는 저장소 밖이어야 합니다.')
data.mkdir(parents=True, exist_ok=True, mode=0o700)
(data / 'files').mkdir(exist_ok=True, mode=0o700)
try:
    fd = os.open(data / 'django-secret-key', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    pass
else:
    with os.fdopen(fd, 'w') as f:
        f.write(secrets.token_urlsafe(64))
print(f'Persistent data prepared: {data}')
