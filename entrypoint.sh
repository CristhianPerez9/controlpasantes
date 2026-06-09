#!/bin/sh
set -e

# 1. Esperar a la base de datos para evitar errores de conexión temprana
if [ -n "$POSTGRES_HOST" ]; then
  echo "Esperando a PostgreSQL en $POSTGRES_HOST:$POSTGRES_PORT..."
  while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
    sleep 0.5
  done
  echo "PostgreSQL está listo!"
fi

# 2. Aplicar migraciones de forma segura
echo "Aplicando migraciones existentes..."
python manage.py migrate --noinput

# 3. Recolectar archivos estáticos para producción
echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear --no-post-process

# 4. Crear superusuario de forma segura (Automático)
# echo "Creando/actualizando superusuario..."
# python manage.py shell << EOF
# import os
# from django.contrib.auth import get_user_model
# User = get_user_model()
# username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'cperezb')
# email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'cperezb@comteco.com.bo')
# password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

# if not User.objects.filter(username=username).exists():
#     User.objects.create_superuser(username, email, password)
#     print(f"Superusuario '{username}' creado exitosamente!")
# else:
#     print(f"Superusuario '{username}' ya existe.")
# EOF

echo "Inicialización completada exitosamente!"

# 5. ¡ESTA LÍNEA ES LA QUE MANTIENE EL SERVIDOR VIVO (Gunicorn)!
exec "$@"