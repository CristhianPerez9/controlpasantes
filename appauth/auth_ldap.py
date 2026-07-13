import sys
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db import DatabaseError
from ldap3 import Server, Connection, SUBTREE, NTLM
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars  # <-- LÍNEA CORREGIDA
from .models import PerfilUsuario

class AutenticacionLDAP(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Evita ejecutar operaciones LDAP durante comandos de gestión en consola
        if any(cmd in sys.argv for cmd in ("createsuperuser", "migrate", "makemigrations", "collectstatic")):
            return None

        if not username or not password:
            return None
        
        ATTRIBUTES_TO_FETCH = ['givenName', 'sn', 'mail', 'memberOf', 'sAMAccountName', 'name', 'distinguishedName', 'department']

        LDAP_SERVER = 'ldap://192.9.200.51:389'
        LDAP_USER_BASE = 'dc=comteco,dc=net'
        LDAP_DOMAIN = 'COMTECO'

        user_bind = f"{LDAP_DOMAIN}\\{username}"
        try:
            server = Server(LDAP_SERVER, get_info=SUBTREE)

            # Intento de enlace mediante NTLM corporativo
            try:
                conn = Connection(server, user=user_bind, password=password, authentication=NTLM, auto_bind=True)
            except Exception as ntlm_err:
                err_text = str(ntlm_err).lower()
                # Fallback a enlace simple si el entorno carece de soporte hash MD4 local
                if 'md4' in err_text or 'unsupported hash' in err_text or 'ntlm' in err_text:
                    try:
                        user_principal = f"{username}@comteco.net"
                        conn = Connection(server, user=user_principal, password=password, auto_bind=True)
                    except Exception as simple_err:
                        raise simple_err
                else:
                    raise ntlm_err

            # Ejecutar búsqueda en el Directorio Activo de COMTECO
            search_filter = f"(sAMAccountName={escape_filter_chars(username)})"
            conn.search(search_base=LDAP_USER_BASE, search_filter=search_filter, search_scope=SUBTREE, attributes=ATTRIBUTES_TO_FETCH)

            if not conn.entries:
                return self.sincronizar_usuario(username, firstname='', lastname='', email=f"{username}@comteco.com.bo", depto='Por Asignar')

            entry = conn.entries[0]

            # Mapeo de atributos remotos de la red corporativa
            firstname = str(entry.givenName) if 'givenName' in entry else ''
            lastname = str(entry.sn) if 'sn' in entry else ''
            email = str(entry.mail) if 'mail' in entry else ''
            depto = str(entry.department) if 'department' in entry else 'Por Asignar'

            return self.sincronizar_usuario(username, firstname, lastname, email, depto)

        except LDAPException as e:
            print(f"LDAP error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error during LDAP auth: {e}")
            return None

    def sincronizar_usuario(self, username, firstname, lastname, email, depto):
        """
        Crea o actualiza el usuario en auth_user de Django y su respectiva 
        extensión de PerfilUsuario en la tabla de la base de datos.
        """
        try:
            # 1. Sincronizar cuenta base de Django
            user, created = User.objects.get_or_create(username=username)
            user.first_name = firstname or ''
            user.last_name = lastname or ''
            user.email = email or ''
            user.set_unusable_password()  # La validación se gestiona en Active Directory, no local
            
            # Asignamos permisos la primera vez que entra: staff=True pero NO superuser
            # Los superusers deben asignarse manualmente en admin
            if created:
                user.is_staff = False  # Cambiar a False - solo login
                user.is_superuser = False  # Cambiar a False - no automático
                
            user.is_active = True
            user.save()

            # 2. Sincronizar el PerfilUsuario con los campos requeridos
            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            if created or perfil.unidad == 'Por Asignar':
                perfil.unidad = depto  # Hereda el departamento de la ficha institucional
            perfil.estado = True
            perfil.save()

            return user
            
        except DatabaseError as e:
            print(f"Database error while syncing LDAP user: {e}")
            return None

    def get_user(self, user_id):
        """
        Obligatorio: Django necesita esto para mantener al usuario logueado en las demás pantallas.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None