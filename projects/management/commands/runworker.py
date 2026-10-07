import fcntl
import signal
import time
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from projects.models import Job, WorkerState
from projects.tasks import process_job


def timeout_handler(signum, frame):
    raise TimeoutError('작업 제한 시간 120초를 초과했습니다. 더 작은 구간으로 나누어 등록하세요.')


class Command(BaseCommand):
    help = 'SQLite 개인용 단일 작업자. 웹과 별도 프로세스로 실행하세요.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='대기 작업을 처리한 뒤 종료')

    def handle(self, *args, **options):
        with open(settings.DATA_DIR / 'worker.lock', 'a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise CommandError('다른 작업자가 실행 중입니다.') from exc
            Job.objects.filter(status='running').update(status='failed', finished_at=timezone.now(),
                error='이전 작업자가 중단되었습니다. 원본과 설정을 확인한 뒤 명시적으로 재시도하세요.')
            signal.signal(signal.SIGALRM, timeout_handler)
            self.stdout.write('Worker ready (single process, 120s/job, max 3 attempts).')
            try:
                while True:
                    WorkerState.objects.update_or_create(pk=1, defaults={'last_seen': timezone.now()})
                    job = Job.objects.filter(status='queued', attempts__lt=3).order_by('created_at').first()
                    if job:
                        signal.alarm(120)
                        try:
                            ok = process_job(job.id)
                            self.stdout.write(f'{job.id}: {"succeeded" if ok else "failed"}')
                        finally:
                            signal.alarm(0)
                    elif options['once']:
                        break
                    else:
                        time.sleep(1)
            except KeyboardInterrupt:
                pass
            finally:
                WorkerState.objects.filter(pk=1).delete()
