FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STATIC_ROOT=/app/staticfiles
WORKDIR /app

RUN useradd --create-home --uid 1000 app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN DJANGO_SECRET_KEY=build python manage.py collectstatic --noinput \
    && chown -R app:app /app
USER app

EXPOSE 8000
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--access-logformat", "%(m)s %(U)s %(s)s %(L)ss"]
