import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-tu-clave-secreta-aqui')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')
# produccion
DEBUG = False
# SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', SECRET_KEY)
# ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
CSRF_TRUSTED_ORIGINS = [
    'https://pasantes.comteco.com.bo',
    'https://www.pasantes.comteco.com.bo',
]
# desarrollo local
# CSRF_TRUSTED_ORIGINS = [
#    'http://localhost',
#    'http://127.0.0.1', ]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Tus aplicaciones del proyecto integradas correctamente
    'asistencia',
    'appauth',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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


# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'asistencia_db'),
        'USER': os.environ.get('POSTGRES_USER', 'pasantes'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'C0mT3C02026'),
        'HOST': os.environ.get('POSTGRES_HOST', '192.9.200.162'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = 'es-bo'

TIME_ZONE = 'America/La_Paz'

USE_I18N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

# STATIC_URL = '/static/'
# STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# # CORRECCIÓN PARA DOCKER: Carpeta donde se recopilarán todos los estáticos
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# # Configuración de Redirecciones de Autenticación
# LOGIN_REDIRECT_URL = 'panel_supervisor'
# LOGOUT_REDIRECT_URL = 'login'
# LOGIN_URL = 'login'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = '/static/'

# CORRECCIÓN IMPORTANTE: Verificar si el directorio existe
static_dir = os.path.join(BASE_DIR, 'static')
if os.path.exists(static_dir):
    STATICFILES_DIRS = [static_dir]
else:
    STATICFILES_DIRS = []  # Lista vacía para evitar el warning
    # Crear el directorio si estamos en desarrollo
    if DEBUG:
        os.makedirs(static_dir, exist_ok=True)
        STATICFILES_DIRS = [static_dir]

STATIC_ROOT = os.environ.get('STATIC_ROOT', os.path.join(BASE_DIR, 'staticfiles'))

# Asegurar que STATIC_ROOT existe
os.makedirs(STATIC_ROOT, exist_ok=True)

# ==============================================================================
# CONFIGURACIÓN DE AUTENTICACIÓN PERSONALIZADA CORREGIDA (LDAP / COMTECO)
# ==============================================================================

AUTHENTICATION_BACKENDS = [
    'appauth.auth_ldap.AutenticacionLDAP',
    'django.contrib.auth.backends.ModelBackend',
]

# Le dice a Django que confíe en el encabezado del proxy que indica que la conexión original era HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')