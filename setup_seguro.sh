#!/bin/bash
# Script de configuración segura del proyecto
# Genera secretos y prepara el entorno

echo "=========================================="
echo "SETUP SEGURO - Control de Asistencia"
echo "=========================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Verificar si .env.local ya existe
if [ -f ".env.local" ]; then
    echo -e "${YELLOW}⚠️  .env.local ya existe. Respetando configuración existente.${NC}"
else
    echo -e "${GREEN}✓ Creando .env.local${NC}"
    
    # Generar Django Secret Key
    DJANGO_SECRET=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    
    # Generar contraseña PostgreSQL segura
    POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    
    # Generar contraseña de superusuario segura
    SUPERUSER_PASSWORD=$(openssl rand -base64 16)
    
    # Crear archivo .env.local
    cat > .env.local << EOF
# Generado automáticamente - MANTENER SEGURO
DEBUG=False
DJANGO_SECRET_KEY=${DJANGO_SECRET}
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,pasantes.comteco.com.bo
CSRF_TRUSTED_ORIGINS=http://localhost:8000,https://pasantes.comteco.com.bo

# PostgreSQL
POSTGRES_DB=asistencia_db
POSTGRES_USER=pasantes
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_HOST=192.9.200.162
POSTGRES_PORT=5432

# Superusuario (cambiar después del primer login)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@comteco.com.bo
DJANGO_SUPERUSER_PASSWORD=${SUPERUSER_PASSWORD}

# LDAP
LDAP_SERVER=ldap://192.9.200.51:389
LDAP_USER_BASE=dc=comteco,dc=net
LDAP_DOMAIN=COMTECO
EOF
    
    chmod 600 .env.local
    echo -e "${GREEN}✓ .env.local creado (permisos 600)${NC}"
    echo ""
    echo -e "${YELLOW}📝 Credenciales temporales:${NC}"
    echo "   Usuario admin: admin"
    echo "   Contraseña: ${SUPERUSER_PASSWORD}"
    echo ""
    echo -e "${RED}⚠️  CAMBIAR ESTOS VALORES DESPUÉS DEL PRIMER LOGIN${NC}"
fi

# 2. Verificar dependencias Python
echo ""
echo "Verificando dependencias..."
pip install -q -r requirements.txt 2>/dev/null || {
    echo -e "${RED}✗ Error al instalar dependencias${NC}"
    exit 1
}
echo -e "${GREEN}✓ Dependencias instaladas${NC}"

# 3. Aplicar migraciones
echo ""
echo "Aplicando migraciones..."
python manage.py migrate --noinput 2>/dev/null || {
    echo -e "${RED}✗ Error al aplicar migraciones${NC}"
    exit 1
}
echo -e "${GREEN}✓ Migraciones aplicadas${NC}"

# 4. Recolectar archivos estáticos
echo ""
echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear 2>/dev/null
echo -e "${GREEN}✓ Archivos estáticos recolectados${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "✓ SETUP COMPLETADO"
echo "==========================================${NC}"
echo ""
echo "Próximos pasos:"
echo "1. Revisar .env.local y actualizar valores (especialmente contraseñas)"
echo "2. Ejecutar: python manage.py runserver"
echo "3. Acceder a: http://localhost:8000"
echo "4. Cambiar contraseña de admin en: http://localhost:8000/admin"
