import os
import csv
import json
import datetime
from datetime import datetime, date, timedelta
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

def tiene_acceso_al_sistema(user):
    if user.username in ['cperezb', 'vvedia']:
        return True
    grupos_permitidos = ['Supervisores', 'supervisores', 'RRHH', 'rrhh']
    return user.groups.filter(name__in=grupos_permitidos).exists()

def es_admin_rrhh(user):
    if user.username in ['cperezb', 'vvedia']:
        return True
    grupos_rrhh = ['RRHH', 'rrhh']
    return user.groups.filter(name__in=grupos_rrhh).exists()

def obtener_nombre_completo_ldap(user):
    nombre_completo = f"{user.first_name} {user.last_name}".strip()
    if not nombre_completo:
        nombre_completo = user.username.upper()
    return nombre_completo

def calcular_horas_pasante(pasante):
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

@login_required
def importar_datos_csv(request):
    if not tiene_acceso_al_sistema(request.user):
        return render(request, 'espera_aprobacion.html')

    base_dir = settings.BASE_DIR
    archivos_en_raiz = os.listdir(base_dir)
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
            for i, enumerate_fila in enumerate(lineas):
                if enumerate_fila and str(enumerate_fila[0]).strip().lower() == 'fecha':
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

@login_required
def decidir_horas_extra(request, marca_id, accion):
    if not tiene_acceso_al_sistema(request.user):
        return render(request, 'espera_aprobacion.html')

    marca = get_object_or_404(RegistroAsistencia, id=marca_id)
    puede_asignar = es_admin_rrhh(request.user)
    
    if puede_asignar or request.user in marca.pasante.supervisores.all():
        if accion == 'aprobar':
            marca.estado = 'APROBADO'
            marca.save()
            messages.success(request, f"Marcación extraordinaria de {marca.pasante.nombre_completo} aprobada con éxito.")
        elif accion == 'rechazar':
            marca.estado = 'RECHAZADO'
            marca.save()
            messages.warning(request, f"Marcación extraordinaria de {marca.pasante.nombre_completo} rechazada.")
            
    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer)

@login_required
def index_dashboard(request):
    if not tiene_acceso_al_sistema(request.user):
        return render(request, 'espera_aprobacion.html')
    return redirect('panel_supervisor')

