from django.contrib import admin
from django.urls import path, include
from asistencia import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Mapeo de Módulos Operativos
    path('', views.registrar_asistencia, name='registrar_asistencia'),
    path('dashboard/', views.index_dashboard, name='index_dashboard'),
    path('panel/', views.panel_supervisor, name='panel_supervisor'),
    path('listado/', views.listado_detallado, name='listado_detallado'),
    path('reportes/', views.generacion_reportes, name='generacion_reportes'),
    path('pasantes/', views.lista_pasantes, name='lista_pasantes'),
    path('turnos/', views.gestionar_turnos, name='gestionar_turnos'),
]