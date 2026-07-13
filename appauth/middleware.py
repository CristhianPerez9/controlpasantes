from django.shortcuts import render
from django.urls import resolve

class ControlAccesoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Rutas libres sin autenticación (especificadas una sola vez)
        self.rutas_libres = frozenset(['login', 'logout', 'registrar_asistencia'])

    def __call__(self, request):
        # 1. Obtener el nombre de la ruta actual de forma segura
        try:
            match = resolve(request.path_info)
            current_url = match.url_name
        except:
            current_url = None

        # 2. Permitir SIEMPRE el Login, el Logout, el Administrador nativo
        # y la pantalla pública de marcación táctil de los pasantes
        if current_url in self.rutas_libres or request.path.startswith('/admin/'):
            return self.get_response(request)

        # 3. Control de acceso para supervisores en las rutas protegidas
        if request.user.is_authenticated:
            # Si el usuario no tiene un perfil cargado o está inactivo en PostgreSQL, le denegamos el acceso
            if hasattr(request.user, 'perfil') and not request.user.perfil.estado:
                return render(request, 'registration/sin_permiso.html', status=403)
                
        return self.get_response(request)