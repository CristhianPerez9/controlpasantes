import os
from pathlib import Path

# Ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# SECRET KEY (Mantén la tuya de desarrollo)
SECRET_KEY = 'django-insecure-tu-clave-secreta-aqui'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Aplicaciones instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Tus aplicaciones modulares
    'appauth',      # Aplicación para el PerfilUsuario (Estructura LDAP)
    'asistencia',   # Aplicación para el control de marcas y pasantes
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # CONTROL DE ACCESO CORPORATIVO (Middleware importado de tu appauth)
    'appauth.middleware.ControlAccesoMiddleware',
]

ROOT_URLCONF = 'control_asistencia.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'control_asistencia.wsgi.application'

# ================================================================
# CONFIGURACIÓN DE BASE DE DATOS (PostgreSQL LOCAL)
# ================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'asistencia_db',
        'USER': 'postgres',
        'PASSWORD': '123',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Validadores de contraseñas nativos
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Configuración Internacional (Bolivia)
LANGUAGE_CODE = 'es-bo'
TIME_ZONE = 'America/La_Paz'
USE_I18N = True
USE_TZ = True

# Archivos Estáticos
STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ================================================================
# GESTIÓN DE SESIONES, REDIRECCIONES Y LOGIN
# ================================================================
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'index_dashboard'
LOGOUT_REDIRECT_URL = 'registrar_asistencia'

# ================================================================
# CONFIGURACIÓN DE AUTENTICACIÓN (LDAP CORPORATIVO & LOCAL)
# ================================================================
AUTHENTICATION_BACKENDS = [
    # 1. Tu puente de autenticación hacia el Active Directory de COMTECO
    'appauth.auth_ldap.AutenticacionLDAP', 
    
    # 2. Respaldo nativo de Django (para cuentas creadas en Postgres o superusuarios)
    'django.contrib.auth.backends.ModelBackend', 
]
