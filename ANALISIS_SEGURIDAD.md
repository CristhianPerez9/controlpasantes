# 🔴 ANÁLISIS DE SEGURIDAD - PROYECTO CONTROL DE ASISTENCIA

**Fecha:** 2026-07-09  
**Nivel de Riesgo General:** 🔴 **CRÍTICO - MÁS DE 15 VULNERABILIDADES GRAVES**

---

## 📋 RESUMEN EJECUTIVO

El proyecto presenta **vulnerabilidades críticas** que lo hacen **NO APTO para producción**. Se han identificado problemas graves en:
- **Gestión de secretos** (contraseñas hardcodeadas)
- **Control de acceso** (permisos excesivos)
- **Configuración de seguridad** (DEBUG=True, ALLOWED_HOSTS=*)
- **Autenticación y autorización** (fallos severos)
- **Protección de datos** (exposición en variables de entorno)

---

## 🔴 VULNERABILIDADES CRÍTICAS (SEVERIDAD ALTA)

### 1. **SECRETOS HARDCODEADOS EN TEXTO PLANO** ⚠️⚠️⚠️
**Ubicación:** `settings.py` y `docker-compose.yml`

**Problema:**
```python
# settings.py línea 8
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-tu-clave-secreta-aqui')

# settings.py líneas 79-84
'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'C0mT3C02026'),
'HOST': os.environ.get('POSTGRES_HOST', '192.9.200.162'),

# docker-compose.yml líneas 10-11
POSTGRES_PASSWORD: C0mT3C02026
DJANGO_SUPERUSER_PASSWORD: admin123
```

**Riesgos:**
- ❌ Contraseña de PostgreSQL visible: `C0mT3C02026`
- ❌ Contraseña de superusuario: `admin123` (extremadamente débil)
- ❌ IP privada expuesta: `192.9.200.162`
- ❌ Credenciales en Docker Compose (repositorio público)

**Solución:**
```bash
# Usar .env.local (no commitear)
DJANGO_SECRET_KEY=<generar-con-django>
POSTGRES_PASSWORD=<contraseña-segura-40-caracteres>
DJANGO_SUPERUSER_PASSWORD=<contraseña-muy-segura>
```

---

### 2. **DEBUG=True EN PRODUCCIÓN** 🔴
**Ubicación:** `settings.py` línea 11

**Problema:**
```python
DEBUG = os.environ.get('DEBUG', 'True') == 'True'  # POR DEFECTO = True
```

**Riesgos:**
- ❌ Expone traceback completos con rutas del servidor
- ❌ Muestra valores de variables de entorno
- ❌ Devuelve información sensible en errores
- ❌ Permite acceso a debug toolbar (si está instalada)
- ❌ Archivos estáticos servidos por Django (lento y expone estructura)

**Impacto:** Un atacante puede obtener información del servidor completa con un simple error 404

**Solución:**
```python
DEBUG = os.environ.get('DEBUG', 'False') == 'True'  # False por defecto
```

---

### 3. **ALLOWED_HOSTS = '*' (CORS DESPROTEGIDO)** 🔴
**Ubicación:** `settings.py` línea 12

**Problema:**
```python
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')
# Acepta CUALQUIER HOST
```

**Riesgos:**
- ❌ Host header injection attacks
- ❌ Cache poisoning
- ❌ Password reset poisoning
- ❌ Brute force en tokens

**Solución:**
```python
ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS', 
    'localhost,127.0.0.1'
).split(',')

# En producción: ['pasantes.comteco.com.bo', 'www.pasantes.comteco.com.bo']
```

---

### 4. **CSRF_TRUSTED_ORIGINS INCOMPLETO** 🔴
**Ubicación:** `settings.py` líneas 13-15

**Problema:**
```python
CSRF_TRUSTED_ORIGINS = [
   'http://localhost',
   'http://127.0.0.1',
]
# En docker-compose: DJANGO_ALLOWED_HOSTS: "*"
# Contradicción: CSRF no protege realmente
```

