import os
import csv
import datetime  
from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.conf import settings
from .models import Pasante, RegistroAsistencia, TurnoPasante, AreaEmpresa
from appauth.models import PerfilUsuario
from django.contrib.auth.models import User
from django.core.paginator import Paginator  
from django.core.mail import send_mail

# --- FUNCIONES AUXILIARES INTERNAS ---
def obtener_nombre_completo_ldap(user):
    nombre_completo = f"{user.first_name} {user.last_name}".strip()
    if not nombre_completo:
        nombre_completo = user.username.upper()
    return nombre_completo

def es_super_admin(user):
    """ Regla Maestra (legacy/fallback) """
    if user.username in ['cperezb', 'vvedia', 'vvedia@comteco.com.bo']:
        return True
    if hasattr(user, 'perfil') and user.perfil.unidad:
        if 'RECURSOS HUMANOS' in user.perfil.unidad.upper():
            return True
    if user.is_superuser:
        return True
    return False

def calcular_horas_pasante(pasante):
    """ Calcula las horas totales hechas por un pasante (solo registros aprobados) """
    marcas = RegistroAsistencia.objects.filter(pasante=pasante)
    horas_totales = 0.0
    marcas_por_dia = {}
    
    for m in marcas:
        if m.fecha not in marcas_por_dia:
            marcas_por_dia[m.fecha] = []
        marcas_por_dia[m.fecha].append(m)
    
    for fecha_dia, lista_marcas in marcas_por_dia.items():
        entrada = None
        for m in lista_marcas:
            if m.tipo == 'ENTRADA':
                entrada = m.hora.replace(second=0, microsecond=0)
            elif m.tipo == 'SALIDA' and m.estado == 'APROBADO' and entrada is not None:
                salida_limpia = m.hora.replace(second=0, microsecond=0)
                dt_entrada = datetime.combine(date.today(), entrada)
                dt_salida = datetime.combine(date.today(), salida_limpia)
                horas_totales += (dt_salida - dt_entrada).total_seconds() / 3600.0
                entrada = None
    return round(horas_totales, 1)


