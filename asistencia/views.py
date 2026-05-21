from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Pasante, RegistroAsistencia, TurnoPasante
from datetime import date, datetime

# 1. TERMINAL DE MARCACIÓN PÚBLICA (ACCESO LIBRE)
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

# 2. PANEL DE CONTROL (BENTO GRID CENTRAL)
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

    context = {'pasantes': pasantes, 'asistencias': asistencias, 'mi_unidad': mi_unidad}
    return render(request, 'panel_del_supervisor_marca_actualizada/code.html', context)

# 3. CONTROL ASISTENCIA (HISTORIAL TABULAR DETALLADO)
@login_required
def listado_detallado(request):
    supervisor_actual = request.user
    mi_unidad = supervisor_actual.perfil.unidad if hasattr(supervisor_actual, 'perfil') else "Sin Área"
    
    if supervisor_actual.is_superuser:
        asistencias = RegistroAsistencia.objects.all().select_related('pasante').order_by('-fecha', '-hora')
    else:
        pasantes = Pasante.objects.filter(Q(supervisor=supervisor_actual) | Q(area=mi_unidad))
        asistencias = RegistroAsistencia.objects.filter(pasante__in=pasantes).select_related('pasante').order_by('-fecha', '-hora')
        
    context = {'asistencias': asistencias, 'mi_unidad': mi_unidad}
    return render(request, 'listado_detallado_de_asistencia_marca_actualizada/code.html', context)

# 4. GENERACIÓN DE REPORTES (HOJA DE IMPRESIÓN CARTA)
@login_required
def generacion_reportes(request):
    supervisor_actual = request.user
    mi_unidad = supervisor_actual.perfil.unidad if hasattr(supervisor_actual, 'perfil') else "Sin Área"
    
    if supervisor_actual.is_superuser:
        pasantes = Pasante.objects.all().order_by('nombre_completo')
        asistencias = RegistroAsistencia.objects.all().select_related('pasante').order_by('-fecha')
    else:
        pasantes = Pasante.objects.filter(Q(supervisor=supervisor_actual) | Q(area=mi_unidad)).order_by('nombre_completo')
        asistencias = RegistroAsistencia.objects.filter(pasante__in=pasantes).select_related('pasante').order_by('-fecha')
        
    context = {'pasantes': pasantes, 'asistencias': asistencias, 'mi_unidad': mi_unidad}
    return render(request, 'generaci_n_de_reportes_marca_actualizada/code.html', context)

# 5. LISTA PASANTES (CONTRATOS Y BALANCES HORARIOS AUTOMÁTICOS)
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
            messages.success(request, f"¡Pasante {nombre} dado de alta con éxito!")
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
                    entrada = m.hora
                elif m.tipo == 'SALIDA' and entrada is not None:
                    dt_entrada = datetime.combine(date.today(), entrada)
                    dt_salida = datetime.combine(date.today(), m.hora)
                    horas_totales_hechas += (dt_salida - dt_entrada).total_seconds() / 3600.0
                    entrada = None

        horas_hechas_redond = round(horas_totales_hechas, 1)
        horas_restantes = max(0.0, round(float(p.horas_requeridas) - horas_hechas_redond, 1))
        
        lista_con_calculos.append({
            'objeto': p,
            'horas_hechas': horas_hechas_redond,
            'horas_restantes': horas_restantes,
        })
        
    context = {'pasantes_calculados': lista_con_calculos, 'mi_unidad': mi_unidad}
    return render(request, 'lista_pasantes_marca_actualizada/code.html', context)

# 6. GESTIONAR TURNOS (HORARIOS ROTATIVOS POR DÍA DE LA SEMANA)
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
        dia = request.POST.get('dia')
        entrada = request.POST.get('hora_entrada')
        salida = request.POST.get('hora_salida')
        obs = request.POST.get('observacion', '')
        
        if pasante_id and dia and entrada and salida:
            p_obj = get_object_or_404(Pasante, id=pasante_id)
            TurnoPasante.objects.update_or_create(
                pasante=p_obj, dia=dia,
                defaults={'hora_entrada': entrada, 'hora_salida': salida, 'observacion': obs}
            )
            messages.success(request, f"¡Turno guardado con éxito para {p_obj.nombre_completo}!")
            return redirect('gestionar_turnos')

    turnos = TurnoPasante.objects.filter(pasante__in=pasantes).select_related('pasante').order_by('pasante', 'dia')
    context = {'pasantes': pasantes, 'turnos': turnos, 'mi_unidad': mi_unidad, 'dias_opciones': TurnoPasante.DIAS_SEMANA}
    return render(request, 'gestionar_turnos_marca_actualizada/code.html', context)