#!/bin/sh
# Arranque del contenedor web: migra, carga datos del caso (solo si la base está vacía) y levanta gunicorn.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput >/dev/null

if [ "${CARGAR_DATOS_CASO:-1}" = "1" ]; then
    python manage.py cargar_datos_caso --si-vacia --historial
fi

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
