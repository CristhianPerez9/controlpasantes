from django.db import models
from django.contrib.auth.models import User

class Pasante(models.Model):
    ci = models.CharField(max_length=20, unique=True)
    nombre_completo = models.CharField(max_length=150)
    area = models.CharField(max_length=100)
    
    # Campo actualizado para soportar MÚLTIPLES supervisores
    supervisores = models.ManyToManyField(User, related_name='pasantes_a_cargo', blank=True)
    
    fecha_nacimiento = models.DateField(null=True, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    horas_requeridas = models.IntegerField(default=240)
    estado = models.BooleanField(default=True, null=True, blank=True)
    nota_final = models.IntegerField(null=True, blank=True, verbose_name="Nota Final")

    def __str__(self):
        return self.nombre_completo

class RegistroAsistencia(models.Model):
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SALIDA', 'Salida'),
    ]
    
    estado = models.CharField(max_length=20, default='APROBADO')
    pasante = models.ForeignKey(Pasante, on_delete=models.CASCADE, related_name='asistencias')
    fecha = models.DateField(auto_now_add=True)
    hora = models.TimeField(auto_now_add=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    def __str__(self):
        return f"{self.pasante.nombre_completo} - {self.tipo} ({self.fecha} {self.hora})"

class TurnoPasante(models.Model):
    DIAS_SEMANA = [
        ('LU', 'Lunes'),
        ('MA', 'Martes'),
        ('MI', 'Miércoles'),
        ('JU', 'Jueves'),
        ('VI', 'Viernes'),
        ('SA', 'Sábado'),
    ]
    TIPO_TURNO = [
        ('MAÑANA', 'Turno Mañana'),
        ('TARDE', 'Turno Tarde'),
    ]
    pasante = models.ForeignKey(Pasante, on_delete=models.CASCADE, related_name='turnos')
    dia = models.CharField(max_length=2, choices=DIAS_SEMANA)
    turno = models.CharField(max_length=10, choices=TIPO_TURNO, default='MAÑANA')
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField()
    observacion = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        unique_together = ('pasante', 'dia', 'turno')

    def __str__(self):
        return f"{self.pasante.nombre_completo} - {self.get_dia_display()} ({self.turno})"

class AreaEmpresa(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    responsable = models.CharField(max_length=255, blank=True, null=True, help_text="Nombre del responsable oficial según RRHH")

    def __str__(self):
        return self.nombre