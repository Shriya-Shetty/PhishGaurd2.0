"""Basic Celery task queue setup stub for PhishGuard."""

def create_celery_app(app_name='phishguard', broker_url='redis://localhost:6379/0'):
    try:
        from celery import Celery
    except ImportError as exc:
        raise ImportError('Celery is required for task queue support.') from exc

    celery = Celery(app_name, broker=broker_url)
    celery.conf.update(
        result_backend='redis://localhost:6379/0',
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
    )
    return celery


def register_tasks(celery):
    @celery.task(name='phishguard.predict_async')
    def predict_async(payload):
        return {'status': 'queued', 'payload': payload}

    return predict_async
