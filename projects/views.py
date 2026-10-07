import hashlib
import json
import mimetypes
import os
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from takeoff.engine import validate_decision
from .forms import DecisionForm, ProjectForm, RunForm, UploadForm
from .models import Decision, Drawing, Job, LoginAttempt, Project, ReviewEvent, WorkerState
from .tasks import enqueue, storage_path


class ThrottledLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        identity = request.POST.get('username', '').strip().lower()[:150]
        self.attempt_keys = [hashlib.sha256(value.encode()).hexdigest() for value in
                             ['user:' + identity, 'ip:' + request.META.get('REMOTE_ADDR', '')]]
        cutoff = timezone.now() - timedelta(minutes=15)
        if LoginAttempt.objects.filter(key__in=self.attempt_keys, failures__gte=10, last_failure__gte=cutoff).exists():
            return HttpResponse('로그인 시도가 너무 많습니다. 15분 뒤 다시 시도하세요.', status=429)
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        for key in self.attempt_keys:
            attempt, _ = LoginAttempt.objects.get_or_create(key=key, defaults={'last_failure': timezone.now()})
            if attempt.last_failure < timezone.now() - timedelta(minutes=15):
                attempt.failures = 0
            attempt.failures += 1
            attempt.last_failure = timezone.now()
            attempt.save()
        return super().form_invalid(form)

    def form_valid(self, form):
        LoginAttempt.objects.filter(key__in=self.attempt_keys).delete()
        return super().form_valid(form)


def owned_project(user, pk):
    return get_object_or_404(Project, pk=pk, owner=user)


def owned_drawing(user, pk):
    return get_object_or_404(Drawing.objects.select_related('project'), pk=pk, project__owner=user)


def owned_job(user, pk):
    return get_object_or_404(Job.objects.select_related('drawing__project'), pk=pk, drawing__project__owner=user)


@login_required
def home(request):
    return render(request, 'projects/home.html', {'projects': Project.objects.filter(owner=request.user).order_by('-created_at')})


@login_required
def project_form(request, pk=None):
    project = owned_project(request.user, pk) if pk else None
    form = ProjectForm(request.POST or None, instance=project)
    if request.method == 'POST' and form.is_valid():
        project = form.save(commit=False)
        project.owner = request.user
        project.save()
        return redirect('project', pk=project.pk)
    return render(request, 'projects/form.html', {'form': form, 'heading': '프로젝트 수정' if pk else '새 프로젝트'})


@login_required
def project_detail(request, pk):
    project = owned_project(request.user, pk)
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        previous = None
        if form.cleaned_data['previous']:
            previous = get_object_or_404(Drawing, pk=form.cleaned_data['previous'], project=project)
        upload = form.cleaned_data['file']
        suffix = Path(upload.name).suffix.lower()
        relative = f'originals/{project.pk}/{uuid.uuid4().hex}{suffix}'
        path = storage_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        hasher = hashlib.sha256()
        try:
            with open(path, 'xb') as f:
                os.chmod(path, 0o600)
                for chunk in upload.chunks():
                    f.write(chunk); hasher.update(chunk)
            with transaction.atomic():
                drawing = Drawing.objects.create(project=project, previous=previous, original_name=Path(upload.name).name,
                            storage_name=relative, kind=suffix[1:], sha256=hasher.hexdigest())
                if drawing.kind == 'dxf':
                    enqueue(drawing, request.user, 'extract', {})
        except Exception:
            path.unlink(missing_ok=True)
            raise
        messages.success(request, '원본을 별도 버전으로 보관했습니다. DXF 객체 추출은 작업자가 처리합니다.')
        return redirect('drawing', pk=drawing.pk)
    heartbeat = WorkerState.objects.filter(pk=1).first()
    ready = bool(heartbeat and timezone.now() - heartbeat.last_seen < timedelta(seconds=150))
    return render(request, 'projects/project.html', {'project': project, 'form': form,
                  'drawings': project.drawings.order_by('-created_at'), 'worker_ready': ready})


@login_required
def drawing_detail(request, pk):
    drawing = owned_drawing(request.user, pk)
    decisions = {d.handle: d.data for d in drawing.decisions.all()}
    entities = []
    for item in drawing.extraction.get('entities', []):
        row = {**item, 'decision': decisions.get(item['handle'], {'status': 'pending'})}
        if request.GET.get('pending') != '1' or row['decision']['status'] == 'pending':
            entities.append(row)
    page = Paginator(entities, 50).get_page(request.GET.get('page'))
    return render(request, 'projects/drawing.html', {'drawing': drawing, 'page': page,
        'jobs': drawing.jobs.order_by('-created_at'), 'form': RunForm(initial={'revision': drawing.review_revision}),
        'pending_only': request.GET.get('pending') == '1'})


