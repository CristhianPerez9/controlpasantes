@echo off
REM Script de configuración segura para Windows
REM Control de Asistencia - Setup seguro

setlocal enabledelayedexpansion

echo ==========================================
echo SETUP SEGURO - Control de Asistencia
echo ==========================================
echo.

REM Colores simplificados para Windows
echo [INFO] Verificando requisitos...

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instalar Python 3.10+
    exit /b 1
)

where openssl >nul 2>nul
if errorlevel 1 (
    echo [ADVERTENCIA] OpenSSL no encontrado. Algunas funciones limitadas.
)

REM 1. Verificar si .env.local ya existe
if exist ".env.local" (
    echo [ADVERTENCIA] .env.local ya existe. Respetando configuración existente.
    echo.
) else (
    echo [INFO] Creando .env.local con secretos seguros...
    
    REM Generar valores seguros usando Python
    for /f "delims=" %%i in ('python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"') do set DJANGO_SECRET=%%i
    
    REM Generar contraseña para PostgreSQL
    for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_urlsafe(25))"') do set POSTGRES_PASSWORD=%%i
    
    REM Generar contraseña para superusuario
    for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_hex(8))"') do set SUPERUSER_PASSWORD=%%i
    
    (
        echo # Generado automaticamente - MANTENER SEGURO
        echo DEBUG=False
        echo DJANGO_SECRET_KEY=!DJANGO_SECRET!
        echo DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,pasantes.comteco.com.bo
        echo CSRF_TRUSTED_ORIGINS=http://localhost:8000,https://pasantes.comteco.com.bo
        echo.
        echo # PostgreSQL
        echo POSTGRES_DB=asistencia_db
        echo POSTGRES_USER=pasantes
        echo POSTGRES_PASSWORD=!POSTGRES_PASSWORD!
        echo POSTGRES_HOST=192.9.200.162
        echo POSTGRES_PORT=5432
        echo.
        echo # Superusuario (cambiar despues del primer login
        echo DJANGO_SUPERUSER_USERNAME=admin
        echo DJANGO_SUPERUSER_EMAIL=admin@comteco.com.bo
        echo DJANGO_SUPERUSER_PASSWORD=!SUPERUSER_PASSWORD!
        echo.
        echo # LDAP
        echo LDAP_SERVER=ldap://192.9.200.51:389
        echo LDAP_USER_BASE=dc=comteco,dc=net
        echo LDAP_DOMAIN=COMTECO
    ) > .env.local
    
    echo [OK] .env.local creado
    echo.
    echo [INFO] Credenciales temporales:
    echo    Usuario admin: admin
    echo    Contraseña: !SUPERUSER_PASSWORD!
    echo.
    echo [ADVERTENCIA] CAMBIAR ESTOS VALORES DESPUES DEL PRIMER LOGIN
    echo.
)

REM 2. Verificar dependencias
echo [INFO] Instalando dependencias Python...
python -m pip install --upgrade pip -q
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Error al instalar dependencias
    exit /b 1
)
echo [OK] Dependencias instaladas
echo.

REM 3. Aplicar migraciones
echo [INFO] Aplicando migraciones...
python manage.py migrate --noinput
echo [OK] Migraciones aplicadas
echo.

REM 4. Recolectar archivos estáticos
echo [INFO] Recolectando archivos estáticos...
python manage.py collectstatic --noinput --clear
echo [OK] Archivos estáticos recolectados
echo.

echo ==========================================
echo [OK] SETUP COMPLETADO
echo ==========================================
echo.
echo Proximos pasos:
echo 1. Revisar .env.local y actualizar valores
echo 2. Ejecutar: python manage.py runserver
echo 3. Acceder a: http://localhost:8000
echo 4. Cambiar contraseña de admin en: http://localhost:8000/admin
echo.
pause
