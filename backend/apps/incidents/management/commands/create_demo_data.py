"""
Genera datos de demostración para el prototipo SGIS-UCV.
Crea 45 incidentes ficticios con historial de estados y comentarios.

Uso:
    python manage.py create_demo_data
    python manage.py create_demo_data --clear   # borra datos previos primero
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, date
import random

from apps.incidents.models import Incident, IncidentStatusHistory, IncidentComment
from apps.action_plans.models import ActionPlan
from apps.action_plans.plan_templates import get_steps_for_incident

User = get_user_model()


# ── Datos ficticios ────────────────────────────────────────────────────────────

AREAS = [
    'Laboratorio 1', 'Laboratorio 2', 'Laboratorio 3', 'Laboratorio 4',
    'Sala de Servidores', 'Red Administrativa', 'Biblioteca Digital',
    'Oficinas Administrativas', 'Sala de Profesores', 'Red Inalámbrica Campus',
    'Centro de Datos', 'Aulas Virtuales', 'Soporte Técnico',
]

SISTEMAS = [
    'PC-LAB-01', 'PC-LAB-07', 'PC-LAB-14', 'PC-ADM-03',
    'SRV-FILE-01', 'SRV-DB-02', 'SRV-WEB-01', 'SRV-MAIL-01',
    'SW-CORE-01', 'FW-PERIMETER-01', 'AP-CAMPUS-03',
    'Estación de trabajo', 'Servidor de base de datos',
    'Router de borde', 'NAS-BACKUP-01', 'VM-DOCENTE-05',
]

# (tipo, criticidad, título, descripción, área, sistema)
INCIDENTS_DATA = [
    # ── MALWARE ──────────────────────────────────────────────────────────────
    ('malware', 'critico',
     'Ransomware cifra 14 equipos del Laboratorio 3',
     'Se detectó actividad de ransomware en el Laboratorio 3 a las 08:42. '
     'El malware cifró archivos en 14 estaciones de trabajo y dejó nota de rescate '
     'en formato TXT. Vector de entrada identificado como unidad USB infectada. '
     'Los equipos afectados fueron aislados de la red de manera inmediata.',
     'Laboratorio 3', 'PC-LAB-14'),

    ('malware', 'alto',
     'Troyano RAT detectado en equipo administrativo',
     'El sistema antivirus corporativo alertó sobre la presencia del troyano '
     'AsyncRAT en PC-ADM-03, equipo perteneciente al área de Registros Académicos. '
     'El malware llevaba activo aproximadamente 6 días según los logs del endpoint. '
     'Se detectó comunicación saliente a servidor de C2 en IP extranjera.',
     'Oficinas Administrativas', 'PC-ADM-03'),

    ('malware', 'alto',
     'Minero de criptomonedas en servidor de virtualización',
     'Monitoreo de recursos del servidor de virtualización detectó uso anómalo '
     'de CPU al 97% durante la madrugada. Análisis posterior reveló la presencia '
     'de un cryptominer (XMRig) instalado mediante vulnerabilidad de SSH expuesta. '
     'El proceso se ejecutaba con privilegios root.',
     'Sala de Servidores', 'SRV-FILE-01'),

    ('malware', 'medio',
     'Adware instalado en 6 PCs del Laboratorio 1',
     'Usuarios del Laboratorio 1 reportaron apertura de ventanas emergentes y '
     'redirecciones del navegador hacia sitios de publicidad. Análisis confirma '
     'presencia de adware Conduit en 6 estaciones. Origen probable: descarga '
     'de software educativo desde fuente no oficial.',
     'Laboratorio 1', 'PC-LAB-01'),

    ('malware', 'medio',
     'Worm propagándose por red del Laboratorio 2',
     'Se detectó propagación de gusano informático a través de recursos compartidos '
     'de Windows en la subred del Laboratorio 2. El malware (variante Conficker) '
     'intenta explotar la vulnerabilidad MS08-067 en equipos sin parches.',
     'Laboratorio 2', 'PC-LAB-07'),

    ('malware', 'bajo',
     'PUA detectado en estación de soporte técnico',
     'El escáner de endpoint detectó una Aplicación Potencialmente No Deseada '
     '(PUA) en la estación de trabajo del técnico de soporte. Se trata de una '
     'herramienta de administración remota de uso dual (TeamViewer modificado).',
     'Soporte Técnico', 'Estación de trabajo'),

    ('malware', 'critico',
     'Backdoor en servidor de correo institucional',
     'Análisis forense detectó backdoor PHP (WebShell) en el servidor de correo '
     'institucional. El atacante mantuvo acceso persistente durante 18 días. '
     'Se exfiltraron aproximadamente 2,300 correos de cuentas docentes. '
     'El servidor fue puesto offline de forma inmediata.',
     'Sala de Servidores', 'SRV-MAIL-01'),

    ('malware', 'alto',
     'Keylogger en cabina de acceso público',
     'Un estudiante reportó comportamiento anómalo en una PC de la biblioteca. '
     'Análisis detectó keylogger de hardware instalado físicamente entre el teclado '
     'y la PC. El dispositivo capturaba credenciales de todos los usuarios.',
     'Biblioteca Digital', 'PC-LAB-01'),

    # ── ACCESO NO AUTORIZADO ─────────────────────────────────────────────────
    ('acceso_no_autorizado', 'critico',
     'Acceso remoto no autorizado a servidor de base de datos académicos',
     'El sistema IDS detectó conexión SSH exitosa al servidor de base de datos '
     'desde una IP de Argentina (181.45.23.112) a las 03:17. El atacante utilizó '
     'credenciales de un ex-empleado no revocadas. Se accedió a tablas con datos '
     'académicos de 48,000 estudiantes.',
     'Centro de Datos', 'SRV-DB-02'),

    ('acceso_no_autorizado', 'alto',
     'Cuenta de administrador accedida desde múltiples países',
     'El sistema de autenticación alertó sobre inicios de sesión simultáneos '
     'en la cuenta del Administrador TI desde Perú, Brasil y Estados Unidos. '
     'La contraseña fue comprometida, posiblemente mediante phishing previo.',
     'Red Administrativa', 'SRV-WEB-01'),

    ('acceso_no_autorizado', 'alto',
     'Escalada de privilegios en sistema de notas',
     'Un usuario con rol de estudiante logró acceder al panel de administración '
     'del sistema de registro académico explotando una vulnerabilidad IDOR '
     '(Insecure Direct Object Reference). Pudo visualizar notas de otros estudiantes.',
     'Aulas Virtuales', 'SRV-WEB-01'),

    ('acceso_no_autorizado', 'medio',
     'Intento de fuerza bruta contra portal de docentes',
     'El WAF registró 4,200 intentos de autenticación fallidos contra el portal '
     'de docentes en un período de 2 horas. La IP de origen (45.33.56.22) '
     'fue bloqueada automáticamente. No se logró acceso exitoso.',
     'Red Administrativa', 'SRV-WEB-01'),

    ('acceso_no_autorizado', 'medio',
     'Acceso a sala de servidores sin autorización',
     'El sistema de control de acceso físico registró entrada a la sala de '
     'servidores con tarjeta de empleado desvinculado. La tarjeta debió ser '
     'desactivada al momento del cese. El intruso estuvo dentro durante 8 minutos.',
     'Sala de Servidores', 'SRV-FILE-01'),

    ('acceso_no_autorizado', 'alto',
     'Credenciales de docente usadas para descarga masiva de recursos',
     'Se detectó descarga inusual de 48GB desde la cuenta de un docente en '
     'horario nocturno (02:00-04:30). El docente confirmó no haber realizado '
     'la actividad. Sesión iniciada desde IP de VPN comercial.',
     'Biblioteca Digital', 'SRV-FILE-01'),

    ('acceso_no_autorizado', 'bajo',
     'Estudiante accede a área restringida del servidor FTP',
     'Un estudiante descubrió que el directorio /backup del servidor FTP no '
     'tenía restricción de acceso y pudo listar archivos de configuración. '
     'El estudiante lo reportó voluntariamente al equipo de TI.',
     'Laboratorio 4', 'SRV-FILE-01'),

    ('acceso_no_autorizado', 'critico',
     'Compromiso de cuenta privilegiada del sistema ERP',
     'Auditoría de accesos detectó que la cuenta de servicio del ERP fue '
     'utilizada para crear 3 usuarios con privilegios de administrador. '
     'Las cuentas fueron creadas fuera del horario laboral. Posible insider threat.',
     'Oficinas Administrativas', 'SRV-DB-02'),

    # ── PHISHING ──────────────────────────────────────────────────────────────
    ('phishing', 'alto',
     'Campaña de phishing masiva suplantando identidad de TI',
     'Se recibieron 340 reportes de correos que suplantan al área de TI solicitando '
     '"actualización urgente de contraseña institucional". El enlace dirige a un '
     'sitio falso (ucv-soporte.net) que replica el portal de autenticación. '
     'Al menos 23 usuarios entregaron credenciales.',
     'Red Administrativa', 'SRV-MAIL-01'),

    ('phishing', 'alto',
     'Spear phishing dirigido a autoridades académicas',
     'El Decano y 4 directores de carrera recibieron correo personalizado '
     'suplantando al Rector, solicitando transferencia bancaria urgente por '
     '"convenio internacional". El correo incluía datos reales de la institución '
     'obtenidos de fuentes públicas.',
     'Oficinas Administrativas', 'SRV-MAIL-01'),

    ('phishing', 'medio',
     'Enlace de phishing distribuido por WhatsApp entre estudiantes',
     'Un enlace malicioso que promete "Wi-Fi gratuito ilimitado en el campus" '
     'se distribuyó por grupos de WhatsApp de estudiantes. El sitio solicita '
     'credenciales institucionales. Aproximadamente 180 personas accedieron al enlace.',
     'Red Inalámbrica Campus', 'AP-CAMPUS-03'),

    ('phishing', 'medio',
     'Correo de phishing con adjunto malicioso a docentes',
     'Docentes del área de Ingeniería recibieron correo con asunto '
     '"Resultados de evaluación curricular 2026" con adjunto Word malicioso. '
     'El documento contiene macros que descargan malware al ejecutarse.',
     'Sala de Profesores', 'SRV-MAIL-01'),

    ('phishing', 'bajo',
     'Estudiante reporta sitio web fraudulento de matrícula',
     'Un estudiante reportó haber encontrado un sitio web que replica el portal '
     'de matrícula de la UCV (ucv-matricula2026.com) solicitando datos de pago. '
     'No hay evidencia de víctimas hasta el momento del reporte.',
     'Aulas Virtuales', 'SRV-WEB-01'),

    ('phishing', 'alto',
     'Phishing de credenciales de correo con 45 cuentas comprometidas',
     'Campaña de phishing activa durante 3 días comprometió 45 cuentas '
     'institucionales (@ucv.edu.pe). Los atacantes usaron las cuentas para enviar '
     'spam y continuar propagando el phishing internamente.',
     'Red Administrativa', 'SRV-MAIL-01'),

    ('phishing', 'medio',
     'QR code malicioso pegado en computadoras del laboratorio',
     'Se encontraron stickers con códigos QR pegados en 12 computadoras del '
     'Laboratorio 4. El código dirige a un sitio que solicita credenciales '
     'institucionales bajo el pretexto de "registrar el equipo".',
     'Laboratorio 4', 'PC-LAB-14'),

    # ── FUGA DE DATOS ─────────────────────────────────────────────────────────
    ('fuga_datos', 'critico',
     'Exposición de base de datos con información de 48,000 estudiantes',
     'Un repositorio GitHub público creado por un desarrollador interno contenía '
     'un archivo SQL con datos completos de estudiantes: DNI, correo, teléfono, '
     'notas y datos de pago de pensiones. El repositorio estuvo público 11 días.',
     'Centro de Datos', 'SRV-DB-02'),

    ('fuga_datos', 'alto',
     'Unidad USB con datos de nómina encontrada en estacionamiento',
     'Un trabajador externo encontró una USB sin etiqueta en el estacionamiento '
     'y la entregó a seguridad. La unidad contiene archivos Excel con datos de '
     'nómina de 890 empleados, incluyendo sueldos y números de cuenta bancaria.',
     'Oficinas Administrativas', 'Estación de trabajo'),

    ('fuga_datos', 'alto',
     'Carpeta compartida con historial médico de personal expuesta en red',
     'Se detectó una carpeta de red compartida sin contraseña que contenía '
     'historiales médicos del personal administrativo. La carpeta era accesible '
     'desde cualquier equipo conectado a la red interna del campus.',
     'Red Administrativa', 'SRV-FILE-01'),

    ('fuga_datos', 'medio',
     'Correo enviado con lista de calificaciones a destinatario equivocado',
     'Un docente envió por error el archivo Excel con las calificaciones finales '
     'de 120 estudiantes (incluyendo DNI) al correo de un proveedor externo en '
     'lugar del coordinador académico. El proveedor confirmó recepción.',
     'Sala de Profesores', 'SRV-MAIL-01'),

    ('fuga_datos', 'medio',
     'Impresora con caché de documentos sensibles accesible en red',
     'La impresora multifuncional del área administrativa tenía habilitado '
     'el servidor web interno sin contraseña. El caché de trabajos de impresión '
     'contenía 34 documentos con información sensible descargables remotamente.',
     'Oficinas Administrativas', 'Estación de trabajo'),

    ('fuga_datos', 'alto',
     'Proveedor reporta recepción de datos de estudiantes sin cifrar vía email',
     'El proveedor de software académico notificó que recibió un correo de un '
     'empleado de TI con datos de prueba que correspondían a información real de '
     '3,200 estudiantes. Los datos no estaban cifrados ni anonimizados.',
     'Red Administrativa', 'SRV-MAIL-01'),

    ('fuga_datos', 'bajo',
     'Pizarra fotográfica con datos de alumnos publicada en redes sociales',
     'Un docente publicó en su cuenta personal de Facebook una fotografía de '
     'pizarra que incluía accidentalmente nombres y calificaciones de 28 '
     'estudiantes identificables. La publicación fue eliminada tras el reporte.',
     'Sala de Profesores', 'Estación de trabajo'),

    # ── FALLO DE CONFIGURACIÓN ────────────────────────────────────────────────
    ('fallo_configuracion', 'critico',
     'Servidor de base de datos expuesto directamente a internet sin firewall',
     'Auditoría de seguridad perimetral detectó que el puerto 5432 (PostgreSQL) '
     'del servidor de base de datos principal está accesible directamente desde '
     'internet. La regla de firewall fue eliminada accidentalmente durante '
     'un mantenimiento. El servicio estuvo expuesto por 72 horas.',
     'Centro de Datos', 'SRV-DB-02'),

    ('fallo_configuracion', 'alto',
     'Switch de core sin VLAN segmentando redes administrativa y estudiantil',
     'Revisión de configuración de red detectó que el switch de core no tiene '
     'configuradas las VLANs correctamente. Los estudiantes pueden hacer ping '
     'y acceder a servicios de la red administrativa desde sus equipos.',
     'Sala de Servidores', 'SW-CORE-01'),

    ('fallo_configuracion', 'alto',
     'Certificado SSL del portal institucional expirado',
     'El certificado SSL del portal web principal (ucv.edu.pe) venció sin ser '
     'renovado. Los navegadores muestran advertencia de "conexión no segura". '
     'Los datos de login de usuarios viajan sin cifrado TLS.',
     'Red Administrativa', 'SRV-WEB-01'),

    ('fallo_configuracion', 'medio',
     'Servidor FTP con acceso anónimo habilitado inadvertidamente',
     'Durante la configuración de un nuevo servidor de archivos, el técnico '
     'habilitó el acceso FTP anónimo para pruebas y olvidó desactivarlo. '
     'El directorio raíz del FTP era accesible sin autenticación durante 5 días.',
     'Sala de Servidores', 'SRV-FILE-01'),

    ('fallo_configuracion', 'medio',
     'Política de contraseñas deshabilitada en Active Directory',
     'Se detectó que la política de complejidad de contraseñas del Active '
     'Directory fue deshabilitada por error. Durante 2 semanas los usuarios '
     'pudieron establecer contraseñas simples como "123456".',
     'Red Administrativa', 'SRV-DB-02'),

    ('fallo_configuracion', 'medio',
     'Punto de acceso Wi-Fi con WEP en laboratorio de redes',
     'El laboratorio de redes (Lab-04) tiene un access point configurado con '
     'cifrado WEP, vulnerable a ataques en menos de 5 minutos. El equipo '
     'fue configurado originalmente para práctica y nunca fue asegurado.',
     'Laboratorio 4', 'AP-CAMPUS-03'),

    ('fallo_configuracion', 'bajo',
     'Logs del servidor web deshabilitados accidentalmente',
     'Durante actualización de Apache, la configuración de logging fue '
     'sobrescrita. Los logs de acceso y error estuvieron deshabilitados '
     'por 4 días, perdiendo trazabilidad de accesos al portal institucional.',
     'Sala de Servidores', 'SRV-WEB-01'),

    ('fallo_configuracion', 'alto',
     'Backup automático deshabilitado: 3 semanas sin respaldo',
     'El sistema de respaldo automatizado falló silenciosamente hace 21 días '
     'por un error de configuración en el scheduler. No se ha generado ningún '
     'backup de la base de datos académica ni de los archivos del servidor.',
     'Centro de Datos', 'NAS-BACKUP-01'),

    ('fallo_configuracion', 'bajo',
     'SNMP con community string "public" en equipos de red',
     'Escaneo de red detectó que varios switches y routers del campus tienen '
     'SNMP v1 habilitado con la community string "public" por defecto. '
     'Esto permite la enumeración completa de la topología de red.',
     'Red Inalámbrica Campus', 'SW-CORE-01'),

    # ── OTRO ──────────────────────────────────────────────────────────────────
    ('otro', 'medio',
     'Denegación de servicio interna durante exámenes finales',
     'Durante el período de exámenes finales, el portal de exámenes en línea '
     'sufrió caída total por 45 minutos. Análisis preliminar indica sobrecarga '
     'de conexiones simultáneas, posiblemente intencional. 1,200 estudiantes '
     'no pudieron completar su examen a tiempo.',
     'Aulas Virtuales', 'SRV-WEB-01'),

    ('otro', 'bajo',
     'Uso no autorizado de licencias de software en laboratorios',
     'Auditoría de software detectó instalaciones no autorizadas de Adobe '
     'Creative Suite en 18 equipos del Laboratorio 2. Las licencias institucionales '
     'no cubren este software. Riesgo legal por uso sin licencia.',
     'Laboratorio 2', 'PC-LAB-07'),

    ('otro', 'medio',
     'Dispositivo no autorizado conectado a red administrativa',
     'El sistema NAC (Network Access Control) detectó un dispositivo desconocido '
     '(Raspberry Pi) conectado al switch de la red administrativa. El dispositivo '
     'tenía servicios de escaneo de red activos.',
     'Red Administrativa', 'SW-CORE-01'),

    ('otro', 'alto',
     'Correo institucional usado para envío masivo de spam',
     'El servidor de correo fue incluido en listas negras de spam (Spamhaus). '
     'Investigación reveló que 3 cuentas comprometidas fueron usadas para enviar '
     '45,000 correos no deseados en 6 horas, afectando la reputación del dominio.',
     'Red Administrativa', 'SRV-MAIL-01'),

    ('otro', 'bajo',
     'Estudiante reporta vulnerabilidad XSS en portal de notas',
     'Un estudiante de la carrera de Ciberseguridad reportó de forma responsable '
     'una vulnerabilidad de Cross-Site Scripting (XSS) almacenado en el campo '
     'de comentarios del portal de notas. Demostró ejecución de JS arbitrario.',
     'Aulas Virtuales', 'SRV-WEB-01'),

    ('otro', 'medio',
     'Pérdida física de laptop con información de proyectos de investigación',
     'Un investigador reportó la pérdida de su laptop personal (usada para '
     'trabajo institucional) en un taxi. El equipo contenía datos de investigación '
     'sin cifrar y credenciales guardadas en el navegador.',
     'Oficinas Administrativas', 'Estación de trabajo'),
]

# Comentarios ficticios por categoría
COMMENTS_ANALISTA = [
    'Iniciando revisión de logs del sistema afectado. Se solicitó imagen forense al equipo.',
    'Confirmado el vector de entrada. Se procede con contención inmediata.',
    'El incidente fue contenido. Iniciando proceso de remediación.',
    'Se realizó análisis de malware en sandbox. Resultados adjuntos en ticket interno.',
    'Coordinando con el área afectada para restaurar operaciones normales.',
    'Revisión de logs completada. Se identificaron 3 sistemas adicionales afectados.',
    'Se aplicó el parche de seguridad correspondiente. Monitoreando por 24 horas.',
    'Usuarios afectados notificados según protocolo. Forzando cambio de contraseñas.',
    'Se restableció el servicio. Implementando monitoreo adicional preventivo.',
    'Herramientas de análisis forense desplegadas. Preservando evidencia digital.',
]

COMMENTS_ADMIN = [
    'Asignando caso a analista de turno. Prioridad alta.',
    'Se notificó al Jefe de Área sobre el incidente. Esperando aprobación para proceder.',
    'Recursos adicionales asignados. Coordinando respuesta con el proveedor.',
    'Validado el plan de acción propuesto por el analista. Autorizado para proceder.',
    'Incidente escalado a nivel crítico. Notificando a dirección académica.',
    'Se solicitó soporte externo del proveedor de ciberseguridad contratado.',
    'Reunión de seguimiento programada para mañana a las 09:00.',
    'Revisando impacto regulatorio. Evaluando si aplica notificación a autoridades.',
]

COMMENTS_JEFE = [
    'Informado. Pendiente de reporte ejecutivo al cierre del caso.',
    'Se comunicó la situación a las áreas afectadas. Coordinando contingencia.',
    'Revisado el impacto en las operaciones del área. El riesgo es aceptable por ahora.',
    'Solicitando reporte formal del incidente para la auditoría semestral.',
]

STATUS_TRANSITIONS = {
    'abierto':          [],
    'en_investigacion': ['abierto'],
    'resuelto':         ['abierto', 'en_investigacion'],
    'cerrado':          ['abierto', 'en_investigacion', 'resuelto'],
}

TRANSITION_COMMENTS = {
    ('', 'abierto'):             'Incidente registrado y clasificado en el sistema.',
    ('abierto', 'en_investigacion'): [
        'Se inicia investigación formal. Analista asignado al caso.',
        'Evidencia inicial recopilada. Ampliando análisis.',
        'Escalado a investigación activa tras confirmación del incidente.',
    ],
    ('en_investigacion', 'resuelto'): [
        'Causa raíz identificada y remedida. Sistema restaurado a operación normal.',
        'Plan de acción ejecutado en su totalidad. Verificada la eliminación de la amenaza.',
        'Remediación completada. No se detectan indicadores de compromiso residuales.',
    ],
    ('resuelto', 'cerrado'): [
        'Incidente cerrado tras 48 horas de monitoreo sin anomalías.',
        'Validación final completada. Lecciones aprendidas documentadas.',
        'Caso cerrado. Reporte final generado para auditoría.',
    ],
}


class Command(BaseCommand):
    help = 'Genera datos de demostración: 45 incidentes con historial y comentarios'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Eliminar incidentes existentes primero')

    def handle(self, *args, **options):
        if options['clear']:
            Incident.objects.all().delete()
            self.stdout.write(self.style.WARNING('Incidentes existentes eliminados.'))

        try:
            admin = User.objects.get(username='admin.ti')
            analista = User.objects.get(username='analista')
            jefe = User.objects.get(username='jefe.area')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                'Usuarios no encontrados. Ejecuta primero: python manage.py loaddata initial_data.json'
            ))
            return

        now = timezone.now()
        random.seed(42)

        # Distribución de estados para 45 incidentes
        # ~20% abierto, ~28% en_investigacion, ~30% resuelto, ~22% cerrado
        statuses = (
            ['abierto'] * 9 +
            ['en_investigacion'] * 13 +
            ['resuelto'] * 13 +
            ['cerrado'] * 10
        )
        random.shuffle(statuses)

        created = 0
        for i, (inc_type, criticality, title, description, area, sistema) in enumerate(INCIDENTS_DATA):
            final_status = statuses[i % len(statuses)]

            # Fecha de detección: entre 90 y 2 días atrás
            days_ago = random.randint(2, 90)
            detected_at = now - timedelta(days=days_ago, hours=random.randint(0, 23))

            # Asignado: admin o analista aleatoriamente (no para los muy nuevos)
            assigned = random.choice([admin, analista, None]) if days_ago > 3 else None

            # Deadline: algunos tienen, otros no
            deadline = None
            if random.random() > 0.4:
                deadline = (detected_at + timedelta(days=random.randint(3, 21))).date()

            incident = Incident.objects.create(
                title=title,
                description=description,
                incident_type=inc_type,
                criticality=criticality,
                status=final_status,
                affected_area=area,
                affected_system=sistema,
                detected_at=detected_at,
                deadline=deadline,
                created_by=random.choice([admin, analista]),
                assigned_to=assigned,
            )

            # ── Historial de estados ──────────────────────────────────────
            transitions = [('', 'abierto')] + [
                (a, b) for a, b in zip(
                    STATUS_TRANSITIONS[final_status],
                    STATUS_TRANSITIONS[final_status][1:] + [final_status]
                )
            ]
            # Construir la secuencia correcta
            all_states = ['abierto'] + STATUS_TRANSITIONS[final_status][1:] if STATUS_TRANSITIONS[final_status] else ['abierto']
            # Simplificar: secuencia desde abierto hasta final_status
            state_sequence = ['abierto', 'en_investigacion', 'resuelto', 'cerrado']
            idx = state_sequence.index(final_status)
            path = state_sequence[:idx + 1]

            history_date = detected_at + timedelta(minutes=random.randint(10, 120))
            prev = ''
            for j, st in enumerate(path):
                comments_pool = TRANSITION_COMMENTS.get((prev, st), ['Cambio de estado registrado.'])
                if isinstance(comments_pool, list):
                    comment = random.choice(comments_pool)
                else:
                    comment = comments_pool

                IncidentStatusHistory.objects.create(
                    incident=incident,
                    previous_status=prev,
                    new_status=st,
                    changed_by=random.choice([admin, analista]),
                    changed_at=history_date,
                    comment=comment,
                )
                prev = st
                history_date += timedelta(hours=random.randint(4, 48))

            # ── Plan de acción ────────────────────────────────────────────
            if not hasattr(incident, 'action_plan'):
                try:
                    ActionPlan.objects.create(
                        incident=incident,
                        steps=get_steps_for_incident(inc_type, criticality),
                    )
                except Exception:
                    pass

            # ── Comentarios ───────────────────────────────────────────────
            num_comments = random.randint(1, 4)
            comment_date = detected_at + timedelta(hours=random.randint(1, 6))

            for _ in range(num_comments):
                role_choice = random.random()
                if role_choice < 0.5:
                    author = analista
                    pool = COMMENTS_ANALISTA
                elif role_choice < 0.8:
                    author = admin
                    pool = COMMENTS_ADMIN
                else:
                    author = jefe
                    pool = COMMENTS_JEFE

                IncidentComment.objects.create(
                    incident=incident,
                    author=author,
                    content=random.choice(pool),
                    created_at=comment_date,
                )
                comment_date += timedelta(hours=random.randint(2, 24))

            created += 1

        self.stdout.write(self.style.SUCCESS(
            f'✓ {created} incidentes creados con historial y comentarios.'
        ))
        self.stdout.write('  Resumen por estado:')
        for st in ['abierto', 'en_investigacion', 'resuelto', 'cerrado']:
            count = Incident.objects.filter(status=st).count()
            self.stdout.write(f'    {st}: {count}')
        self.stdout.write('  Resumen por criticidad:')
        for cr in ['critico', 'alto', 'medio', 'bajo']:
            count = Incident.objects.filter(criticality=cr).count()
            self.stdout.write(f'    {cr}: {count}')