# --- CARGADOR AUXILIAR ---
@login_required
def importar_datos_csv(request):
    base_dir = settings.BASE_DIR
    archivos_en_raiz = os.listdir(base_dir)
    
    # 1. IMPORTAR ÁREAS DE LA EMPRESA (ARCHIVO SIRHU)
    archivo_areas = None
    for f in archivos_en_raiz:
        if 'SIRHU' in f.upper() and f.endswith('.csv'):
            archivo_areas = os.path.join(base_dir, f)
            break
            
    areas_creadas = 0
    if archivo_areas:
        try:
            with open(archivo_areas, 'r', encoding='utf-8-sig', errors='ignore') as f:
                contenido_areas = f.read().splitlines()
                if contenido_areas:
                    sep = ';' if ';' in contenido_areas[0] or (len(contenido_areas) > 1 and ';' in contenido_areas[1]) else ','
                    lector_areas = csv.reader(contenido_areas, delimiter=sep)
                    
                    for fila in lector_areas:
                        if not fila or len(fila) < 3: 
                            continue
                        
                        col_cero = str(fila[0]).strip().upper()
                        nombre_area = str(fila[2]).strip().upper()
                        
                        if 'CÓDIGO' in col_cero or 'SIRHU' in col_cero or nombre_area == 'DESCRIPCIÓN':
                            continue
                        
                        if nombre_area:
                            try:
                                obj = AreaEmpresa.objects.filter(nombre=nombre_area).first()
                                if not obj:
                                    AreaEmpresa.objects.create(nombre=nombre_area)
                                    areas_creadas += 1
                            except Exception:
                                pass
        except Exception as e:
            return HttpResponse(f"<h3>❌ Error leyendo archivo SIRHU: {e}</h3>")

    # 2. IMPORTAR ASISTENCIA ANTIGUA
    archivo_detectado = None
    for f in archivos_en_raiz:
        if f.lower() in ['datos.xls', 'datos.xlsx', 'datos.csv'] and 'sirhu' not in f.lower():
            archivo_detectado = os.path.join(base_dir, f)
            break

    if not archivo_detectado and not archivo_areas:
        return HttpResponse(f"<h3>❌ Archivos No Encontrados en la carpeta principal: {base_dir}</h3>")

    contador_marcas = 0
    if archivo_detectado:
        columnas_excel = {'Deysi': (1, 2), 'Yusara': (4, 5), 'Alison': (7, 8), 'Sheyling': (10, 11)}
        user_supervisor = request.user

        pasantes_db = {}
        for nombre in columnas_excel.keys():
            obj, creado = Pasante.objects.get_or_create(
                ci=f"CI-{nombre.upper()}",
                defaults={'nombre_completo': nombre, 'area': 'GERENCIA DE TECNOLOGIAS DE INFORMACION', 'horas_requeridas': 360}
            )
            obj.supervisores.add(user_supervisor)
            obj.save()
            pasantes_db[nombre] = obj

        try:
            with open(archivo_detectado, 'r', encoding='utf-8-sig', errors='ignore') as f:
                contenido = f.read().splitlines()

            separador = ';' if ';' in contenido[0] else ','
            lector = csv.reader(contenido, delimiter=separador)
            lineas = list(lector)

            indice_inicio = 0
            for i, fila in enumerate(lineas):
                if fila and str(fila[0]).strip().lower() == 'fecha':
                    indice_inicio = i + 1
                    break

            for fila in lineas[indice_inicio:]:
                if not fila or not str(fila[0]).strip(): continue
                fecha_str = str(fila[0]).strip()
                try:
                    fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except:
                    continue

                for nombre, columnas in columnas_excel.items():
                    col_entrada, col_salida = columnas
                    if len(fila) > col_salida:
                        hora_in = str(fila[col_entrada].strip() or '')
                        hora_out = str(fila[col_salida].strip() or '')
                        pasante_actual = pasantes_db[nombre]

                        if hora_in and hora_in not in ['00:00:00', '']:
                            RegistroAsistencia.objects.get_or_create(pasante=pasante_actual, fecha=fecha_obj, hora=hora_in, tipo='ENTRADA', estado='APROBADO')
                            contador_marcas += 1
                        if hora_out and hora_out not in ['00:00:00', '']:
                            RegistroAsistencia.objects.get_or_create(pasante=pasante_actual, fecha=fecha_obj, hora=hora_out, tipo='SALIDA', estado='APROBADO')
                            contador_marcas += 1
        except Exception as e:
            return HttpResponse(f"<h3>❌ Error en archivo de asistencias: {e}</h3>")

    return HttpResponse(f"<h2>🎉 ¡Operación Exitosa!</h2><p>Se registraron {areas_creadas} nuevas áreas/departamentos desde el SIRHU.</p><p>Se cargaron {contador_marcas} marcaciones.</p><br><a href='/panel/'>Volver al Panel</a>")


