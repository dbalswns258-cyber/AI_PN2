import json
import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from projects.models import Decision, Drawing, Job, Project, ReviewEvent, WorkerState
from projects.tasks import process_job, storage_path
from takeoff.sample import create_sample


class WorkflowTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.override = override_settings(MEDIA_ROOT=self.root / 'files', DATA_DIR=self.root)
        self.override.enable(); self.addCleanup(self.override.disable)
        self.owner = get_user_model().objects.create_user('owner', password='test-only-strong-pass-392!')
        self.other = get_user_model().objects.create_user('other', password='test-only-other-pass-492!')
        self.project = Project.objects.create(owner=self.owner, name='합성 학교 급수 검증', client='합성 테스트')
        self.client.force_login(self.owner)
        self.sample = create_sample(self.root / 'sample')

    def upload(self, data=None, name='synthetic.dxf', extract_now=True):
        response = self.client.post(reverse('project', args=[self.project.pk]),
                {'file': SimpleUploadedFile(name, self.sample.read_bytes() if data is None else data)})
        self.assertEqual(response.status_code, 302)
        drawing = Drawing.objects.latest('created_at')
        if extract_now and drawing.kind == 'dxf':
            self.assertTrue(process_job(drawing.jobs.get().pk))
            drawing.refresh_from_db()
        return drawing

    def review_sample(self, drawing):
        decisions = json.loads((self.sample.parent / 'decisions.json').read_text())
        for handle, data in decisions.items():
            drawing.refresh_from_db()
            response = self.client.post(reverse('decision', args=[drawing.pk, handle]),
                                       {**data, 'revision': drawing.review_revision})
            self.assertEqual(response.status_code, 302)
        drawing.refresh_from_db()

    def request_run(self, drawing):
        return self.client.post(reverse('run', args=[drawing.pk]), {'revision': drawing.review_revision,
             'unit': 'mm', 'unit_evidence': '합성 5000 mm 치수', 'decimal_places': '3', 'rounding': 'ROUND_HALF_UP', 'accept': 'on'})

    def test_real_password_login_and_post_logout(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('home')).status_code, 302)
        bad = self.client.post(reverse('login'), {'username': 'owner', 'password': 'wrong'})
        self.assertEqual(bad.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        good = self.client.post(reverse('login'), {'username': 'owner', 'password': 'test-only-strong-pass-392!'})
        self.assertEqual(good.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertEqual(self.client.post(reverse('logout')).status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_csrf_required_for_login_and_mutation(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('login'), {'username': 'owner', 'password': 'test-only-strong-pass-392!'}).status_code, 403)
        client.force_login(self.owner)
        self.assertEqual(client.post(reverse('project_create'), {'name': 'blocked'}).status_code, 403)

    def test_login_rate_limit_persists_between_sessions(self):
        self.client.logout()
        for _ in range(10):
            self.client.post(reverse('login'), {'username': 'owner', 'password': 'wrong'})
        fresh = Client()
        self.assertEqual(fresh.post(reverse('login'), {'username': 'owner', 'password': 'wrong'}).status_code, 429)

    def test_projects_create_edit_and_list_owner(self):
        response = self.client.post(reverse('project_create'), {'name': '새 공사', 'client': '교육청', 'trade': '급수', 'status': 'active'})
        self.assertEqual(response.status_code, 302)
        p = Project.objects.get(name='새 공사'); self.assertEqual(p.owner, self.owner)
        self.client.post(reverse('project_edit', args=[p.pk]), {'name': '수정 공사', 'client': '교육청', 'trade': '급수', 'status': 'review'})
        p.refresh_from_db(); self.assertEqual(p.name, '수정 공사')
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('home')), '수정 공사')

    def test_full_upload_review_job_export_flow(self):
        drawing = self.upload(); self.review_sample(drawing)
        response = self.request_run(drawing); self.assertEqual(response.status_code, 302)
        job = drawing.jobs.get(kind='takeoff')
        self.assertEqual(job.status, 'queued')
        self.assertTrue(process_job(job.pk)); job.refresh_from_db()
        self.assertEqual(job.result['summary'][0]['length_m'], '8.142')
        self.assertEqual(job.result['provenance']['review_revision'], 4)
        self.assertEqual(ReviewEvent.objects.count(), 4)
        for name in ('standardized.dxf', 'takeoff.xlsx', 'result.json'):
            response = self.client.get(reverse('artifact', args=[job.pk, name]))
            self.assertEqual(response.status_code, 200)
            self.assertGreater(len(b''.join(response.streaming_content)), 10)
        for url in (reverse('drawing', args=[drawing.pk]), reverse('job', args=[job.pk]), reverse('project', args=[self.project.pk])):
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_duplicate_submit_returns_same_job(self):
        drawing = self.upload(); self.review_sample(drawing)
        self.request_run(drawing); self.request_run(drawing)
        self.assertEqual(drawing.jobs.filter(kind='takeoff').count(), 1)

    def test_snapshot_is_immutable_after_review_changes(self):
        drawing = self.upload(); self.review_sample(drawing); self.request_run(drawing)
        job = drawing.jobs.get(kind='takeoff')
        handle = next(iter(job.snapshot['decisions']))
        old = job.snapshot['decisions'][handle]
        self.client.post(reverse('decision', args=[drawing.pk, handle]),
                {**old, 'status': 'excluded', 'evidence': '나중에 변경', 'revision': drawing.review_revision})
        self.assertTrue(process_job(job.pk)); job.refresh_from_db()
        self.assertEqual(job.result['summary'][0]['length_m'], '8.142')
        self.assertEqual(job.snapshot['decisions'][handle], old)

    def test_stale_review_and_run_are_rejected(self):
        drawing = self.upload(); self.review_sample(drawing)
        handle = drawing.extraction['entities'][0]['handle']
        response = self.client.post(reverse('decision', args=[drawing.pk, handle]), {'status': 'excluded', 'evidence': 'stale', 'revision': 0})
        self.assertEqual(response.status_code, 409)
        drawing.review_revision = 0
        self.assertEqual(self.request_run(drawing).status_code, 409)

    def test_all_project_file_result_routes_check_ownership(self):
        drawing = self.upload(); self.review_sample(drawing); self.request_run(drawing)
        job = drawing.jobs.get(kind='takeoff'); process_job(job.pk)
        handle = drawing.extraction['entities'][0]['handle']
        self.client.force_login(self.other)
        gets = [('project', [self.project.pk]), ('project_edit', [self.project.pk]), ('drawing', [drawing.pk]),
                ('decision', [drawing.pk, handle]), ('original', [drawing.pk]), ('job', [job.pk]),
                ('artifact', [job.pk, 'takeoff.xlsx'])]
        for name, args in gets:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 404, name)
        for name, args in [('project', [self.project.pk]), ('decision', [drawing.pk, handle]), ('run', [drawing.pk]), ('retry', [job.pk])]:
            self.assertEqual(self.client.post(reverse(name, args=args), {}).status_code, 404, name)

    def test_reference_preview_is_protected_and_not_extracted(self):
        drawing = self.upload(data=b'%PDF-1.4\n%%EOF', name='reference.pdf')
        self.assertFalse(drawing.jobs.exists())
        response = self.client.get(reverse('original', args=[drawing.pk]) + '?preview=1')
        self.assertEqual(response.status_code, 200); response.close()
        self.client.logout()
        self.assertEqual(self.client.get(reverse('original', args=[drawing.pk]) + '?preview=1').status_code, 302)

    def test_upload_validation(self):
        for name, body in [('drawing.dwg', b'AC1027'), ('evil.html', b'<html>'), ('empty.dxf', b''), ('fake.png', b'not a png')]:
            response = self.client.post(reverse('project', args=[self.project.pk]), {'file': SimpleUploadedFile(name, body)})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(Drawing.objects.count(), 0)

    def test_original_version_is_separate_and_preserved(self):
        first = self.upload()
        response = self.client.post(reverse('project', args=[self.project.pk]), {'file': SimpleUploadedFile('v2.dxf', self.sample.read_bytes()), 'previous': str(first.pk)})
        self.assertEqual(response.status_code, 302)
        second = Drawing.objects.latest('created_at')
        self.assertEqual(second.previous, first)
        self.assertNotEqual(first.storage_name, second.storage_name)
        self.assertEqual(storage_path(first.storage_name).read_bytes(), self.sample.read_bytes())

    def test_previous_version_cannot_reference_other_project(self):
        first = self.upload(); self.client.force_login(self.other)
        project = Project.objects.create(owner=self.other, name='Other')
        response = self.client.post(reverse('project', args=[project.pk]), {'file': SimpleUploadedFile('v2.dxf', self.sample.read_bytes()), 'previous': str(first.pk)})
        self.assertEqual(response.status_code, 404)

    def test_failure_and_explicit_retry_limit(self):
        drawing = self.upload(data=b'not valid dxf', extract_now=False)
        job = drawing.jobs.get()
        for attempt in range(1, 4):
            self.assertFalse(process_job(job.pk))
            job.refresh_from_db(); self.assertEqual(job.status, 'failed'); self.assertEqual(job.attempts, attempt)
            response = self.client.post(reverse('retry', args=[job.pk]))
            self.assertEqual(response.status_code, 302 if attempt < 3 else 409)
        self.assertTrue(job.error)

    def test_running_job_cannot_be_claimed_twice(self):
        drawing = self.upload(extract_now=False); job = drawing.jobs.get()
        Job.objects.filter(pk=job.pk).update(status='running')
        self.assertFalse(process_job(job.pk)); job.refresh_from_db()
        self.assertEqual(job.attempts, 0)

    def test_worker_processes_queue_and_recovers_interrupted_work(self):
        first = self.upload(extract_now=False); abandoned = first.jobs.get()
        Job.objects.filter(pk=abandoned.pk).update(status='running')
        second = self.upload(extract_now=False)
        call_command('runworker', once=True, verbosity=0)
        abandoned.refresh_from_db(); self.assertEqual(abandoned.status, 'failed')
        self.assertIn('이전 작업자', abandoned.error)
        self.assertEqual(second.jobs.get().status, 'succeeded')
        self.assertFalse(WorkerState.objects.exists())

    def test_changed_source_is_blocked(self):
        drawing = self.upload(extract_now=False)
        storage_path(drawing.storage_name).write_bytes(b'changed')
        job = drawing.jobs.get(); self.assertFalse(process_job(job.pk))
        job.refresh_from_db(); self.assertIn('해시가 변경', job.error)

    def test_missing_unit_or_confirmation_cannot_run(self):
        drawing = self.upload(); self.review_sample(drawing)
        response = self.client.post(reverse('run', args=[drawing.pk]), {'revision': drawing.review_revision})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(drawing.jobs.filter(kind='takeoff').exists())

    def test_unconfirmed_entities_cannot_be_implicitly_calculated(self):
        drawing = self.upload()
        self.assertEqual(self.request_run(drawing).status_code, 400)

    def test_storage_path_cannot_escape(self):
        with self.assertRaises(ValueError):
            storage_path('../db.sqlite3')

    def test_download_whitelist(self):
        drawing = self.upload(); job = drawing.jobs.get()
        self.assertEqual(self.client.get(reverse('artifact', args=[job.pk, 'db.sqlite3'])).status_code, 404)
