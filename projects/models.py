import uuid
from django.conf import settings
from django.db import models


class Project(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    name = models.CharField('공사명', max_length=200)
    client = models.CharField('발주처', max_length=200, blank=True)
    trade = models.CharField('공종', max_length=40, default='급수 (위생)')
    status = models.CharField('진행 상태', max_length=20, choices=[('review', '검토 중'), ('active', '산출 중'), ('done', '검토 완료')], default='review')
    is_sample = models.BooleanField('테스트 프로젝트', default=False,
                                   help_text='연습·검증용 자료와 수량을 보관할 때 선택하세요. 실제 업무 프로젝트와 구분하여 표시합니다.')
    created_at = models.DateTimeField(auto_now_add=True)


class Drawing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='drawings')
    previous = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT)
    original_name = models.CharField(max_length=255)
    storage_name = models.CharField(max_length=300)
    sha256 = models.CharField(max_length=64)
    kind = models.CharField(max_length=10)
    extraction = models.JSONField(default=dict)
    review_revision = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class Decision(models.Model):
    drawing = models.ForeignKey(Drawing, on_delete=models.PROTECT, related_name='decisions')
    handle = models.CharField(max_length=40)
    data = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['drawing', 'handle'], name='unique_drawing_handle')]


class ReviewEvent(models.Model):
    drawing = models.ForeignKey(Drawing, on_delete=models.PROTECT, related_name='events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    handle = models.CharField(max_length=40)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    revision = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    drawing = models.ForeignKey(Drawing, on_delete=models.PROTECT, related_name='jobs')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=10, choices=[('extract', '객체 추출'), ('takeoff', '길이 산출')])
    request_key = models.CharField(max_length=64, unique=True)
    snapshot = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=[('queued', '대기'), ('running', '진행'), ('succeeded', '완료'), ('failed', '실패')], default='queued')
    attempts = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    result = models.JSONField(default=dict)
    artifact_dir = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)


class WorkerState(models.Model):
    last_seen = models.DateTimeField()


class LoginAttempt(models.Model):
    """Persistent login throttling; no passwords or raw remote addresses stored."""
    key = models.CharField(max_length=64, unique=True)
    failures = models.PositiveIntegerField(default=0)
    last_failure = models.DateTimeField()