# --- REGISTRO PUBLICO DESDE MOSTRADOR ---
def registrar_asistencia(request):
    if request.method == 'POST':
        ci_digitado = request.POST.get('ci_value')
        
        if not ci_digitado:
            messages.error(request, "Por favor, introduzca su Carnet de Identidad.")
            return redirect('registrar_asistencia')
            
        try:
            pasante = Pasante.objects.get(ci=ci_digitado)
            fecha_hoy = date.today()
            
            marca_entrada = RegistroAsistencia.objects.filter(pasante=pasante, fecha=fecha_hoy, tipo='ENTRADA').first()
            marca_salida = RegistroAsistencia.objects.filter(pasante=pasante, fecha=fecha_hoy, tipo='SALIDA').first()
            estado_registro = 'APROBADO'
            
            if not marca_entrada:
                RegistroAsistencia.objects.create(pasante=pasante, tipo='ENTRADA', estado=estado_registro)
                messages.success(request, f"¡Marca de ENTRADA registrada con éxito para {pasante.nombre_completo}!")
                
            elif marca_entrada and not marca_salida:
                ahora_hora = datetime.now().time()
                limite_salida = datetime.strptime('16:15', '%H:%M').time() 
                
                if ahora_hora > limite_salida:
                    estado_registro = 'PENDIENTE'
                    
                nueva_marca = RegistroAsistencia.objects.create(pasante=pasante, tipo='SALIDA', estado=estado_registro)
                
                supervisores_lista = pasante.supervisores.all()
                correos = [s.email if s.email else f"{s.username}@comteco.com.bo" for s in supervisores_lista]
                
                if correos:
                    primer_sup = supervisores_lista.first()
                    nombre_sup = obtener_nombre_completo_ldap(primer_sup)
                    
                    if estado_registro == 'PENDIENTE':
                        asunto = f"⚠️ Solicitud de Horas Extra Pendiente - {pasante.nombre_completo}"
                        cuerpo = f"Estimado(a) {nombre_sup},\n\n" \
                                 f"El pasante {pasante.nombre_completo} registró una SALIDA extraordinaria a las {nueva_marca.hora.strftime('%H:%M')}.\n" \
                                 f"Quedó PENDIENTE de aprobación en el Panel de Control.\n\nSistema TI COMTECO."
                        send_mail(asunto, cuerpo, 'asistencia.pasantes@comteco.com.bo', correos, fail_silently=True)
                        messages.warning(request, f"Salida registrada. Al exceder las 16:15 se guardó como pendiente de aprobación por su supervisor.")
                    else:
                        messages.success(request, f"¡Marca de SALIDA registrada con éxito para {pasante.nombre_completo}!")
                        
                    horas_hechas = calcular_horas_pasante(pasante)
                    horas_restantes = float(pasante.horas_requeridas) - horas_hechas
                    
                    if 24 <= horas_restantes <= 30:
                        asunto_fin = f"🎓 AVISO: Conclusión de Pasantía Próxima - {pasante.nombre_completo}"
                        cuerpo_fin = f"Estimado(a) {nombre_sup},\n\n" \
                                     f"Le informamos que el pasante {pasante.nombre_completo} está en su semana final de pasantía.\n" \
                                     f"Total requerido: {pasante.horas_requeridas} hrs\n" \
                                     f"Horas restantes aproximadas: {round(horas_restantes, 1)} hrs.\n\n" \
                                     f"Por favor, prepare la evaluación de desempeño correspondiente con RRHH.\n\nSistema TI COMTECO."
                        send_mail(asunto_fin, cuerpo_fin, 'asistencia.pasantes@comteco.com.bo', correos, fail_silently=True)
                else:
                    if estado_registro == 'PENDIENTE':
                        messages.warning(request, f"Salida registrada fuera de horario regular. Pendiente de aprobación.")
                    else:
                        messages.success(request, f"¡Marca de SALIDA registrada con éxito para {pasante.nombre_completo}!")

            else:
                messages.error(request, f"Atención {pasante.nombre_completo}: Ya completaste tus marcaciones por hoy.")
                
            return redirect('registrar_asistencia')
            
        except Pasante.DoesNotExist:
            messages.error(request, "Error: El Carnet de Identidad no está registrado.")
            return redirect('registrar_asistencia')
            
    return render(request, 'registro_de_asistencia_pasante_marca_actualizada/code.html')


# --- VISTA PARA APROBAR / RECHAZAR ---
@login_required
def decidir_horas_extra(request, marca_id, accion):
    marca = get_object_or_404(RegistroAsistencia, id=marca_id)
    perfil = getattr(request.user, 'perfil', None)
    tipo_rol = perfil.tipo if perfil else 'SUPERVISOR'
    puede_asignar = (tipo_rol in ['SUPER_ADMIN', 'ADMINISTRADOR'] or request.user.is_superuser or request.user.username in ['cperezb', 'vvedia'])
    
    if puede_asignar or request.user in marca.pasante.supervisores.all():
        if accion == 'aprobar':
            marca.estado = 'APROBADO'
            marca.save()
            messages.success(request, f"Marcación extraordinaria de {marca.pasante.nombre_completo} aprobada con éxito.")
        elif accion == 'rechazar':
            marca.estado = 'RECHAZADO'
            marca.save()
            messages.warning(request, f"Marcación extraordinaria de {marca.pasante.nombre_completo} rechazada.")
    return redirect('panel_supervisor')


@login_required
def index_dashboard(request):
    return redirect('panel_supervisor')