**Riesgos:**
- ❌ CSRF attacks desde dominios no autorizados
- ❌ Inconsistencia entre configuraciones

**Solución:**
```python
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:3000'
).split(',')

# En producción: ['https://pasantes.comteco.com.bo']
```

---

### 5. **PERMISOS DESPROPORCIONADOS EN AUTENTICACIÓN LDAP** 🔴🔴
**Ubicación:** `appauth/auth_ldap.py` líneas 86-90

**Problema:**
```python
if created:
    user.is_staff = True      # ❌ TODO usuario nuevo es staff
    user.is_superuser = True  # ❌❌❌ TODO usuario nuevo es ADMIN
```

**Riesgos:**
- ❌ **TODO usuario nuevo que entra es automáticamente ADMINISTRADOR**
- ❌ Sin validación de rol o grupo
- ❌ Acceso total a admin panel
- ❌ Poder modificar bases de datos

**Impacto:** Cualquier empleado que se autentique en LDAP se convierte en admin

**Solución:**
```python
# Validar grupo LDAP
ldap_groups = entry.memberOf if 'memberOf' in entry else []
is_admin = any('cn=Administradores' in str(g) for g in ldap_groups)

if created:
    user.is_staff = is_admin
    user.is_superuser = is_admin
```

---

### 6. **CONTROL DE ACCESO DÉBIL EN MIDDLEWARE** 🔴
**Ubicación:** `appauth/middleware.py` líneas 19-20

**Problema:**
```python
def tiene_acceso_al_sistema(user):
    if user.username in ['cperezb', 'vvedia']:  # ❌ Hardcoded
        return True
    grupos_permitidos = ['Supervisores', 'supervisores', 'RRHH', 'rrhh']
```

**Riesgos:**
- ❌ Usuarios hardcodeados (caso sensible diferenciado)
- ❌ Doble grupo "Supervisores"/"supervisores"
- ❌ Fácilmente explotable

**Solución:**
```python
def tiene_acceso_al_sistema(user):
    grupos_permitidos = ['supervisores', 'rrhh', 'administradores']
    return user.groups.filter(name__in=grupos_permitidos).exists()
```

---

### 7. **FALTA DE ENCRIPTACIÓN EN TRÁNSITO (No HTTPS/TLS)** 🔴
**Ubicación:** `settings.py` - Falta de configuración

**Problema:**
- ❌ No hay `SECURE_SSL_REDIRECT = True`
- ❌ No hay `SECURE_HSTS_SECONDS`
- ❌ No hay `SESSION_COOKIE_SECURE = True`
- ❌ No hay `CSRF_COOKIE_SECURE = True`

**Riesgos:**
- ❌ Man-in-the-middle attacks
- ❌ Credenciales interceptadas
- ❌ Sesiones hijacked
- ❌ LDAP password en texto plano

**Solución (agregar a settings.py):**
```python
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
```

---

### 8. **AUTENTICACIÓN LDAP CON FALLBACK INSEGURO** 🔴
**Ubicación:** `appauth/auth_ldap.py` líneas 26-37

**Problema:**
```python
try:
    conn = Connection(server, user=user_bind, password=password, authentication=NTLM, auto_bind=True)
except Exception as ntlm_err:
    err_text = str(ntlm_err).lower()
    if 'md4' in err_text or 'ntlm' in err_text:
        try:
            user_principal = f"{username}@comteco.net"
            conn = Connection(server, user=user_principal, password=password, auto_bind=True)
```

**Riesgos:**
- ❌ Fallback a LDAP simple sin validar el error
- ❌ Contraseñas en texto plano en conexión LDAP
- ❌ Sin timeout configurado
- ❌ Sin rate limiting

**Solución:**
```python
try:
    conn = Connection(
        server, 
        user=user_bind, 
        password=password, 
        authentication=NTLM, 
        auto_bind=True,
        receive_timeout=10
    )
except LDAPException:
    return None  # Fallar seguro, no hacer fallback
```

---

### 9. **CONTRASEÑA POSTGRESQL DÉBIL** 🔴
**Ubicación:** `settings.py` y `docker-compose.yml`

