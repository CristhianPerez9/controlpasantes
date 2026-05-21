from django.urls import path
from . import views

urlpatterns = [
    # ACCESO LIBRE: Terminal público de marcación (Pantalla Blanca con teclado)
    path('', views.registrar_asistencia, name='registrar_asistencia'),
    
    # ACCESO RESTRINGIDO: El supervisor debe loguearse para entrar a estas pantallas
    path('dashboard/', views.index_dashboard, name='index_dashboard'),
    path('supervisor/', views.panel_supervisor, name='panel_supervisor'),
    path('listado/', views.listado_detallado, name='listado_detallado'),
    path('reportes/', views.generacion_reportes, name='generacion_reportes'),
]