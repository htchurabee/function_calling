import threading
from celery import Celery
import os

celery = Celery(__name__)
celery.conf.broker_url = os.getenv('CELERY_BROKER_URL',default='redis://localhost:6379/0')
celery.conf.result_backend = os.getenv('CELERY_BACKEND_URL',default='redis://localhost:6379/1')
celery.conf.imports = ["services.structured_output.structured_output"]
celery.conf.update(
    broker_connection_retry_on_startup = True,
    worker_proc_alive_timeout =60,
    worker_concurrency = 2 
)



def strat_celery_worker():
    worker = celery.Worker(loglevel = 'info',pool = "solo")
    worker.start()
if __name__ == "__main__":
    #threading.Thread(target=strat_celery_worker,daemon=True).start()
    strat_celery_worker()
    


