from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # 1. Pantalla pública del Reloj Marcador (Mouse + Teclado)
    path('', views.registrar_asistencia, name='registrar_asistencia'),
    
    # 2. Módulos de Administración y Control de Supervisores
    path('panel/', views.panel_supervisor, name='panel_supervisor'),
    path('listado/', views.listado_detallado, name='listado_detallado'),
    path('pasantes/', views.lista_pasantes, name='lista_pasantes'),
    path('reportes/', views.generacion_reportes, name='generacion_reportes'),
    path('turnos/', views.gestionar_turnos, name='gestionar_turnos'),
    path('dashboard/', views.index_dashboard, name='index_dashboard'),

    # 3. Cargador Masivo de Datos (Excel / CSV)
    path('importar/', views.importar_datos_csv, name='importar_datos_csv'),

    # 4. Gestión de Sesiones del Sistema
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]