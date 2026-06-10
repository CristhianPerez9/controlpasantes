from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
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
    
    # NUEVA RUTA: Recibe la ID de la marca y la acción ('aprobar' o 'rechazar')
    path('asistencia/decidir/<int:marca_id>/<str:accion>/', views.decidir_horas_extra, name='decidir_horas_extra'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')