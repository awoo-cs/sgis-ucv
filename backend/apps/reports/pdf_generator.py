from io import BytesIO
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER


CRITICALITY_COLORS = {
    'bajo': colors.HexColor('#4CAF50'),
    'medio': colors.HexColor('#FF9800'),
    'alto': colors.HexColor('#F44336'),
    'critico': colors.HexColor('#9C27B0'),
}


def build_incident_report(incidents, filters_description: str = '') -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Encabezado
    title_style = ParagraphStyle('title', parent=styles['Title'], fontSize=16, spaceAfter=6)
    subtitle_style = ParagraphStyle('subtitle', parent=styles['Normal'], fontSize=10,
                                    textColor=colors.grey, spaceAfter=12)
    story.append(Paragraph('SGIS-UCV — Reporte de Incidentes de Seguridad', title_style))
    story.append(Paragraph('Universidad César Vallejo — Centro de Cómputo', subtitle_style))
    story.append(Paragraph(f'Generado el: {date.today().strftime("%d/%m/%Y")}', subtitle_style))
    if filters_description:
        story.append(Paragraph(f'Filtros aplicados: {filters_description}', subtitle_style))
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#1976D2')))
    story.append(Spacer(1, 0.5*cm))

    # Resumen
    story.append(Paragraph(f'Total de incidentes: <b>{len(incidents)}</b>', styles['Normal']))
    story.append(Spacer(1, 0.3*cm))

    # Tabla
    headers = ['#', 'Título', 'Tipo', 'Criticidad', 'Estado', 'Área', 'Fecha detección', 'Responsable']
    data = [headers]

    for i, inc in enumerate(incidents, 1):
        row = [
            str(i),
            Paragraph(inc.title[:50], styles['Normal']),
            inc.get_incident_type_display(),
            inc.get_criticality_display(),
            inc.get_status_display(),
            inc.affected_area[:30],
            inc.detected_at.strftime('%d/%m/%Y %H:%M'),
            inc.assigned_to.get_full_name() if inc.assigned_to else '—',
        ]
        data.append(row)

    col_widths = [0.8*cm, 4.5*cm, 2.8*cm, 2*cm, 2.5*cm, 2.5*cm, 3*cm, 2.5*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDBDBD')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ])

    # Colorear criticidad
    for i, inc in enumerate(incidents, 1):
        crit_color = CRITICALITY_COLORS.get(inc.criticality, colors.grey)
        table_style.add('TEXTCOLOR', (3, i), (3, i), crit_color)
        table_style.add('FONTNAME', (3, i), (3, i), 'Helvetica-Bold')

    table.setStyle(table_style)
    story.append(table)
    story.append(Spacer(1, 1*cm))

    # Pie de página
    footer_style = ParagraphStyle('footer', parent=styles['Normal'], fontSize=8,
                                   textColor=colors.grey, alignment=TA_CENTER)
    story.append(HRFlowable(width='100%', thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph('SGIS-UCV — Sistema de Gestión de Incidentes de Seguridad | Confidencial', footer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
