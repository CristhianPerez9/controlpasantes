from django.contrib import admin
from .models import Pasante, RegistroAsistencia

@admin.register(Pasante)
class PasanteAdmin(admin.ModelAdmin):
    # Columnas que se mostrarán en la tabla de pasantes del /admin/
    list_display = ('ci', 'nombre_completo', 'area', 'supervisor', 'fecha_nacimiento')
    
    # Buscador por Carnet de Identidad o por Nombre Completo
    search_fields = ('ci', 'nombre_completo', 'area')
    
    # Filtro lateral rápido por departamento o supervisor
    list_filter = ('area', 'supervisor')

@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    # Columnas para ver las marcas de entrada/salida en tiempo real
    list_display = ('get_pasante_nombre', 'get_pasante_ci', 'tipo', 'fecha', 'hora')
    
    # Filtros para que el administrador audite rápidamente por día o tipo
    list_filter = ('tipo', 'fecha')
    
    # Permitir buscar marcas escribiendo el CI o el nombre del pasante
    search_fields = ('pasante__ci', 'pasante__nombre_completo')

    # Funciones auxiliares para mostrar datos del pasante en la tabla de registros
    def get_pasante_nombre(self, obj):
        return obj.pasante.nombre_completo
    get_pasante_nombre.short_description = 'Pasante'

    def get_pasante_ci(self, obj):
        return obj.pasante.ci
    get_pasante_ci.short_description = 'CI'