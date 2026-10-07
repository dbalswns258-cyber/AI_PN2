"""Production entry point: one private persistent volume, one web service, one worker.

The hosting platform restarts this process if either child exits unexpectedly.
This is deliberately single-instance for SQLite/local-file consistency.
"""
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.umask(0o077)
    os.environ.setdefault('AI_PN2_ENV', 'production')
    os.environ['AI_PN2_DEBUG'] = '0'
    if not os.environ.get('AI_PN2_DATA_DIR'):
        raise SystemExit('Set AI_PN2_DATA_DIR to the persistent disk directory.')
    os.environ.setdefault('XDG_CACHE_HOME', str(Path(os.environ['AI_PN2_DATA_DIR']) / 'cache'))
    for args in [('scripts/prepare_data.py',), ('manage.py', 'migrate', '--noinput'),
                 ('manage.py', 'collectstatic', '--noinput'), ('manage.py', 'check', '--deploy')]:
        subprocess.run([sys.executable, *args], check=True)
    children = []
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    port = str(int(os.environ.get('PORT', '8000')))
    try:
        children.append(subprocess.Popen([sys.executable, '-u', 'manage.py', 'runworker']))
        children.append(subprocess.Popen([sys.executable, '-m', 'gunicorn', 'config.wsgi:application',
            '--bind', '0.0.0.0:' + port, '--workers', '1', '--threads', '2', '--timeout', '90',
            '--graceful-timeout', '20', '--access-logfile', '-', '--error-logfile', '-']))
        while not stopping:
            for child in children:
                if child.poll() is not None:
                    print('A required service exited; stopping for platform restart.', file=sys.stderr)
                    return 1
            time.sleep(.25)
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=25)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait()


if __name__ == '__main__':
    sys.exit(main())