**Problema:**
- ❌ Contraseña: `C0mT3C02026` (patrón predecible: NombreEmpresa+Año)
- ❌ Solo 11 caracteres
- ❌ Sin caracteres especiales variados
- ❌ Hardcodeada en versión de control

**Solución:**
Generar con: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

---

### 10. **SUPERUSUARIO CON CONTRASEÑA POR DEFECTO** 🔴🔴
**Ubicación:** `docker-compose.yml` línea 16

**Problema:**
```yaml
DJANGO_SUPERUSER_PASSWORD: admin123  # ❌ EXTREMADAMENTE DÉBIL
```

**Riesgos:**
- ❌ Usuario: `cperezb` con contraseña: `admin123`
- ❌ Acceso total al admin panel
- ❌ Se puede cambiar con simple brute force

**Solución:**
```yaml
# No crear automáticamente, o usar contraseña temporal fuerte
# Generar: `openssl rand -base64 16`
```

---

## 🟡 VULNERABILIDADES ALTAS

### 11. **VALIDACIÓN INSUFICIENTE DE ENTRADA EN VISTAS**
**Ubicación:** `asistencia/views.py`

**Problema:**
- ❌ No hay validación visible de entrada de usuario
- ❌ Uso de `get_object_or_404` sin autorización
- ❌ No hay sanitización de CSV

**Solución:**
```python
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods

@require_http_methods(["POST"])
@login_required
def crear_registro(request):
    # Validar entrada
    if not request.POST.get('fecha'):
        raise ValidationError("Fecha requerida")
```

---

### 12. **INYECCIÓN SQL EN BÚSQUEDAS LDAP** 🟡
**Ubicación:** `appauth/auth_ldap.py` línea 40

**Problema:**
```python
search_filter = f"(sAMAccountName={username})"  # ❌ String interpolation
```

**Riesgos:**
- ❌ LDAP injection attacks
- ❌ Elusión de autenticación

**Solución:**
```python
from ldap3 import escape_filter_chars
search_filter = f"(sAMAccountName={escape_filter_chars(username)})"
```

---

### 13. **NO HAY RATE LIMITING** 🟡
**Ubicación:** Falta en todo el proyecto

**Problema:**
- ❌ Brute force en login
- ❌ Ataques de fuerza bruta sin límite
- ❌ DDoS posible

**Solución:**
```bash
pip install django-ratelimit
# Configurar en views.py para login
```

---

### 14. **LOGS SIN ROTACIÓN Y SIN SEGURIDAD** 🟡
**Ubicación:** `settings.py` - Falta configuración de logging

**Problema:**
- ❌ Errores no se registran correctamente
- ❌ Sin auditoría de accesos
- ❌ Sin alertas de seguridad