@login_required
def panel_supervisor(request):
    supervisor_actual = request.user
    
    if not hasattr(supervisor_actual, 'perfil') or not supervisor_actual.perfil.estado:
        if not supervisor_actual.is_superuser:
            return render(request, 'espera_aprobacion.html')

    perfil = getattr(supervisor_actual, 'perfil', None)
    tipo_rol = perfil.tipo if perfil else 'SUPERVISOR'
    mi_unidad = perfil.unidad if perfil else "Sin Área"
    
    puede_asignar = (tipo_rol in ['SUPER_ADMIN', 'ADMINISTRADOR'] or supervisor_actual.is_superuser or supervisor_actual.username in ['cperezb', 'vvedia'])
    
    if puede_asignar:
        pasantes = Pasante.objects.all()
        asistencias = RegistroAsistencia.objects.filter(fecha=date.today()).select_related('pasante').order_by('-hora')
        pendientes = RegistroAsistencia.objects.filter(estado='PENDIENTE').select_related('pasante').order_by('-fecha', '-hora')
    else:
        pasantes = Pasante.objects.filter(supervisores=supervisor_actual)
        asistencias = RegistroAsistencia.objects.filter(pasante__in=pasantes, fecha=date.today()).select_related('pasante').order_by('-hora')
        pendientes = RegistroAsistencia.objects.filter(estado='PENDIENTE', pasante__supervisores=supervisor_actual).select_related('pasante').order_by('-fecha', '-hora').distinct()

    horas_hoy = 0.0
    alertas_tardanza = 0
    marcas_por_pasante = {}
    
    for m in asistencias:
        if m.pasante_id not in marcas_por_pasante:
            marcas_por_pasante[m.pasante_id] = []
        marcas_por_pasante[m.pasante_id].append(m)
        if m.tipo == 'ENTRADA' and m.hora > datetime.strptime('08:15', '%H:%M').time():
            alertas_tardanza += 1

    for pid, marcas in marcas_por_pasante.items():
        marcas_asc = sorted(marcas, key=lambda x: x.hora)
        entrada = None
        for m in marcas_asc:
            if m.tipo == 'ENTRADA':
                entrada = m.hora.replace(second=0, microsecond=0)
            elif m.tipo == 'SALIDA' and m.estado == 'APROBADO' and entrada is not None:
                salida_limpia = m.hora.replace(second=0, microsecond=0)
                dt_entrada = datetime.combine(date.today(), entrada)
                dt_salida = datetime.combine(date.today(), salida_limpia)
                horas_hoy += (dt_salida - dt_entrada).total_seconds() / 3600.0
                entrada = None

    context = {
        'pasantes': pasantes, 
        'asistencias': asistencias, 
        'asistencias_pendientes': pendientes,
        'mi_unidad': "Toda la Empresa" if puede_asignar else mi_unidad,
        'horas_hoy': round(horas_hoy, 1),
        'alertas_tardanza': alertas_tardanza,
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual)
    }
    return render(request, 'panel_del_supervisor_marca_actualizada/code.html', context)


