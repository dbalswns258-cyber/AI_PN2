from datetime import timedelta
from pathlib import Path
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from .models import WorkerState


@require_GET
def health(request):
    """No account or project information is exposed by this public health check."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        worker = WorkerState.objects.filter(pk=1).first()
        healthy = bool(worker and timezone.now() - worker.last_seen < timedelta(seconds=150)
                       and Path(settings.MEDIA_ROOT).is_dir())
    except Exception:
        healthy = False
    response = JsonResponse({'status': 'ok' if healthy else 'unavailable'}, status=200 if healthy else 503)
    response['Cache-Control'] = 'no-store'
    return response
