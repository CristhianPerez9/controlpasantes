from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from asistencia import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- AUTENTICACIÓN ---
    path('login/', auth_views.LoginView.as_view(template_name='index.html'), name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),
    
    # --- RUTAS PRINCIPALES ---
    path('index/', views.index_dashboard, name='index_dashboard'),
    path('panel/', views.panel_supervisor, name='panel_supervisor'),
    path('pasantes/', views.lista_pasantes, name='lista_pasantes'),
    path('asistencia/control/', views.listado_detallado, name='listado_detallado'),
    path('reportes/', views.generacion_reportes, name='generacion_reportes'),
    
    # --- OPERACIÓN Y CONFIGURACIÓN ---
    path('', views.registrar_asistencia, name='registrar_asistencia'),
    path('turnos/', views.gestionar_turnos, name='gestionar_turnos'),
    path('importar-csv/', views.importar_datos_csv, name='importar_csv'),
    
    # --- RUTAS DE LOS PASANTES ---
    path('asistencia/decidir/<int:marca_id>/<str:accion>/', views.decidir_horas_extra, name='decidir_horas_extra'),
    path('portal/', views.portal_pasante, name='portal_pasante'), # <-- ESTA LÍNEA ARREGLA EL ERROR
]