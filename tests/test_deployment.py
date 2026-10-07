import tempfile
from datetime import timedelta
from pathlib import Path
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from projects.models import Project, WorkerState


class DeploymentTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.override = override_settings(MEDIA_ROOT=self.root)
        self.override.enable(); self.addCleanup(self.override.disable)

    def test_health_needs_worker_and_uses_no_private_details(self):
        self.assertEqual(self.client.get('/healthz/').status_code, 503)
        WorkerState.objects.create(pk=1, last_seen=timezone.now())
        response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        WorkerState.objects.update(last_seen=timezone.now() - timedelta(seconds=151))
        self.assertEqual(self.client.get('/healthz/').status_code, 503)

    @override_settings(SECURE_SSL_REDIRECT=True, SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
                       SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
                       CSRF_TRUSTED_ORIGINS=['https://testserver'])
    def test_proxy_https_login_cookie_csrf_and_redirect(self):
        get_user_model().objects.create_user('deploy-check', password='test-only-login-pass-456!')
        client = Client(enforce_csrf_checks=True)
        response = client.get(reverse('login'))
        self.assertEqual(response.status_code, 301)
        response = client.get(reverse('login'), HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.cookies['csrftoken']['secure'])
        response = client.post(reverse('login'), {'username': 'deploy-check', 'password': 'test-only-login-pass-456!',
                               'csrfmiddlewaretoken': client.cookies['csrftoken'].value},
                               HTTP_X_FORWARDED_PROTO='https', HTTP_ORIGIN='https://testserver')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.cookies['sessionid']['secure'])
        response = client.post(reverse('project_create'), {'name': 'blocked'}, HTTP_X_FORWARDED_PROTO='https',
                               HTTP_ORIGIN='https://attacker.invalid')
        self.assertEqual(response.status_code, 403)

    def test_test_project_label_and_default_business_project(self):
        user = get_user_model().objects.create_user('sample-owner')
        self.client.force_login(user)
        data = {'name': '연습 프로젝트', 'client': '가상 발주처', 'trade': '급수', 'status': 'review', 'is_sample': 'on'}
        response = self.client.post(reverse('project_create'), data)
        self.assertEqual(response.status_code, 302)
        sample = Project.objects.get(name='연습 프로젝트')
        self.assertTrue(sample.is_sample)
        self.assertContains(self.client.get(reverse('project', args=[sample.pk])), '테스트 프로젝트')
        ordinary = Project.objects.create(owner=user, name='새 업무')
        self.assertFalse(ordinary.is_sample)
        self.assertContains(self.client.get(reverse('home')), '업무 프로젝트')
