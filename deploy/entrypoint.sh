#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py createcachetable
# Erster Bestand echter Kölner Orte. Idempotent: vorhandene und gesperrte Orte werden übersprungen.
python manage.py orte_importieren data/orte_koeln.json
exec "$@"
