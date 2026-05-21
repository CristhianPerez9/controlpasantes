from django.contrib import admin
from .models import PerfilUsuario

@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'unidad', 'fecha', 'estado')
    list_filter = ('unidad', 'estado')
    search_fields = ('user__username', 'unidad')

    # Funciones auxiliares para mostrar el nombre de usuario de la relación OneToOne
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Usuario (LDAP)'