@login_required
def panel_supervisor(request):
    if not tiene_acceso_al_sistema(request.user):
        return render(request, 'espera_aprobacion.html')

    supervisor_actual = request.user
    puede_asignar = es_admin_rrhh(supervisor_actual)
    perfil = getattr(supervisor_actual, 'perfil', None)
    mi_unidad = perfil.unidad if perfil else "Sin Área"
    
    if puede_asignar:
        pasantes = Pasante.objects.all().order_by('nombre_completo')
        asistencias = RegistroAsistencia.objects.filter(fecha=date.today()).select_related('pasante').order_by('-hora')
        pendientes = RegistroAsistencia.objects.filter(estado='PENDIENTE').select_related('pasante').order_by('-fecha', '-hora')
    else:
        pasantes = Pasante.objects.filter(supervisores=supervisor_actual).order_by('nombre_completo')
        asistencias = RegistroAsistencia.objects.filter(pasante__in=pasantes, fecha=date.today()).select_related('pasante').order_by('-hora')
        pendientes = RegistroAsistencia.objects.filter(estado='PENDIENTE', pasante__supervisores=supervisor_actual).select_related('pasante').order_by('-fecha', '-hora').distinct()

    horas_hoy = 0.0
    alertas_tardanza = 0
    marcas_por_pasante = {}
    
    dias_semana_codigo = {0: 'LU', 1: 'MA', 2: 'MI', 3: 'JU', 4: 'VI', 5: 'SA', 6: 'DO'}
    codigo_hoy = dias_semana_codigo[date.today().weekday()]
    turnos_hoy = TurnoPasante.objects.filter(pasante__in=pasantes, dia=codigo_hoy)
    dict_turnos = {t.pasante_id: t for t in turnos_hoy}

    for m in asistencias:
        if m.pasante_id not in marcas_por_pasante:
            marcas_por_pasante[m.pasante_id] = []
        marcas_por_pasante[m.pasante_id].append(m)
        
        if m.tipo == 'ENTRADA':
            turno_oficial = dict_turnos.get(m.pasante_id)
            if turno_oficial:
                dt_entrada_oficial = datetime.combine(date.today(), turno_oficial.hora_entrada)
                limite_tolerancia = (dt_entrada_oficial + timedelta(minutes=15)).time()
                if m.hora > limite_tolerancia:
                    alertas_tardanza += 1

    # --- CORRECCIÓN 1: SE INICIALIZA LA LISTA DEL RADAR ---
    radar_presentes = []
    en_oficina_count = 0
    presentes_hoy_count = len(marcas_por_pasante) 
    
    for pid, marcas in marcas_por_pasante.items():
        marcas_asc = sorted(marcas, key=lambda x: x.hora)
        ultima_marca = marcas_asc[-1]
        pasante_obj = ultima_marca.pasante
        
        if ultima_marca.tipo == 'ENTRADA':
            estado_actual = "Activo en Oficina"
            color_bg = "bg-emerald-100 text-emerald-700 border border-emerald-200"
            en_oficina_count += 1
        else:
            estado_actual = "Jornada Finalizada"
            color_bg = "bg-slate-100 text-slate-500 border border-slate-200"
            
        radar_presentes.append({
            'nombre': pasante_obj.nombre_completo,
            'area': pasante_obj.area or "Sin Área",
            'estado': estado_actual,
            'color': color_bg
        })
        
    radar_presentes.sort(key=lambda x: x['nombre'])

    pasantes_ausentes = []
    for p in pasantes:
        if not p.nota_final and p.id not in marcas_por_pasante:
            pasantes_ausentes.append(p)
            
    pasantes_ausentes.sort(key=lambda x: x.nombre_completo)

    distribucion_areas = {}
    ranking_pasantes = []
    total_activos_reales = 0

    for p in pasantes:
        if not p.nota_final:
            total_activos_reales += 1
            area_nombre = p.area or 'Sin Área Especificada'
            distribucion_areas[area_nombre] = distribucion_areas.get(area_nombre, 0) + 1
            
            h_hechas = calcular_horas_pasante(p)
            h_req = float(p.horas_requeridas)
            pct = min(100, int((h_hechas / h_req) * 100)) if h_req > 0 else 0
            ranking_pasantes.append({
                'nombre': p.nombre_completo,
                'area': area_nombre,
                'porcentaje': pct,
                'hechas': h_hechas,
                'req': h_req
            })

    ranking_pasantes.sort(key=lambda x: x['porcentaje'], reverse=True)
    top_5_pasantes = ranking_pasantes[:5]

    nombres_areas_json = json.dumps(list(distribucion_areas.keys()))
    cantidades_areas_json = json.dumps(list(distribucion_areas.values()))

    context = {
        'pasantes': pasantes, 
        'radar_presentes': radar_presentes,
        'asistencias_pendientes': pendientes,
        'mi_unidad': "Toda la Empresa" if puede_asignar else mi_unidad,
        'alertas_tardanza': alertas_tardanza,
        'presentes_hoy_count': presentes_hoy_count,
        'en_oficina_count': en_oficina_count, 
        'ausentes_hoy_count': len(pasantes_ausentes), 
        'pasantes_ausentes': pasantes_ausentes,       
        'total_activos': total_activos_reales,        
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual),
        'puede_asignar': puede_asignar,
        'top_5_pasantes': top_5_pasantes,
        'nombres_areas_json': nombres_areas_json,
        'cantidades_areas_json': cantidades_areas_json
    }
    return render(request, 'panel_del_supervisor_marca_actualizada/code.html', context)

