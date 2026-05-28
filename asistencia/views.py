import os
import csv
import datetime  
from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.conf import settings
from .models import Pasante, RegistroAsistencia, TurnoPasante
from django.contrib.auth.models import User
from django.core.paginator import Paginator  

# --- FUNCIÓN AUXILIAR INTERNA (NO CREA ARCHIVOS) ---
def obtener_nombre_completo_ldap(user):
    """
    Toma el nombre y apellido mapeados por el LDAP de COMTECO.
    Si vienen vacíos, usa el username en mayúsculas como respaldo seguro.
    """
    nombre_completo = f"{user.first_name} {user.last_name}".strip()
    if not nombre_completo:
        nombre_completo = user.username.upper()
    return nombre_completo


# --- 1. CARGADOR AUXILIAR ---
@login_required
def importar_datos_csv(request):
    base_dir = settings.BASE_DIR
    archivos_en_raiz = os.listdir(base_dir)
    archivo_detectado = None

    for f in archivos_en_raiz:
        if f.lower() in ['datos.xls', 'datos.xlsx', 'datos.csv']:
            archivo_detectado = os.path.join(base_dir, f)
            break

    if not archivo_detectado:
        return HttpResponse(f"<h3>❌ Archivo No Encontrado en: {base_dir}</h3>")

    columnas_excel = {'Deysi': (1, 2), 'Yusara': (4, 5), 'Alison': (7, 8), 'Sheyling': (10, 11)}
    user_supervisor = request.user

    pasantes_db = {}
    for nombre in columnas_excel.keys():
        obj, creado = Pasante.objects.get_or_create(
            ci=f"CI-{nombre.upper()}",
            defaults={'nombre_completo': nombre, 'area': 'GERENCIA DE TECNOLOGIAS DE INFORMACION', 'supervisor': user_supervisor, 'horas_requeridas': 360}
        )
        if not creado:
            obj.supervisor = user_supervisor
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

        contador_marcas = 0
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
                        RegistroAsistencia.objects.get_or_create(pasante=pasante_actual, fecha=fecha_obj, hora=hora_in, tipo='ENTRADA')
                        contador_marcas += 1
                    if hora_out and hora_out not in ['00:00:00', '']:
                        RegistroAsistencia.objects.get_or_create(pasante=pasante_actual, fecha=fecha_obj, hora=hora_out, tipo='SALIDA')
                        contador_marcas += 1

        return HttpResponse(f"<h2>🎉 ¡Sincronización Exitosa! Se cargaron {contador_marcas} marcaciones.</h2><br><a href='/panel/'>Volver al Panel</a>")
    except Exception as e:
        return HttpResponse(f"<h3>❌ Error: {e}</h3>")


# --- 2. VISTAS DEL SISTEMA NORMALES ---
def registrar_asistencia(request):
    if request.method == 'POST':
        ci_digitado = request.POST.get('ci_value')
        tipo_marca = request.POST.get('tipo_marca')
        if not ci_digitado:
            messages.error(request, "Por favor, introduzca su Carnet de Identidad.")
            return redirect('registrar_asistencia')
        try:
            pasante = Pasante.objects.get(ci=ci_digitado)
            RegistroAsistencia.objects.create(pasante=pasante, tipo=tipo_marca)
            messages.success(request, f"¡Marca de {tipo_marca.lower()} registrada con éxito para {pasante.nombre_completo}!")
            return redirect('registrar_asistencia')
        except Pasante.DoesNotExist:
            messages.error(request, "Error: El Carnet de Identidad no está registrado.")
            return redirect('registrar_asistencia')
    return render(request, 'registro_de_asistencia_pasante_marca_actualizada/code.html')

@login_required
def index_dashboard(request):
    return redirect('panel_supervisor')

@login_required
def panel_supervisor(request):
    supervisor_actual = request.user
    mi_unidad = supervisor_actual.perfil.unidad if hasattr(supervisor_actual, 'perfil') else "Sin Área"
    
    if supervisor_actual.is_superuser:
        pasantes = Pasante.objects.all()
        asistencias = RegistroAsistencia.objects.filter(fecha=date.today()).select_related('pasante').order_by('-hora')
    else:
        pasantes = Pasante.objects.filter(Q(supervisor=supervisor_actual) | Q(area=mi_unidad))
        asistencias = RegistroAsistencia.objects.filter(pasante__in=pasantes, fecha=date.today()).select_related('pasante').order_by('-hora')

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
            elif m.tipo == 'SALIDA' and entrada is not None:
                salida_limpia = m.hora.replace(second=0, microsecond=0)
                dt_entrada = datetime.combine(date.today(), entrada)
                dt_salida = datetime.combine(date.today(), salida_limpia)
                horas_hoy += (dt_salida - dt_entrada).total_seconds() / 3600.0
                entrada = None

    context = {
        'pasantes': pasantes, 
        'asistencias': asistencias, 
        'mi_unidad': mi_unidad,
        'horas_hoy': round(horas_hoy, 1),
        'alertas_tardanza': alertas_tardanza,
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual)
    }
    return render(request, 'panel_del_supervisor_marca_actualizada/code.html', context)