@login_required
def listado_detallado(request):
    supervisor_actual = request.user
    
    if not hasattr(supervisor_actual, 'perfil') or not supervisor_actual.perfil.estado:
        if not supervisor_actual.is_superuser:
            return render(request, 'espera_aprobacion.html')

    perfil = getattr(supervisor_actual, 'perfil', None)
    tipo_rol = perfil.tipo if perfil else 'SUPERVISOR'
    mi_unidad = perfil.unidad if perfil else "Sin Área"
    
    puede_asignar = (tipo_rol in ['SUPER_ADMIN', 'ADMINISTRADOR'] or supervisor_actual.is_superuser or supervisor_actual.username in ['cperezb', 'vvedia'])
    
    if puede_asignar:
        pasantes_queryset = Pasante.objects.all().order_by('nombre_completo')
        queryset_marcas = RegistroAsistencia.objects.all().select_related('pasante')
    else:
        pasantes_queryset = Pasante.objects.filter(supervisores=supervisor_actual).order_by('nombre_completo')
        queryset_marcas = RegistroAsistencia.objects.filter(pasante__in=pasantes_queryset).select_related('pasante')

    lista_con_calculos = []
    horas_area = 0.0
    
    for p in pasantes_queryset:
        horas_totales_p = calcular_horas_pasante(p)
        horas_area += horas_totales_p
        lista_con_calculos.append({
            'objeto': p,
            'horas_hechas': horas_totales_p
        })

    fechas_unicas = queryset_marcas.order_by('-fecha').values_list('fecha', flat=True).distinct()
    paginator = Paginator(fechas_unicas, 1)  
    pagina_actual = paginator.get_page(request.GET.get('page'))

    reporte_final = []
    if pagina_actual.object_list:
        fecha_del_dia = pagina_actual.object_list[0]
        marcas_del_dia = queryset_marcas.filter(fecha=fecha_del_dia).order_by('pasante__nombre_completo', 'hora')
        
        marcas_agrupadas = {}
        for m in marcas_del_dia:
            if m.pasante not in marcas_agrupadas:
                marcas_agrupadas[m.pasante] = {'entrada': None, 'salida': None}
            if m.tipo == 'ENTRADA' and not marcas_agrupadas[m.pasante]['entrada']:
                marcas_agrupadas[m.pasante]['entrada'] = m.hora.replace(second=0, microsecond=0)
            elif m.tipo == 'SALIDA' and m.estado == 'APROBADO':
                marcas_agrupadas[m.pasante]['salida'] = m.hora.replace(second=0, microsecond=0)

        for pasante, datos in marcas_agrupadas.items():
            horas_dia = 0.0
            if datos['entrada'] and datos['salida']:
                dt_entrada = datetime.combine(fecha_del_dia, datos['entrada'])
                dt_salida = datetime.combine(fecha_del_dia, datos['salida'])
                horas_dia = (dt_salida - dt_entrada).total_seconds() / 3600.0
                
            reporte_final.append({
                'pasante': pasante,
                'fecha': fecha_del_dia,
                'entrada': datos['entrada'],
                'salida': datos['salida'],
                'horas_dia': round(horas_dia, 2)
            })

    context = {
        'reportes_asistencia': reporte_final,      
        'pagina_actual': pagina_actual,            
        'horas_area': round(horas_area, 1),        
        'pasantes_calculados': lista_con_calculos, 
        'mi_unidad': "Toda la Empresa" if puede_asignar else mi_unidad,
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual)
    }
    return render(request, 'listado_detallado_de_asistencia_marca_actualizada/code.html', context)


@login_required
def generacion_reportes(request):
    supervisor_actual = request.user
    
    if not hasattr(supervisor_actual, 'perfil') or not supervisor_actual.perfil.estado:
        if not supervisor_actual.is_superuser:
            return render(request, 'espera_aprobacion.html')

    perfil = getattr(supervisor_actual, 'perfil', None)
    tipo_rol = perfil.tipo if perfil else 'SUPERVISOR'
    mi_unidad = perfil.unidad if perfil else "Sin Área"
    
    puede_asignar = (tipo_rol in ['SUPER_ADMIN', 'ADMINISTRADOR'] or supervisor_actual.is_superuser or supervisor_actual.username in ['cperezb', 'vvedia'])
    
    if puede_asignar:
        pasantes_lista = Pasante.objects.all().order_by('nombre_completo')
        queryset_marcas = RegistroAsistencia.objects.all().select_related('pasante')
    else:
        pasantes_lista = Pasante.objects.filter(supervisores=supervisor_actual).order_by('nombre_completo')
        queryset_marcas = RegistroAsistencia.objects.filter(pasante__in=pasantes_lista).select_related('pasante')
        
    filtro_pasante = request.GET.get('pasante_id')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    pasante_seleccionado = None
    
    if filtro_pasante and filtro_pasante != 'todos':
        queryset_marcas = queryset_marcas.filter(pasante_id=filtro_pasante)
        pasante_seleccionado = pasantes_lista.filter(id=filtro_pasante).first()
        
    if fecha_desde: queryset_marcas = queryset_marcas.filter(fecha__gte=fecha_desde)
    if fecha_hasta: queryset_marcas = queryset_marcas.filter(fecha__lte=fecha_hasta)
        
    queryset_marcas = queryset_marcas.order_by('fecha', 'hora')
    
    marcas_agrupadas = {}
    for m in queryset_marcas:
        clave = (m.pasante, m.fecha)
        if clave not in marcas_agrupadas:
            marcas_agrupadas[clave] = {'entrada': None, 'salida': None}
        if m.tipo == 'ENTRADA' and not marcas_agrupadas[clave]['entrada']:
            marcas_agrupadas[clave]['entrada'] = m.hora.replace(second=0, microsecond=0)
        elif m.tipo == 'SALIDA' and m.estado == 'APROBADO':
            marcas_agrupadas[clave]['salida'] = m.hora.replace(second=0, microsecond=0)

    reporte_final = []
    total_horas_periodo = 0.0

    for (pasante, fecha), datos in marcas_agrupadas.items():
        horas_dia = 0.0
        if datos['entrada'] and datos['salida']:
            dt_entrada = datetime.combine(fecha, datos['entrada'])
            dt_salida = datetime.combine(fecha, datos['salida'])
            horas_dia = (dt_salida - dt_entrada).total_seconds() / 3600.0
            total_horas_periodo += horas_dia
        reporte_final.append({'pasante': pasante, 'fecha': fecha, 'entrada': datos['entrada'], 'salida': datos['salida'], 'horas_dia': round(horas_dia, 2)})

    reporte_final.sort(key=lambda x: x['fecha'], reverse=True)
        
    context = {
        'pasantes': pasantes_lista, 
        'reportes_asistencia': reporte_final, 
        'total_horas_periodo': round(total_horas_periodo, 1),
        'mi_unidad': "Toda la Empresa" if puede_asignar else mi_unidad,
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual),
        'filtro_pasante': filtro_pasante, 'fecha_desde': fecha_desde, 'fecha_hasta': fecha_hasta, 'pasante_seleccionado': pasante_seleccionado
    }
    return render(request, 'generaci_n_de_reportes_marca_actualizada/code.html', context)


