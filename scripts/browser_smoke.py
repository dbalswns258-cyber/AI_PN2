"""Optional real-browser end-to-end check. Uses an isolated temporary database.

Run with an interpreter containing Playwright and system Chromium:
python scripts/browser_smoke.py --python /path/to/application/venv/bin/python
"""
import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', required=True)
    parser.add_argument('--screenshot')
    parser.add_argument('--production', action='store_true', help='Use Gunicorn/WhiteNoise and verify restart + backup restore')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='ai-pn2-browser-') as tmp:
        temp = Path(tmp)
        password = secrets.token_urlsafe(28)
        env = {**os.environ, 'AI_PN2_DATA_DIR': str(temp / 'state'), 'AI_PN2_DEBUG': '1',
               'XDG_CACHE_HOME': str(temp / 'cache'), 'SMOKE_PASSWORD': password}
        if args.production:
            # This local loopback test has no TLS terminator. Proxy HTTPS is covered separately.
            env.update({'AI_PN2_ENV': 'production', 'AI_PN2_HTTPS': '0', 'AI_PN2_TRUST_PROXY': '0',
                        'AI_PN2_ALLOWED_HOSTS': '127.0.0.1,localhost'})
        def run(*command, **kwargs):
            return subprocess.run([args.python, *command], cwd=root, env=env, check=True, capture_output=True, text=True, **kwargs)
        run('scripts/prepare_data.py')
        run('manage.py', 'migrate', '--noinput')
        run('manage.py', 'shell', input="import os\nfrom django.contrib.auth import get_user_model\nget_user_model().objects.create_user('browser-test', password=os.environ['SMOKE_PASSWORD'])\n")
        run('-m', 'takeoff.cli', 'sample', str(temp / 'sample'))
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        url = f'http://127.0.0.1:{port}'
        env['PORT'] = str(port)
        with open(temp / 'services.log', 'w') as log:
            processes = []
            def stop_services():
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                for process in processes:
                    try:
                        process.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait()
                processes.clear()
            def start_services():
                commands = [[args.python, 'scripts/serve.py']] if args.production else [
                    [args.python, 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload'],
                    [args.python, 'manage.py', 'runworker']]
                for command in commands:
                    processes.append(subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=log))
                for _ in range(80):
                    try:
                        with urlopen(url + '/healthz/', timeout=1) as response:
                            if response.status == 200:
                                break
                    except OSError:
                        time.sleep(.25)
                else:
                    raise RuntimeError('Server did not become ready')
            try:
                start_services()
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox', '--disable-dev-shm-usage'])
                    context = browser.new_context(viewport={'width': 1440, 'height': 1050})
                    page = context.new_page()
                    page_errors = []
                    page.on('pageerror', lambda e: page_errors.append(str(e)))
                    page.goto(url)
                    assert '/accounts/login/' in page.url
                    page.locator('[name=username]').fill('browser-test')
                    page.locator('[name=password]').fill(password)
                    page.get_by_role('button', name='로그인', exact=True).click()
                    page.get_by_role('link', name='＋ 새 프로젝트').click()
                    page.get_by_label('공사명').fill('합성 도면 브라우저 검증')
                    page.get_by_label('발주처').fill('테스트 전용 — 실제 공사 아님')
                    page.get_by_label('테스트 프로젝트').check()
                    page.get_by_role('button', name='저장 / 실행').click()
                    page.locator('input[type=file]').set_input_files(temp / 'sample/sample.dxf')
                    page.get_by_role('button', name='보관하고 객체 추출 요청').click()
                    drawing_url = page.url
                    for _ in range(40):
                        if page.get_by_role('heading', name='검토용 평면 길이 산출').count():
                            break
                        page.wait_for_timeout(250); page.reload()
                    else:
                        raise AssertionError('DXF extraction did not complete')
                    decisions = json.loads((temp / 'sample/decisions.json').read_text())
                    for handle, decision in decisions.items():
                        page.goto(drawing_url + f'objects/{handle}/')
                        page.get_by_label('확인 상태').select_option(decision['status'])
                        if decision['status'] == 'confirmed':
                            page.get_by_label('계통').select_option('water')
                            page.get_by_label('호칭지름 (mm)').fill(decision['diameter_mm'])
                        page.get_by_label('확정·제외의 근거').fill(decision['evidence'])
                        page.get_by_role('button', name='확인 정보 저장').click()
                    page.get_by_label('확인한 모델 공간 길이 단위').select_option('mm')
                    page.get_by_label('단위 확인 근거').fill('합성 3-4-5 삼각형의 5000 mm 치수')
                    page.get_by_label('관경별 합계를 표시할 소수 자릿수').select_option('3')
                    page.get_by_label('관경별 합계 반올림 방법').select_option('ROUND_HALF_UP')
                    page.get_by_label('평면 직접 길이의 검토용 결과이며').check()
                    page.get_by_role('button', name='산출 작업 요청').click()
                    for _ in range(60):
                        if page.get_by_role('heading', name='길이 산출 · 완료').count():
                            break
                        page.wait_for_timeout(250); page.reload()
                    else:
                        raise AssertionError('Takeoff did not complete')
                    assert page.get_by_text('8.142', exact=True).count() == 1
                    assert page.get_by_text('3.000', exact=True).count() == 1
                    with page.expect_download() as download:
                        page.get_by_role('link', name='계산 원본 JSON ↓').click()
                    downloaded = temp / 'result.json'; download.value.save_as(downloaded)
                    result = json.loads(downloaded.read_text())
                    assert result['counts'] == {'confirmed': 3, 'excluded': 1, 'pending': 5}
                    with page.expect_download() as download:
                        page.get_by_role('link', name='엑셀 근거 / 집계 ↓').click()
                    download.value.save_as(temp / 'takeoff.xlsx')
                    assert (temp / 'takeoff.xlsx').stat().st_size > 1000
                    if args.production:
                        result_url = page.url
                        with page.expect_download() as original_download:
                            page.goto(drawing_url)
                            page.get_by_role('link', name='원본 다운로드 ↓').click()
                        original_download.value.save_as(temp / 'downloaded-source.dxf')
                        expected_hash = hashlib.sha256((temp / 'sample/sample.dxf').read_bytes()).hexdigest()
                        assert hashlib.sha256((temp / 'downloaded-source.dxf').read_bytes()).hexdigest() == expected_hash
                        run('scripts/backup.py', '--destination', str(temp / 'backup'))
                        for restore in (False, True):
                            stop_services()
                            if restore:
                                shutil.copytree(temp / 'backup', temp / 'restored')
                                env['AI_PN2_DATA_DIR'] = str(temp / 'restored')
                            start_services()
                            page.goto(result_url)
                            assert page.get_by_role('heading', name='길이 산출 · 완료').count() == 1
                            assert page.get_by_text('8.142', exact=True).count() == 1
                            page.goto(drawing_url)
                            with page.expect_download() as download:
                                page.get_by_role('link', name='원본 다운로드 ↓').click()
                            download.value.save_as(temp / 'after-restart.dxf')
                            assert hashlib.sha256((temp / 'after-restart.dxf').read_bytes()).hexdigest() == expected_hash
                        page.goto(result_url)
                        print('PASS: production Gunicorn/WhiteNoise, account/session/project/file persistence across restart, backup restoration')
                    if args.screenshot:
                        page.screenshot(path=args.screenshot, full_page=True)
                    page.set_viewport_size({'width': 390, 'height': 844})
                    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                    page.get_by_role('button', name='로그아웃').click()
                    page.goto(drawing_url)
                    assert '/accounts/login/' in page.url
                    assert not page_errors, page_errors
                    browser.close()
                    print('PASS: browser login, project, upload, worker extraction, 4 reviews, takeoff, JSON/XLSX downloads, mobile layout, logout/access denial')
            except Exception:
                print((temp / 'services.log').read_text()[-6000:])
                raise
            finally:
                stop_services()


if __name__ == '__main__':
    main()