@login_required
def listado_detallado(request):
    supervisor_actual = request.user
    mi_unidad = supervisor_actual.perfil.unidad if hasattr(supervisor_actual, 'perfil') else "Sin Área"
    
    if supervisor_actual.is_superuser:
        pasantes_queryset = Pasante.objects.all().order_by('nombre_completo')
        queryset_marcas = RegistroAsistencia.objects.all().select_related('pasante')
    else:
        pasantes_queryset = Pasante.objects.filter(Q(supervisor=supervisor_actual) | Q(area=mi_unidad)).order_by('nombre_completo')
        queryset_marcas = RegistroAsistencia.objects.filter(pasante__in=pasantes_queryset).select_related('pasante')

    lista_con_calculos = []
    horas_area = 0.0
    
    for p in pasantes_queryset:
        marcas_p = RegistroAsistencia.objects.filter(pasante=p).order_by('fecha', 'hora')
        horas_totales_p = 0.0
        marcas_por_dia_p = {}
        
        for m in marcas_p:
            if m.fecha not in marcas_por_dia_p:
                marcas_por_dia_p[m.fecha] = []
            marcas_por_dia_p[m.fecha].append(m)
            
        for fecha_dia, lista_marcas in marcas_por_dia_p.items():
            entrada = None
            for m in lista_marcas:
                if m.tipo == 'ENTRADA':
                    entrada = m.hora.replace(second=0, microsecond=0)
                elif m.tipo == 'SALIDA' and entrada is not None:
                    salida_limpia = m.hora.replace(second=0, microsecond=0)
                    dt_entrada = datetime.combine(date.today(), entrada)
                    dt_salida = datetime.combine(date.today(), salida_limpia)
                    tot_calc = (dt_salida - dt_entrada).total_seconds() / 3600.0
                    horas_totales_p += tot_calc
                    horas_area += tot_calc
                    entrada = None
                    
        lista_con_calculos.append({
            'objeto': p,
            'horas_hechas': round(horas_totales_p, 1)
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
            elif m.tipo == 'SALIDA':
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
        'mi_unidad': mi_unidad,
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual)
    }
    return render(request, 'listado_detallado_de_asistencia_marca_actualizada/code.html', context)


# --- 3. LOGICA DE REPORTES PERSONALIZADOS (CORREGIDA) ---
@login_required
def generacion_reportes(request):
    supervisor_actual = request.user
    mi_unidad = supervisor_actual.perfil.unidad if hasattr(supervisor_actual, 'perfil') else "Sin Área"
    
    if supervisor_actual.is_superuser:
        pasantes_lista = Pasante.objects.all().order_by('nombre_completo')
        queryset_marcas = RegistroAsistencia.objects.all().select_related('pasante')
    else:
        pasantes_lista = Pasante.objects.filter(Q(supervisor=supervisor_actual) | Q(area=mi_unidad)).order_by('nombre_completo')
        queryset_marcas = RegistroAsistencia.objects.filter(pasante__in=pasantes_lista).select_related('pasante')
        
    # CORRECCIÓN: Usar 'pasante_id' para que coincida con el nombre del <select> en HTML
    filtro_pasante = request.GET.get('pasante_id')
    fecha_desde = request.GET.get('fecha_desde', '')
    fecha_hasta = request.GET.get('fecha_hasta', '')
    
    pasante_seleccionado = None
    
    if filtro_pasante and filtro_pasante != 'todos':
        queryset_marcas = queryset_marcas.filter(pasante_id=filtro_pasante)
        pasante_seleccionado = pasantes_lista.filter(id=filtro_pasante).first()
        
    if fecha_desde:
        queryset_marcas = queryset_marcas.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        queryset_marcas = queryset_marcas.filter(fecha__lte=fecha_hasta)
        
    queryset_marcas = queryset_marcas.order_by('fecha', 'hora')
    
    marcas_agrupadas = {}
    for m in queryset_marcas:
        clave = (m.pasante, m.fecha)
        if clave not in marcas_agrupadas:
            marcas_agrupadas[clave] = {'entrada': None, 'salida': None}
            
        if m.tipo == 'ENTRADA' and not marcas_agrupadas[clave]['entrada']:
            marcas_agrupadas[clave]['entrada'] = m.hora.replace(second=0, microsecond=0)
        elif m.tipo == 'SALIDA':
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
            
        reporte_final.append({
            'pasante': pasante,
            'fecha': fecha,
            'entrada': datos['entrada'],
            'salida': datos['salida'],
            'horas_dia': round(horas_dia, 2)
        })

    reporte_final.sort(key=lambda x: x['fecha'], reverse=True)
        
    context = {
        'pasantes': pasantes_lista,
        'reportes_asistencia': reporte_final,
        'total_horas_periodo': round(total_horas_periodo, 1),
        'mi_unidad': mi_unidad,
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual),
        
        # CORRECCIÓN: Mandar variables al HTML para que no se borren los filtros al recargar
        'filtro_pasante': filtro_pasante,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'pasante_seleccionado': pasante_seleccionado
    }
    return render(request, 'generaci_n_de_reportes_marca_actualizada/code.html', context)