# =========================================================
# LÓGICA DE ALTA CORPORATIVA Y CÁLCULO DE PROGRESO
# =========================================================
@login_required
def lista_pasantes(request):
    supervisor_actual = request.user
    
    # COMPROBACIÓN DE PANTALLA AMIGABLE
    if not hasattr(supervisor_actual, 'perfil') or not supervisor_actual.perfil.estado:
        if not supervisor_actual.is_superuser:
            return render(request, 'espera_aprobacion.html')

    perfil = getattr(supervisor_actual, 'perfil', None)
    tipo_rol = perfil.tipo if perfil else 'SUPERVISOR'
    mi_unidad = perfil.unidad if perfil else "Sin Área"
    
    puede_asignar = (tipo_rol in ['SUPER_ADMIN', 'ADMINISTRADOR'] or supervisor_actual.is_superuser or supervisor_actual.username in ['cperezb', 'vvedia'])

    todos_los_usuarios = []
    areas_disponibles = []
    if puede_asignar:
        todos_los_usuarios = User.objects.filter(is_active=True).select_related('perfil').order_by('username')
        
        areas_bd = list(AreaEmpresa.objects.values_list('nombre', flat=True))
        if areas_bd:
            areas_disponibles = sorted(areas_bd)
        else:
            areas_brutas = [u.perfil.unidad for u in todos_los_usuarios if hasattr(u, 'perfil') and u.perfil.unidad]
            areas_disponibles = sorted(list(set(areas_brutas)))

    if request.method == 'POST':
        ci = request.POST.get('ci')
        nombre = request.POST.get('nombre_completo')
        f_inicio = request.POST.get('fecha_inicio')
        f_fin = request.POST.get('fecha_fin')
        horas_req = request.POST.get('horas_requeridas', 360)
        
        area_asignada = mi_unidad
        
        if puede_asignar:
            area_digitada = request.POST.get('area_asignada')
            if area_digitada:
                area_asignada = area_digitada

        if ci and nombre and f_inicio and f_fin:
            if Pasante.objects.filter(ci=ci).exists():
                messages.error(request, f"Error: Ya existe un pasante con el CI {ci}.")
            else:
                nuevo_pasante = Pasante.objects.create(
                    ci=ci, nombre_completo=nombre, area=area_asignada,
                    fecha_inicio=f_inicio, fecha_fin=f_fin, horas_requeridas=horas_req
                )
                
                if puede_asignar:
                    supervisores_ids = request.POST.getlist('supervisores_ids')
                    if supervisores_ids:
                        for s_id in supervisores_ids:
                            try:
                                u_sup = User.objects.get(id=s_id)
                                nuevo_pasante.supervisores.add(u_sup)
                            except User.DoesNotExist:
                                pass
                    else:
                        nuevo_pasante.supervisores.add(supervisor_actual)
                    messages.success(request, f"¡Pasante {nombre} asignado a {area_asignada}!")
                else:
                    nuevo_pasante.supervisores.add(supervisor_actual)
                    messages.success(request, f"¡Pasante {nombre} guardado exitosamente!")
            return redirect('lista_pasantes')

    if puede_asignar:
        pasantes_queryset = Pasante.objects.all().order_by('nombre_completo')
    else:
        pasantes_queryset = Pasante.objects.filter(supervisores=supervisor_actual).order_by('nombre_completo')
        
    lista_con_calculos = []
    for p in pasantes_queryset:
        horas_hechas_redond = calcular_horas_pasante(p)
        horas_req_float = float(p.horas_requeridas)
        horas_restantes = max(0.0, round(horas_req_float - horas_hechas_redond, 1))
        
        porcentaje = 0
        if horas_req_float > 0:
            porcentaje = min(100, int((horas_hechas_redond / horas_req_float) * 100))
            
        alerta_conclusion = horas_restantes <= 30
        
        lista_con_calculos.append({
            'objeto': p,
            'horas_hechas': horas_hechas_redond,
            'horas_restantes': horas_restantes,
            'porcentaje': porcentaje,
            'alerta_conclusion': alerta_conclusion
        })
        
    context = {
        'pasantes_calculados': lista_con_calculos, 
        'mi_unidad': "Toda la Empresa" if puede_asignar else mi_unidad,
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual),
        'puede_asignar': puede_asignar,
        'todos_los_usuarios': todos_los_usuarios,
        'areas_disponibles': areas_disponibles
    }
    return render(request, 'lista_pasantes_marca_actualizada/code.html', context)


