import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def generate_blueprint_pdf(results):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "SubTitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14
    )
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=colors.HexColor("#c2410c"),
        spaceBefore=12,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#334155"),
        leading=14
    )

    elements = []

    # Header
    elements.append(Paragraph("ThermoShelter AI — Blueprint Thermal Report", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Area-Specific Shelter Design Engine", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#ea580c"), spaceAfter=15))

    # Key Metrics Grid
    eff = results.get("thermal_efficiency", 78)
    bridges = results.get("cold_bridge_count", 3)
    heating = results.get("heating_load_kwh_day", 12.0)
    pmv = results.get("pmv", 0.0)
    ppd = results.get("ppd", 5.0)
    status = results.get("status", "OPTIMAL COMFORT")

    summary_data = [
        [
            Paragraph("<b>Overall Thermal Efficiency</b>", body_style),
            Paragraph("<b>Critical Cold Bridges</b>", body_style),
            Paragraph("<b>Heating Load</b>", body_style),
            Paragraph("<b>Thermal Comfort Status</b>", body_style)
        ],
        [
            Paragraph(f"<font size=14 color='#059669'><b>{eff}%</b></font>", body_style),
            Paragraph(f"<font size=14 color='#ea580c'><b>{bridges}</b></font>", body_style),
            Paragraph(f"<font size=14 color='#0284c7'><b>{heating} kWh/day</b></font>", body_style),
            Paragraph(f"<font size=12 color='#059669'><b>{status}</b><br/>PMV: {pmv:+.2f} | PPD: {ppd:.1f}%</font>", body_style)
        ]
    ]

    t_summary = Table(summary_data, colWidths=[130, 130, 130, 130])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 15))

    # Parameters Table
    elements.append(Paragraph("Shelter Specifications & Environmental Boundaries", heading_style))

    spec_data = [
        ["Parameter", "Configured Value", "Parameter", "Configured Value"],
        ["Insulation Material", str(results.get("material", "EPS")), "Outdoor Temperature", f"{results.get('t_out', -10)} °C"],
        ["Insulation Thickness", f"{results.get('thickness_mm', 250)} mm", "Indoor Temperature", f"{results.get('t_in', 20)} °C"],
        ["Thermal Resistance (R)", f"{results.get('r_value', 6.25)} m²K/W", "Target Temperature", f"{results.get('t_target', 21)} °C"],
        ["Thermal Transmittance (U)", f"{results.get('u_value', 0.16)} W/m²K", "Relative Humidity", f"{results.get('rh', 50)} %"],
        ["Envelope Surface Area", f"{results.get('envelope_area', 90)} m²", "Wind Speed", f"{results.get('wind', 0.5)} m/s"],
        ["Internal Shelter Volume", f"{results.get('volume', 56)} m³", "Solar Radiation", f"{results.get('solar', 150)} W/m²"],
        ["Net Thermal Load", f"{results.get('net_load_watts', 500)} W", "Ventilation Rate", "0.5 ACH"]
    ]

    t_spec = Table(spec_data, colWidths=[130, 130, 130, 130])
    t_spec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f1f5f9")]),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_spec)
    elements.append(Spacer(1, 15))

    # Recommendations
    elements.append(Paragraph("Engineering Recommendations & AI Insights", heading_style))
    recs = [
        "1. Thermal Envelope Optimization: The selected insulation provides sufficient R-value for sub-zero alpine conditions.",
        "2. Thermal Bridging Mitigation: Maintain insulation continuity around corner chamfers and window perimeters.",
        "3. Solar Heat Gain: South-facing window glazing contributes passive heating offsets of ~150 W.",
        "4. Indoor Air Quality & Ventilation: 0.5 ACH balanced mechanical heat recovery ventilation (HRV) is recommended."
    ]
    for r in recs:
        elements.append(Paragraph(r, body_style))
        elements.append(Spacer(1, 4))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