@login_required
def listado_detallado(request):
    if not tiene_acceso_al_sistema(request.user):
        return render(request, 'espera_aprobacion.html')

    supervisor_actual = request.user
    puede_asignar = es_admin_rrhh(supervisor_actual)
    perfil = getattr(supervisor_actual, 'perfil', None)
    mi_unidad = perfil.unidad if perfil else "Sin Área"
    
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
        lista_con_calculos.append({'objeto': p, 'horas_hechas': horas_totales_p})

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
    if not tiene_acceso_al_sistema(request.user):
        return render(request, 'espera_aprobacion.html')

    supervisor_actual = request.user
    puede_asignar = es_admin_rrhh(supervisor_actual)
    perfil = getattr(supervisor_actual, 'perfil', None)
    mi_unidad = perfil.unidad if perfil else "Sin Área"
    
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

@login_required
def lista_pasantes(request):
    if not tiene_acceso_al_sistema(request.user):
        return render(request, 'espera_aprobacion.html')

    supervisor_actual = request.user
    puede_asignar = es_admin_rrhh(supervisor_actual)
    perfil = getattr(supervisor_actual, 'perfil', None)
    mi_unidad = perfil.unidad if perfil else "Sin Área"

    todos_los_usuarios = []
    areas_disponibles = []
    mapa_supervisores = {}

    if puede_asignar:
        todos_los_usuarios = User.objects.filter(is_active=True).select_related('perfil').order_by('username')
        areas_objs = AreaEmpresa.objects.all().order_by('nombre')
        
        if areas_objs.exists():
            areas_disponibles = [a.nombre for a in areas_objs]
            for a in areas_objs:
                if a.responsable:
                    mapa_supervisores[a.nombre] = [r.strip() for r in a.responsable.split(',')]
                else:
                    mapa_supervisores[a.nombre] = []
        else:
            areas_brutas = [u.perfil.unidad for u in todos_los_usuarios if hasattr(u, 'perfil') and u.perfil.unidad]
            areas_disponibles = sorted(list(set(areas_brutas)))

    if request.method == 'POST' and 'btn_guardar_nota' in request.POST:
        pasante_id = request.POST.get('pasante_id_modal')
        nota_final = request.POST.get('nota_final')
        if pasante_id and nota_final:
            try:
                p_obj = Pasante.objects.get(id=pasante_id)
                p_obj.nota_final = int(nota_final)
                p_obj.save()
                messages.success(request, f"¡Calificación de {p_obj.nombre_completo} guardada exitosamente y archivada!")
            except Pasante.DoesNotExist:
                messages.error(request, "Error: No se encontró al pasante.")
        return redirect('lista_pasantes')

    if request.method == 'POST' and 'btn_guardar_nota' not in request.POST:
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
    hoy = date.today()
    for p in pasantes_queryset:
        horas_hechas_redond = calcular_horas_pasante(p)
        horas_req_float = float(p.horas_requeridas)
        horas_restantes = max(0.0, round(horas_req_float - horas_hechas_redond, 1))
        porcentaje = 0
        if horas_req_float > 0:
            porcentaje = min(100, int((horas_hechas_redond / horas_req_float) * 100))
        
        dias_restantes = (p.fecha_fin - hoy).days
        alerta_conclusion = horas_restantes <= 20 
        marca_pendiente = RegistroAsistencia.objects.filter(pasante=p, estado='PENDIENTE').order_by('-fecha', '-hora').first()

        lista_con_calculos.append({
            'objeto': p, 
            'horas_hechas': horas_hechas_redond,
            'horas_restantes': horas_restantes, 
            'porcentaje': porcentaje,
            'dias_restantes': dias_restantes,
            'alerta_conclusion': alerta_conclusion,
            'marca_pendiente': marca_pendiente
        })
        
    mapa_supervisores_json = json.dumps(mapa_supervisores)

    context = {
        'pasantes_calculados': lista_con_calculos, 
        'mi_unidad': "Toda la Empresa" if puede_asignar else mi_unidad,
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual),
        'puede_asignar': puede_asignar,
        'todos_los_usuarios': todos_los_usuarios,
        'areas_disponibles': areas_disponibles,
        'mapa_supervisores_json': mapa_supervisores_json 
    }
    return render(request, 'lista_pasantes_marca_actualizada/code.html', context)

