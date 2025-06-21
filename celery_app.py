from celery import Celery

# Celery 애플리케이션 생성
app = Celery('tasks')
app.config_from_object('celeryconfig')

@app.task
def add(x, y):
    return x + y