@login_required
def gestionar_turnos(request):
    supervisor_actual = request.user
    
    if not hasattr(supervisor_actual, 'perfil') or not supervisor_actual.perfil.estado:
        if not supervisor_actual.is_superuser:
            return render(request, 'espera_aprobacion.html')

    perfil = getattr(supervisor_actual, 'perfil', None)
    tipo_rol = perfil.tipo if perfil else 'SUPERVISOR'
    mi_unidad = perfil.unidad if perfil else "Sin Área"
    
    puede_asignar = (tipo_rol in ['SUPER_ADMIN', 'ADMINISTRADOR'] or supervisor_actual.is_superuser or supervisor_actual.username in ['cperezb', 'vvedia'])
    
    if puede_asignar:
        pasantes = Pasante.objects.all().order_by('nombre_completo')
    else:
        pasantes = Pasante.objects.filter(supervisores=supervisor_actual).order_by('nombre_completo')
        
    if request.method == 'POST':
        pasante_id = request.POST.get('pasante_id')
        dia_seleccionado = request.POST.get('dia')
        turno = request.POST.get('turno')
        entrada = request.POST.get('hora_entrada')
        salida = request.POST.get('hora_salida')
        obs = request.POST.get('observacion', '')
        
        if pasante_id and dia_seleccionado and turno and entrada and salida:
            p_obj = get_object_or_404(Pasante, id=pasante_id)
            dias_a_guardar = ['LU', 'MA', 'MI', 'JU', 'VI'] if dia_seleccionado == 'LV' else [dia_seleccionado]
            
            for d in dias_a_guardar:
                TurnoPasante.objects.update_or_create(
                    pasante=p_obj, dia=d, turno=turno,
                    defaults={'hora_entrada': entrada, 'hora_salida': salida, 'observacion': obs}
                )
            messages.success(request, f"¡Horario de {turno.lower()} asignado a {p_obj.nombre_completo}!")
            return redirect('gestionar_turnos')

    turnos = TurnoPasante.objects.filter(pasante__in=pasantes).select_related('pasante').order_by('pasante', 'dia', 'turno')
    context = {
        'pasantes': pasantes, 
        'turnos': turnos, 
        'mi_unidad': "Toda la Empresa" if puede_asignar else mi_unidad, 
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual)
    }
    return render(request, 'gestionar_turnos_marca_actualizada/code.html', context)


@login_required
def cerrar_sesion(request):
    logout(request)
    return redirect('login')