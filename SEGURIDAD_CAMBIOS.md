# GUÍA DE MEJORAS DE SEGURIDAD IMPLEMENTADAS
# Este archivo resume los cambios sin afectar funcionalidad

## ✅ CAMBIOS REALIZADOS

### 1. settings.py - Configuración de seguridad
- [x] DEBUG=False por defecto (en lugar de True)
- [x] ALLOWED_HOSTS=localhost,127.0.0.1 (en lugar de '*')
- [x] CSRF_TRUSTED_ORIGINS específicos (en lugar de solo localhost)
- [x] SESSION_COOKIE_HTTPONLY=True (cookies solo HTTP)
- [x] CSRF_COOKIE_HTTPONLY=True 
- [x] SESSION_COOKIE_AGE=3600 (timeout 1 hora)
- [x] SECURE_BROWSER_XSS_FILTER=True
- [x] X_FRAME_OPTIONS='SAMEORIGIN'
- [x] Headers HTTPS automáticos en producción

### 2. auth_ldap.py - Protección contra inyección
- [x] Importar escape_filter_chars de ldap3
- [x] Sanitizar búsquedas LDAP con escape_filter_chars()
- [x] Cambiar is_staff=False para usuarios nuevos (no automático staff)
- [x] Cambiar is_superuser=False (no todos son admins automáticamente)

### 3. middleware.py - Código más limpio
- [x] Remover hardcoding de rutas
- [x] Usar frozenset para mejor rendimiento
- [x] Mantener lógica de autorización igual

### 4. .gitignore - Proteger secretos
- [x] Agregar .env.local
- [x] Agregar .env.*.local
- [x] Agregar archivos log
- [x] Agregar directorios build/dist

### 5. Archivos nuevos creados
- [x] .env.example - Plantilla de variables (sin secretos)
- [x] docker-compose.secure.yml - Compose sin secretos hardcodeados
- [x] setup_seguro.sh - Script de setup que genera secretos

---

## 🔧 CÓMO USAR LOS NUEVOS ARCHIVOS

### Primer Setup (desarrollo)
```bash
# 1. Copiar plantilla
cp .env.example .env.local

# 2. Ejecutar setup (genera secretos automáticamente)
bash setup_seguro.sh

# 3. Editar .env.local con valores reales si es necesario
nano .env.local
```

### Usando Docker
```bash
# Asegurar que .env.local existe
docker-compose -f docker-compose.secure.yml up -d
```

### Variables de entorno requeridas
```bash
DJANGO_SECRET_KEY          # Generada automáticamente por setup
POSTGRES_PASSWORD          # Generada automáticamente por setup
DEBUG=False                # Importante en producción
DJANGO_ALLOWED_HOSTS       # Especificar hosts reales
CSRF_TRUSTED_ORIGINS       # Dominios HTTPS
```

---

## ⚠️ CAMBIOS IMPORTANTES (PERO NO ROMPEN NADA)

### 1. Nuevos usuarios LDAP NO son automáticamente admins
**Antes:**
- Todo usuario que entra por LDAP → is_superuser=True

**Ahora:**
- Todo usuario que entra por LDAP → is_superuser=False
- Los admins se asignan manualmente en Django admin
- **Usuarios existentes conservan sus permisos**

**Solución:**
1. Dar acceso manual a usuarios específicos:
   - Admin → Usuarios → Seleccionar usuario
   - Marcar "Staff status" y "Superuser status"
   - Guardar

### 2. DEBUG por defecto es False
**Antes:**
- Entraba por .env pero por defecto True

**Ahora:**
- Por defecto False (más seguro)
- DEBUG=True solo si se especifica explícitamente

**Solución:**
- En desarrollo local: agregar `DEBUG=True` a .env.local
- En producción: dejar DEBUG=False

### 3. ALLOWED_HOSTS ahora es específico
**Antes:**
- Aceptaba cualquier host ('*')

**Ahora:**
- Solo localhost:127.0.0.1 por defecto
- Agregar dominios en DJANGO_ALLOWED_HOSTS

**Solución:**
- Para desarrollo: DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,*.local
- Para producción: DJANGO_ALLOWED_HOSTS=pasantes.comteco.com.bo,www.pasantes.comteco.com.bo

---

## 📋 CHECKLIST DE CONFIGURACIÓN

### Desarrollo Local
- [ ] Ejecutar: bash setup_seguro.sh
- [ ] Revisar .env.local generado
- [ ] Agregar DEBUG=True a .env.local
- [ ] python manage.py runserver
- [ ] Verificar que funciona todo igual

### Pre-Producción
- [ ] Generar new DJANGO_SECRET_KEY
- [ ] Generar new POSTGRES_PASSWORD fuerte
- [ ] Especificar DJANGO_ALLOWED_HOSTS reales
- [ ] Configurar CSRF_TRUSTED_ORIGINS con HTTPS
- [ ] Asignar admins específicos en Django admin
- [ ] Cambiar DJANGO_SUPERUSER_PASSWORD inicial
- [ ] Configurar HTTPS/SSL en proxy (nginx/Apache)

### Producción
- [ ] DEBUG=False (verificar)
- [ ] SECURE_SSL_REDIRECT=True (verificar)
- [ ] SESSION_COOKIE_SECURE=True (verificar)
- [ ] CSRF_COOKIE_SECURE=True (verificar)
- [ ] Usar .env.local con secretos (NO en repositorio)
- [ ] Usar docker-compose.secure.yml
- [ ] Revisar permisos de usuarios

---

## 🔐 SECRETOS QUE DEBES CAMBIAR

Los siguientes secretos DEBEN ser cambiados ANTES de producción:

1. **DJANGO_SECRET_KEY**
   - Se genera automáticamente con setup_seguro.sh
   - Verificar que está en .env.local

2. **POSTGRES_PASSWORD**
   - Se genera automáticamente con setup_seguro.sh
   - Mínimo 25 caracteres aleatorios

3. **DJANGO_SUPERUSER_PASSWORD**
   - Se genera automáticamente con setup_seguro.sh
   - Cambiar después del primer login en admin

4. **ALLOWED_HOSTS**
   - Especificar los dominios reales del sistema

---

## ✅ VERIFICACIÓN DE SEGURIDAD

Para verificar que los cambios están aplicados:

```bash
# 1. Verificar DEBUG
python manage.py shell
>>> from django.conf import settings
>>> settings.DEBUG  # Debe ser False

# 2. Verificar ALLOWED_HOSTS
>>> settings.ALLOWED_HOSTS  # Debe ser lista específica

# 3. Verificar permisos de usuario nuevo
# Crear usuario en LDAP y verificar:
# - is_staff debe ser False
# - is_superuser debe ser False
# - is_active debe ser True
```

---

## 📞 SOPORTE

Si algo no funciona:
1. Revisar .env.local existe y tiene valores
2. Ejecutar: python manage.py check
3. Revisar logs: tail -f logs/django.log
4. Recrear .env.local: rm .env.local && bash setup_seguro.sh