@login_required
def decision_edit(request, pk, handle):
    drawing = owned_drawing(request.user, pk)
    entity = next((e for e in drawing.extraction.get('entities', []) if e['handle'] == handle), None)
    if not entity:
        raise Http404
    existing = drawing.decisions.filter(handle=handle).first()
    initial = {**(existing.data if existing else {}), 'revision': drawing.review_revision}
    form = DecisionForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        data = {k: str(v) if k == 'diameter_mm' and v is not None else v for k, v in form.cleaned_data.items() if k != 'revision'}
        try:
            validate_decision(entity, data)
        except ValueError as exc:
            form.add_error(None, str(exc))
        else:
            with transaction.atomic():
                revision = form.cleaned_data['revision']
                changed = Drawing.objects.filter(pk=pk, review_revision=revision).update(review_revision=F('review_revision') + 1)
                if not changed:
                    return HttpResponse('다른 화면에서 확인 정보가 변경되었습니다. 새로고침 후 다시 검토하세요.', status=409)
                decision, _ = Decision.objects.get_or_create(drawing=drawing, handle=handle)
                ReviewEvent.objects.create(drawing=drawing, actor=request.user, handle=handle, before=decision.data, after=data, revision=revision + 1)
                decision.data = data
                decision.save(update_fields=['data'])
            messages.success(request, f'객체 {handle} 확인 정보와 변경 이력을 저장했습니다.')
            return redirect('drawing', pk=pk)
    return render(request, 'projects/decision.html', {'drawing': drawing, 'entity': entity, 'form': form,
                  'events': drawing.events.filter(handle=handle).order_by('-revision')})


@login_required
@require_POST
def run_takeoff(request, pk):
    drawing = owned_drawing(request.user, pk)
    if drawing.kind != 'dxf' or not drawing.extraction:
        return HttpResponse('DXF 객체 추출이 완료되어야 합니다.', status=409)
    form = RunForm(request.POST)
    if not form.is_valid():
        return render(request, 'projects/form.html', {'form': form, 'heading': '산출 설정 확인'}, status=400)
    rules = json.loads((settings.BASE_DIR / 'rules/planar-v1.json').read_text())
    rules.update({k: form.cleaned_data[k] for k in ('decimal_places', 'rounding')})
    with transaction.atomic():
        # Acquire a write lock before reading decisions, keeping the revision and snapshot consistent.
        changed = Drawing.objects.filter(pk=pk, review_revision=form.cleaned_data['revision']).update(review_revision=F('review_revision'))
        if not changed:
            return HttpResponse('확인 정보가 변경되었습니다. 새로고침 후 실행하세요.', status=409)
        decisions = {d.handle: d.data for d in drawing.decisions.all()}
        if not any(d.get('status') == 'confirmed' for d in decisions.values()):
            return HttpResponse('최소 하나의 급수 배관을 확정해야 합니다.', status=400)
        snapshot = {k: form.cleaned_data[k] for k in ('unit', 'unit_evidence', 'revision')}
        snapshot.update({'decisions': decisions, 'rules': rules})
        job = enqueue(drawing, request.user, 'takeoff', snapshot)
    return redirect('job', pk=job.pk)


@login_required
def job_detail(request, pk):
    job = owned_job(request.user, pk)
    rows = job.result.get('rows', [])
    if request.GET.get('diameter'):
        rows = [r for r in rows if r['diameter_mm'] == request.GET['diameter']]
    if request.GET.get('zone'):
        rows = [r for r in rows if r['zone'] == request.GET['zone']]
    return render(request, 'projects/job.html', {'job': job, 'rows': Paginator(rows, 50).get_page(request.GET.get('page')),
        'diameters': sorted({r['diameter_mm'] for r in job.result.get('rows', []) if r['diameter_mm']}),
        'zones': sorted({r['zone'] for r in job.result.get('rows', []) if r['zone']})})


@login_required
@require_POST
def retry_job(request, pk):
    job = owned_job(request.user, pk)
    changed = Job.objects.filter(pk=job.pk, status='failed', attempts__lt=3).update(status='queued', error='', finished_at=None)
    if not changed:
        return HttpResponse('실패한 작업만 최대 3회까지 실행할 수 있습니다.', status=409)
    return redirect('job', pk=pk)


@login_required
def original(request, pk):
    drawing = owned_drawing(request.user, pk)
    path = storage_path(drawing.storage_name)
    if not path.is_file():
        raise Http404
    preview = request.GET.get('preview') == '1' and drawing.kind in ('pdf', 'png', 'jpg', 'jpeg')
    content_type = mimetypes.guess_type(drawing.original_name)[0] if preview else 'application/octet-stream'
    response = FileResponse(open(path, 'rb'), as_attachment=not preview, filename=drawing.original_name, content_type=content_type)
    response['Content-Security-Policy'] = "sandbox; default-src 'none'"
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
def artifact(request, pk, name):
    job = owned_job(request.user, pk)
    if name not in ('standardized.dxf', 'takeoff.xlsx', 'result.json') or job.status != 'succeeded' or not job.artifact_dir:
        raise Http404
    path = storage_path(f'{job.artifact_dir}/{name}')
    if not path.is_file():
        raise Http404
    response = FileResponse(open(path, 'rb'), as_attachment=True, filename=name)
    response['Cache-Control'] = 'private, no-store'
    return response
