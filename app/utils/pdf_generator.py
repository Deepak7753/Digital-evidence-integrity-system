import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from datetime import datetime

def generate_evidence_pdf(report_path: str, case_data: dict, evidence_list: list, custody_histories: dict, qr_paths: dict) -> None:
    """
    Generate a highly professional digital forensic PDF report using ReportLab.
    
    :param report_path: Destination path for the PDF.
    :param case_data: Dict with case_number, name, status, investigator, and description.
    :param evidence_list: List of dicts/objects with evidence details (id, file_name, file_size, category, upload_date, original_hash, status).
    :param custody_histories: Dict mapping evidence_id -> list of custody record dicts.
    :param qr_paths: Dict mapping evidence_id -> absolute path to QR code on disk.
    """
    doc = SimpleDocTemplate(
        report_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles matching Cyber Security theme
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor('#0f172a'),  # Dark Slate/Navy
        spaceAfter=15,
        alignment=0
    )
    
    h2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor('#1e3a8a'),  # Deep Navy Blue
        spaceBefore=10,
        spaceAfter=8
    )
    
    normal_style = styles['Normal']
    
    bold_label = ParagraphStyle(
        'BoldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#334155')
    )
    
    table_text = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontSize=8,
        leading=10
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white
    )

    story = []
    
    # Document Header / Banner
    story.append(Paragraph("DIGITAL EVIDENCE INTEGRITY SYSTEM", title_style))
    story.append(Paragraph(f"<b>FORENSIC ANALYSIS REPORT</b> &mdash; Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 15))
    
    # Section 1: Case Details
    story.append(Paragraph("1. Case Metadata", h2_style))
    case_table_data = [
        [Paragraph("Case Number:", bold_label), Paragraph(case_data.get('case_number', 'N/A'), normal_style),
         Paragraph("Status:", bold_label), Paragraph(case_data.get('status', 'N/A'), normal_style)],
        [Paragraph("Case Name:", bold_label), Paragraph(case_data.get('name', 'N/A'), normal_style),
         Paragraph("Investigator:", bold_label), Paragraph(case_data.get('investigator', 'N/A'), normal_style)],
        [Paragraph("Description:", bold_label), Paragraph(case_data.get('description', 'No description provided'), normal_style),
         Paragraph("", bold_label), Paragraph("", normal_style)]
    ]
    
    case_table = Table(case_table_data, colWidths=[100, 170, 80, 190])
    case_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,2), (-1,2), 0.5, colors.lightgrey)
    ]))
    story.append(case_table)
    story.append(Spacer(1, 15))
    
    # Section 2: Evidence Summary
    story.append(Paragraph("2. Evidence Summary & Integrity Status", h2_style))
    
    for idx, ev in enumerate(evidence_list):
        story.append(Paragraph(f"<b>Evidence Item #{idx+1}: {ev.get('title')}</b>", bold_label))
        
        status_color = '#10b981'  # Green
        if ev.get('status') == 'Tampered':
            status_color = '#ef4444'  # Red
        elif ev.get('status') == 'Warning':
            status_color = '#f59e0b'  # Amber
            
        ev_status_html = f"<font color='{status_color}'><b>{ev.get('status')}</b></font>"
        
        # Build metadata list
        ev_table_data = [
            [Paragraph("File Name:", bold_label), Paragraph(ev.get('file_name'), normal_style),
             Paragraph("Category:", bold_label), Paragraph(ev.get('category'), normal_style)],
            [Paragraph("File Size:", bold_label), Paragraph(f"{ev.get('file_size')} bytes", normal_style),
             Paragraph("Upload Date:", bold_label), Paragraph(ev.get('upload_date'), normal_style)],
            [Paragraph("SHA-256 Hash:", bold_label), Paragraph(f"<code>{ev.get('original_hash')}</code>", normal_style),
             Paragraph("Integrity:", bold_label), Paragraph(ev_status_html, normal_style)]
        ]
        
        # Check if QR image is available
        qr_cell = Paragraph("", normal_style)
        ev_id = ev.get('id')
        if ev_id in qr_paths and os.path.exists(qr_paths[ev_id]):
            try:
                qr_cell = RLImage(qr_paths[ev_id], width=70, height=70)
            except Exception:
                pass
                
        # Structure the table containing data on left and QR code on the right
        data_table = Table(ev_table_data, colWidths=[90, 160, 80, 130])
        data_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        
        outer_table_data = [
            [data_table, qr_cell]
        ]
        outer_table = Table(outer_table_data, colWidths=[460, 80])
        outer_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LINEBELOW', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        
        story.append(outer_table)
        story.append(Spacer(1, 10))
        
        # Custody history for this evidence
        history = custody_histories.get(ev_id, [])
        if history:
            story.append(Paragraph("Chain of Custody History:", bold_label))
            history_table_data = [
                [Paragraph("Action", header_style), 
                 Paragraph("From User", header_style), 
                 Paragraph("To User", header_style), 
                 Paragraph("Timestamp (UTC)", header_style), 
                 Paragraph("Remarks", header_style)]
            ]
            
            for record in history:
                history_table_data.append([
                    Paragraph(record.get('action'), table_text),
                    Paragraph(record.get('from_user', 'System'), table_text),
                    Paragraph(record.get('to_user', 'System'), table_text),
                    Paragraph(record.get('timestamp'), table_text),
                    Paragraph(record.get('remarks', ''), table_text)
                ])
                
            history_table = Table(history_table_data, colWidths=[100, 90, 90, 110, 150])
            history_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(history_table)
            story.append(Spacer(1, 15))
            
    # Section 3: Signature Block
    story.append(Spacer(1, 25))
    sig_data = [
        [Paragraph("<b>Investigator Signature</b>", bold_label), Paragraph("<b>Verification Authority</b>", bold_label)],
        [Spacer(1, 30), Spacer(1, 30)],
        [Paragraph("_____________________________", normal_style), Paragraph("_____________________________", normal_style)],
        [Paragraph(case_data.get('investigator', 'Forensic Examiner'), normal_style), Paragraph("Digital Evidence Integrity System Service", normal_style)]
    ]
    sig_table = Table(sig_data, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(sig_table)
    
    # Build Document
    doc.build(story)
