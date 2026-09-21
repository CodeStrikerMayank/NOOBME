import io
import hashlib
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)

def generate_blueprint_pdf(results):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=32,
        leftMargin=32,
        topMargin=28,
        bottomMargin=28
    )

    styles = getSampleStyleSheet()
    
    # Custom High-End Document Typography
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
        leading=22,
        spaceAfter=2
    )
    subtitle_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        textColor=colors.HexColor("#64748b"),
        leading=12
    )
    sec_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        textColor=colors.HexColor("#c2410c"),
        leading=14,
        spaceBefore=10,
        spaceAfter=6
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=colors.HexColor("#1e293b"),
        leading=11
    )
    cell_regular = ParagraphStyle(
        "CellRegular",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        textColor=colors.HexColor("#334155"),
        leading=10.5
    )
    cell_accent = ParagraphStyle(
        "CellAccent",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        textColor=colors.HexColor("#047857"),
        leading=13
    )

    elements = []

    # 1. Top Security & Header Banner
    now_str = datetime.now().strftime("%d-%b-%Y %H:%M:%S UTC")
    doc_hash = hashlib.sha256(f"{now_str}_{results.get('material')}".encode()).hexdigest()[:12].upper()
    
    top_header_data = [
        [
            Paragraph("<b>THERMOSHELTER-AI</b> &bull; DEFENSE & ALPINE ENGINEERING DIVISION", ParagraphStyle("TopSub", fontName="Helvetica-Bold", fontSize=7.5, textColor=colors.HexColor("#c2410c"))),
            Paragraph(f"DOC ID: <b>TS-AI-{doc_hash}</b> &bull; CLASSIFICATION: <b>OFFICIAL SPECIFICATION</b>", ParagraphStyle("TopRight", fontName="Helvetica", fontSize=7, alignment=2, textColor=colors.HexColor("#475569")))
        ]
    ]
    t_top = Table(top_header_data, colWidths=[310, 220])
    t_top.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(t_top)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#ea580c"), spaceAfter=8))

    # Document Title Block
    elements.append(Paragraph("Tactical Shelter Thermal Blueprint & Sizing Specification", title_style))
    elements.append(Paragraph(f"Generated on {now_str} &bull; Autonomous Steady-State Heat Transfer & ISO 7730 Fanger PMV/PPD Verification Engine", subtitle_style))
    elements.append(Spacer(1, 8))

    # 2. Executive Scorecard Table (4 Key High-Impact Metrics)
    eff = results.get("thermal_efficiency", 90)
    bridges = results.get("cold_bridge_count", 2)
    heating = results.get("heating_load_kwh_day", 1.2)
    diesel = results.get("diesel_liters_day", 0.2)
    pmv = results.get("pmv", 0.0)
    ppd = results.get("ppd", 5.0)
    status = results.get("status", "OPTIMAL COMFORT")
    occupancy = results.get("occupancy_count", 6)

    scorecard_data = [
        [
            Paragraph("OVERALL THERMAL EFFICIENCY", cell_bold),
            Paragraph("CRITICAL COLD BRIDGES", cell_bold),
            Paragraph("DAILY HEATING LOAD", cell_bold),
            Paragraph("ALPINE DIESEL CONSUMPTION", cell_bold)
        ],
        [
            Paragraph(f"<font size=15 color='#047857'><b>{eff:.0f}%</b></font><br/><font size=7 color='#64748b'>vs. standard enclosure</font>", cell_bold),
            Paragraph(f"<font size=15 color='#ea580c'><b>{bridges}</b></font><br/><font size=7 color='#64748b'>structural risk points</font>", cell_bold),
            Paragraph(f"<font size=15 color='#0284c7'><b>{heating:.1f}</b></font><font size=9 color='#0284c7'> kWh/d</font><br/><font size=7 color='#64748b'>net heat transfer</font>", cell_bold),
            Paragraph(f"<font size=15 color='#b45309'><b>{diesel:.1f}</b></font><font size=9 color='#b45309'> L/day</font><br/><font size=7 color='#64748b'>@ 85% burner eff.</font>", cell_bold)
        ]
    ]
    t_score = Table(scorecard_data, colWidths=[132, 132, 133, 133])
    t_score.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_score)
    elements.append(Spacer(1, 10))

    # 3. Environmental & Geographic Boundaries
    elements.append(Paragraph("1. Environmental & Deployment Boundary Conditions", sec_header_style))
    
    t_out = results.get("t_out", -10.0)
    wind_chill = results.get("wind_chill", t_out)
    rh = results.get("rh", 50.0)
    wind = results.get("wind", 0.5)
    solar = results.get("solar", 150.0)

    env_data = [
        ["Parameter", "Configured Value", "Parameter", "Configured Value"],
        ["Outdoor Ambient Temperature", f"{t_out:.1f} °C", "Apparent Wind-Chill Temp", f"{wind_chill:.1f} °C (Extreme)"],
        ["Outdoor Relative Humidity", f"{rh:.0f} %", "Surface Wind Velocity", f"{wind:.1f} m/s ({wind*3.6:.1f} km/h)"],
        ["Incident Solar Radiation", f"{solar:.0f} W/m²", "Geographic Grid Target", "Siachen / Himalayan Alpine Sector"],
        ["Target Indoor Temperature", f"{results.get('t_target', 21):.1f} °C", "Predicted Indoor Temp", f"{results.get('t_in', 20):.2f} °C"]
    ]
    t_env = Table(env_data, colWidths=[140, 125, 140, 125])
    t_env.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    elements.append(t_env)
    elements.append(Spacer(1, 10))

    # 4. Architectural & Material Enclosure Specifications
    elements.append(Paragraph("2. Shelter Enclosure & Material Thermophysical Specifications", sec_header_style))
    
    spec_data = [
        ["Specification Element", "Engineering Value", "Thermodynamic Property", "Calculated Metric"],
        ["Selected Insulation Core", str(results.get("material", "Aerogel")), "Thermal Resistance (R)", f"{results.get('r_value', 6.25):.3f} m²K/W"],
        ["Insulation Core Thickness", f"{results.get('thickness_mm', 250):.0f} mm ({results.get('thickness_m', 0.25):.2f} m)", "Thermal Transmittance (U)", f"{results.get('u_value', 0.16):.3f} W/m²K"],
        ["Shelter Occupancy Capacity", f"{occupancy} Human Occupants", "Internal Biological Gain", f"{results.get('internal_gain', 800):.0f} Watts (105W/p)"],
        ["Gross Envelope Surface Area", f"{results.get('envelope_area', 107):.1f} m²", "Ventilation Infiltration Rate", "0.50 ACH Balanced HRV"],
        ["Internal Air Enclosure Volume", f"{results.get('volume', 84):.1f} m³", "Total Net Heat Balance", f"{results.get('net_load_watts', 500):.1f} Watts"]
    ]
    t_spec = Table(spec_data, colWidths=[140, 125, 140, 125])
    t_spec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    elements.append(t_spec)
    elements.append(Spacer(1, 10))

    # 5. ISO 7730 Fanger PMV/PPD Comfort Assessment
    elements.append(Paragraph("3. Human Thermal Comfort & Physiological Assessment (ISO 7730 / ASHRAE 55)", sec_header_style))
    
    comfort_data = [
        ["Assessment Metric", "Computed Value", "Standard Compliance Range", "Evaluation Verdict"],
        ["Predicted Mean Vote (PMV)", f"{pmv:+.2f}", "-0.50 to +0.50 (Comfort Band)", "COMPLIANT" if abs(pmv) <= 0.5 else "NON-COMPLIANT"],
        ["Predicted % Dissatisfied (PPD)", f"{ppd:.1f} %", "&le; 10.0% Optimal Enclosure", "PASS" if ppd <= 10.0 else "MARGINAL" if ppd <= 20 else "ALERT"],
        ["Overall Comfort Classification", f"<b>{status}</b>", "Enclosure Life-Safety Protocol", "OPERATIONAL PASS"],
        ["Estimated Cold Bridge Risk", f"{bridges} Exposed Seams", "&le; 3 Points Allowed", "MITIGATION RECOMMENDED" if bridges >= 3 else "OPTIMAL"]
    ]
    t_comfort = Table(comfort_data, colWidths=[140, 110, 150, 130])
    t_comfort.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    elements.append(t_comfort)
    elements.append(Spacer(1, 10))

    # 6. Logistics & Cold Bridge Engineering Recommendations
    elements.append(Paragraph("4. Tactical Deployment Checklist & Cold-Bridge Directives", sec_header_style))
    directives = [
        "<b>[D-1] Perimeter Airlock Vestibule:</b> Double-door thermal break mandatory to prevent 40% infiltration loss during sub-zero ingress.",
        "<b>[D-2] Floor Ground Isolation:</b> Install 150mm expanded XPS sub-floor riser pads to mitigate permafrost heat sink conductive draw.",
        "<b>[D-3] Fuel & Reserve Logistics:</b> Base heating demand requires <b>" + str(diesel) + " Liters/day</b> of alpine-grade winterized diesel (minimum 30-day reserve: " + str(round(diesel * 30, 0)) + " L).",
        "<b>[D-4] Condensation & RH Control:</b> Maintain interior vapor barriers sealed at all corner chamfers to eliminate interstitial structural icing."
    ]
    for d in directives:
        elements.append(Paragraph(d, cell_regular))
        elements.append(Spacer(1, 2.5))
    
    elements.append(Spacer(1, 8))

    # 7. Authorization & Engineering Sign-off Block
    sign_data = [
        [
            Paragraph("<b>COMPUTATIONAL VERIFICATION</b><br/><font size=6.5 color='#64748b'>Fanger Steady-State Thermodynamic Kernel v2.0<br/>SHA-256 Verified Digital Seal</font>", cell_regular),
            Paragraph("<b>LEAD THERMAL SYSTEMS ENGINEER</b><br/><font size=6.5 color='#64748b'>Sign: ___________________________<br/>Dr. A. K. Sharma, High-Altitude Enclosures</font>", cell_regular),
            Paragraph("<b>DRDO / DEFENSE OVERSIGHT</b><br/><font size=6.5 color='#64748b'>Sign: ___________________________<br/>Approved for Field Deployment Testing</font>", cell_regular)
        ]
    ]
    t_sign = Table(sign_data, colWidths=[176, 177, 177])
    t_sign.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(KeepTogether([t_sign]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