**Solución:**
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/django/app.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
}
```

---

### 15. **AUSENCIA DE VALIDACIÓN DE PERFILES DE USUARIO** 🟡
**Ubicación:** `appauth/auth_ldap.py` línea 99

**Problema:**
```python
perfil.estado = True  # ❌ Siempre activo sin validar
```

**Riesgos:**
- ❌ No hay desactivación de usuarios
- ❌ Sin auditoría

---

### 16. **POSTGRESQL EXPUESTO DIRECTAMENTE** 🟡
**Ubicación:** `settings.py` línea 79

**Problema:**
```python
'HOST': os.environ.get('POSTGRES_HOST', '192.9.200.162'),
```

**Riesgos:**
- ❌ IP interna expuesta en código
- ❌ Acceso directo a PostgreSQL sin proxy/SSH

**Solución:**
```python
# Usar tunnel SSH o proxy
# Nunca exponer PostgreSQL directamente
```

---

## 🔵 VULNERABILIDADES MEDIAS

### 17. **FALTA DE VALIDACIÓN CSRF EN FORMULARIOS**
- No visible en vistas
- Asegurarse de incluir `{% csrf_token %}` en todos los forms

### 18. **SIN PROTECCIÓN CONTRA XSS**
- No hay `|escape` o `|safe` apropiadamente usado
- Falta `Content-Security-Policy` header

### 19. **INFORMACIÓN SENSIBLE EN ERRORES**
- Errores LDAP mostrados en output
- Stacktraces visibles en DEBUG

### 20. **NO VALIDATE ON SERVER SIDE DATES**
- Validaciones posiblemente solo en cliente

---

## 📊 TABLA RESUMEN

| # | Vulnerabilidad | Severidad | Estado | Línea |
|---|---|---|---|---|
| 1 | Secretos Hardcodeados | 🔴 CRÍTICA | ❌ ACTIVA | settings.py:8,79-84 |
| 2 | DEBUG=True por defecto | 🔴 CRÍTICA | ❌ ACTIVA | settings.py:11 |
| 3 | ALLOWED_HOSTS='*' | 🔴 CRÍTICA | ❌ ACTIVA | settings.py:12 |
| 4 | Permisos excesivos LDAP | 🔴 CRÍTICA | ❌ ACTIVA | auth_ldap.py:86-90 |
| 5 | Sin HTTPS/TLS | 🔴 CRÍTICA | ❌ ACTIVA | settings.py |
| 6 | Control acceso débil | 🔴 CRÍTICA | ❌ ACTIVA | middleware.py:19 |
| 7 | CSRF débil | 🔴 CRÍTICA | ❌ ACTIVA | settings.py:13 |
| 8 | LDAP injection | 🟡 ALTA | ❌ ACTIVA | auth_ldap.py:40 |
| 9 | Rate limiting | 🟡 ALTA | ❌ FALTA | - |
| 10 | Logging inseguro | 🟡 ALTA | ❌ FALTA | - |

---

## 🛠️ PLAN DE ACCIÓN INMEDIATO

### **FASE 1 - EMERGENCIA (Hoy)**
- [ ] Cambiar contraseña PostgreSQL
- [ ] Cambiar contraseña superusuario admin123
- [ ] Cambiar SECRET_KEY
- [ ] Establecer DEBUG=False

### **FASE 2 - CRÍTICA (Esta semana)**
- [ ] Implementar .env.local con secretos
- [ ] Añadir SSL/TLS
- [ ] Corregir permisos LDAP
- [ ] Implementar rate limiting

### **FASE 3 - IMPORTANTE (Próximas 2 semanas)**
- [ ] Implementar logging seguro
- [ ] Añadir validación de entrada
- [ ] Configurar ALLOWED_HOSTS correcto
- [ ] CSP headers

---

## ✅ CHECKLIST DE CORRECCIÓN

```
[ ] 1. Generar nuevo SECRET_KEY con django
[ ] 2. Crear archivo .env.local (NO commitear)
[ ] 3. Cambiar DEBUG default a False
[ ] 4. Establecer ALLOWED_HOSTS específicos
[ ] 5. Corregir permisos LDAP (validar grupos)
[ ] 6. Implementar SSL/TLS
[ ] 7. Añadir SECURE_SSL_REDIRECT
[ ] 8. Sanitizar búsquedas LDAP
[ ] 9. Implementar Rate limiting
[ ] 10. Configurar logging rotatoria
[ ] 11. Añadir HSTS headers
[ ] 12. Validar entrada en vistas
[ ] 13. Añadir CSP headers
[ ] 14. Revisar templates por XSS
[ ] 15. Documentar políticas de seguridad
```

---

## 🚨 CONCLUSIÓN

**ESTADO ACTUAL:** 🔴 **NO APTO PARA PRODUCCIÓN**

El proyecto tiene **vulnerabilidades críticas que lo hacen vulnerable a:**
- Acceso administrativo no autorizado
- Inyección de código
- Robo de credenciales
- Manipulación de datos
- Ataques CSRF, XSS, LDAP injection

**RECOMENDACIÓN:** 
No desplegar a producción hasta completar las correcciones de Fase 1 y 2.

---

**Próximos pasos:** Procederé a generar archivos de corrección automática si lo autorizas.
