"""
Plantillas de planes de acción por tipo y criticidad de incidente (RF6).
"""

_STEPS = {
    'malware': {
        'base': [
            'Aislar el equipo afectado de la red inmediatamente.',
            'Identificar el proceso o archivo malicioso en ejecución.',
            'Ejecutar análisis completo con antivirus actualizado.',
            'Preservar logs del sistema y copias forenses del equipo.',
            'Eliminar el malware y sus artefactos residuales.',
            'Restaurar el equipo desde backup limpio verificado.',
            'Documentar el vector de entrada y aplicar parche o control.',
        ],
        'critico': [
            'Notificar al Jefe de Área y Administrador TI de inmediato.',
            'Aislar el segmento de red completo si hay riesgo de propagación.',
            'Activar protocolo de respuesta a incidentes críticos.',
        ],
    },
    'acceso_no_autorizado': {
        'base': [
            'Deshabilitar la cuenta o sesión comprometida.',
            'Revocar tokens de acceso y forzar cierre de sesiones activas.',
            'Revisar logs de acceso para determinar alcance del incidente.',
            'Cambiar credenciales de todos los sistemas accedidos.',
            'Verificar si se exfiltraron datos sensibles.',
            'Aplicar MFA si no estaba habilitado.',
            'Reportar a las partes afectadas según política institucional.',
        ],
        'critico': [
            'Escalar a la dirección de TI y al área legal si corresponde.',
            'Preservar evidencia para posible investigación forense.',
        ],
    },
    'phishing': {
        'base': [
            'Bloquear el dominio o URL maliciosa en el proxy/firewall.',
            'Identificar y notificar a todos los usuarios que recibieron el correo.',
            'Deshabilitar cuentas que hayan entregado credenciales.',
            'Revisar actividad anómala en las cuentas afectadas.',
            'Reportar el sitio de phishing a los servicios anti-abuso.',
            'Enviar alerta de concientización a toda la comunidad universitaria.',
        ],
        'critico': [
            'Involucrar al equipo de comunicaciones para aviso institucional masivo.',
            'Coordinar con proveedor de correo para retiro del mensaje.',
        ],
    },
    'fuga_datos': {
        'base': [
            'Identificar la fuente y volumen de datos expuestos.',
            'Revocar accesos al recurso comprometido inmediatamente.',
            'Notificar a los titulares de los datos según normativa vigente.',
            'Evaluar si se requiere notificación a autoridades regulatorias.',
            'Aplicar cifrado y controles de acceso adicionales al recurso.',
            'Revisar configuraciones de permisos y ACLs.',
            'Documentar para auditoría y lecciones aprendidas.',
        ],
        'critico': [
            'Activar protocolo de respuesta a brecha de datos.',
            'Involucrar asesoría legal de la institución.',
        ],
    },
    'fallo_configuracion': {
        'base': [
            'Identificar el sistema o servicio mal configurado.',
            'Aplicar la configuración segura de referencia (hardening).',
            'Verificar que no se haya explotado la vulnerabilidad durante la ventana de exposición.',
            'Revisar configuraciones de sistemas similares en el entorno.',
            'Documentar el cambio y validar con checklist de seguridad.',
        ],
        'critico': [
            'Deshabilitar el servicio expuesto hasta aplicar el fix.',
            'Notificar a Administrador TI y Jefe de Área.',
        ],
    },
    'otro': {
        'base': [
            'Documentar en detalle los síntomas y sistemas afectados.',
            'Asignar responsable técnico para análisis inicial.',
            'Clasificar correctamente el incidente en base al análisis.',
            'Aplicar medidas de contención según el tipo identificado.',
            'Escalar si supera la capacidad de respuesta del equipo.',
        ],
        'critico': [],
    },
}


def get_steps_for_incident(incident_type: str, criticality: str) -> list[str]:
    template = _STEPS.get(incident_type, _STEPS['otro'])
    steps = list(template['base'])
    if criticality == 'critico':
        steps = template.get('critico', []) + steps
    return steps


def new_step(text: str) -> dict:
    """Un paso del checklist: texto + estado de avance + evidencia (V1.1)."""
    return {'text': text, 'done': False, 'done_by': None, 'done_at': None, 'evidence': ''}


def build_steps(incident_type: str, criticality: str) -> list[dict]:
    """Pasos del plan ya en forma de checklist (lista de dicts)."""
    return [new_step(s) for s in get_steps_for_incident(incident_type, criticality)]


def generate_action_plan(incident) -> None:
    from apps.action_plans.models import ActionPlan
    ActionPlan.objects.create(
        incident=incident,
        steps=build_steps(incident.incident_type, incident.criticality),
    )