@login_required
def gestionar_turnos(request):
    if not tiene_acceso_al_sistema(request.user):
        return render(request, 'espera_aprobacion.html')

    supervisor_actual = request.user
    puede_asignar = es_admin_rrhh(supervisor_actual)
    perfil = getattr(supervisor_actual, 'perfil', None)
    mi_unidad = perfil.unidad if perfil else "Sin Área"
    
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

def portal_pasante(request):
    context = {}
    if request.method == 'POST':
        ci_digitado = request.POST.get('ci', '').strip()
        if ci_digitado:
            try:
                pasante = Pasante.objects.get(ci=ci_digitado)
                
                horas_hechas = calcular_horas_pasante(pasante)
                horas_req = float(pasante.horas_requeridas)
                horas_restantes = max(0.0, round(horas_req - horas_hechas, 1))
                porcentaje = min(100, int((horas_hechas / horas_req) * 100)) if horas_req > 0 else 0
                
                hoy = date.today()
                dias_restantes = (pasante.fecha_fin - hoy).days
                
                # --- CORRECCIÓN 2: CÁLCULO POSITIVO DE DÍAS VENCIDOS DESDE PYTHON ---
                dias_vencidos = abs(dias_restantes) if dias_restantes < 0 else 0
                
                turnos = TurnoPasante.objects.filter(pasante=pasante)
                dict_turnos = {t.dia: t for t in turnos}
                dias_semana_codigo = {0: 'LU', 1: 'MA', 2: 'MI', 3: 'JU', 4: 'VI', 5: 'SA', 6: 'DO'}
                
                marcas_entrada = RegistroAsistencia.objects.filter(pasante=pasante, tipo='ENTRADA')
                total_tardanzas = 0
                for m in marcas_entrada:
                    cod_dia = dias_semana_codigo[m.fecha.weekday()]
                    turno = dict_turnos.get(cod_dia)
                    if turno:
                        dt_oficial = datetime.combine(date.today(), turno.hora_entrada)
                        limite = (dt_oficial + timedelta(minutes=15)).time()
                        if m.hora > limite:
                            total_tardanzas += 1
                            
                if pasante.nota_final:
                    semaforo_color = "bg-emerald-500 shadow-[0_0_12px_#10b981]"
                    semaforo_texto = "Pasantía Finalizada y Archivada Oficialmente"
                elif dias_restantes < 0:
                    semaforo_color = "bg-red-500 shadow-[0_0_12px_#ef4444] animate-pulse"
                    semaforo_texto = "Alerta: Período de Contrato Vencido"
                elif horas_restantes <= 20:
                    semaforo_color = "bg-amber-500 shadow-[0_0_12px_#f59e0b] animate-pulse"
                    semaforo_texto = "Etapa Crítica Final (¡Preparar Informe de Conclusión!)"
                else:
                    semaforo_color = "bg-emerald-400 shadow-[0_0_12px_#34d399]"
                    semaforo_texto = "Curso Regular Activo"
                    
                context = {
                    'pasante': pasante,
                    'horas_hechas': horas_hechas,
                    'horas_restantes': horas_restantes,
                    'porcentaje': porcentaje,
                    'dias_restantes': dias_restantes,
                    'dias_vencidos': dias_vencidos, # Enviamos la variable ya calculada y positiva
                    'total_tardanzas': total_tardanzas,
                    'semaforo_color': semaforo_color,
                    'semaforo_texto': semaforo_texto,
                }
            except Pasante.DoesNotExist:
                context = {'error_msg': "El Carnet de Identidad digitado no está registrado."}
        else:
            context = {'error_msg': "Por favor, introduzca su documento de identidad."}
            
    return render(request, 'portal_pasante/code.html', context)

def cerrar_sesion(request):
    logout(request)
    return redirect('login')