@login_required
def lista_pasantes(request):
    supervisor_actual = request.user
    mi_unidad = supervisor_actual.perfil.unidad if hasattr(supervisor_actual, 'perfil') else "Sin Área"
    
    if request.method == 'POST':
        ci = request.POST.get('ci')
        nombre = request.POST.get('nombre_completo')
        f_inicio = request.POST.get('fecha_inicio')
        f_fin = request.POST.get('fecha_fin')
        horas_req = request.POST.get('horas_requeridas', 240)
        
        if ci and nombre and f_inicio and f_fin:
            Pasante.objects.create(
                ci=ci, nombre_completo=nombre, area=mi_unidad,
                supervisor=supervisor_actual, fecha_inicio=f_inicio,
                fecha_fin=f_fin, horas_requeridas=horas_req
            )
            messages.success(request, f"¡Pasante {nombre} guardado exitosamente!")
            return redirect('lista_pasantes')

    if supervisor_actual.is_superuser:
        pasantes_queryset = Pasante.objects.all().order_by('nombre_completo')
    else:
        pasantes_queryset = Pasante.objects.filter(Q(supervisor=supervisor_actual) | Q(area=mi_unidad)).order_by('nombre_completo')
        
    lista_con_calculos = []
    for p in pasantes_queryset:
        marcas = RegistroAsistencia.objects.filter(pasante=p).order_by('fecha', 'hora')
        horas_totales_hechas = 0.0
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
                elif m.tipo == 'SALIDA' and entrada is not None:
                    salida_limpia = m.hora.replace(second=0, microsecond=0)
                    dt_entrada = datetime.combine(date.today(), entrada)
                    dt_salida = datetime.combine(date.today(), salida_limpia)
                    horas_totales_hechas += (dt_salida - dt_entrada).total_seconds() / 3600.0
                    entrada = None

        horas_hechas_redond = round(horas_totales_hechas, 1)
        horas_restantes = max(0.0, round(float(p.horas_requeridas) - horas_hechas_redond, 1))
        
        lista_con_calculos.append({
            'objeto': p,
            'horas_hechas': horas_hechas_redond,
            'horas_restantes': horas_restantes,
        })
        
    context = {
        'pasantes_calculados': lista_con_calculos, 
        'mi_unidad': mi_unidad,
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual)
    }
    return render(request, 'lista_pasantes_marca_actualizada/code.html', context)

@login_required
def gestionar_turnos(request):
    supervisor_actual = request.user
    mi_unidad = supervisor_actual.perfil.unidad if hasattr(supervisor_actual, 'perfil') else "Sin Área"
    
    if supervisor_actual.is_superuser:
        pasantes = Pasante.objects.all().order_by('nombre_completo')
    else:
        pasantes = Pasante.objects.filter(Q(supervisor=supervisor_actual) | Q(area=mi_unidad)).order_by('nombre_completo')
        
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
        'mi_unidad': mi_unidad,
        'supervisor_nombre_completo': obtener_nombre_completo_ldap(supervisor_actual)
    }
    return render(request, 'gestionar_turnos_marca_actualizada/code.html', context)