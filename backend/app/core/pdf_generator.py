import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing

class PDFGenerator:
    def __init__(self, scan_data):
        self.scan = scan_data
        self.buffer = io.BytesIO()
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        # Professional Color Palette
        self.primary_color = colors.HexColor('#4F46E5')  # Indigo-600
        self.secondary_color = colors.HexColor('#1F2937') # Gray-800
        self.accent_color = colors.HexColor('#F3F4F6')    # Gray-100
        
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            alignment=TA_CENTER,
            fontSize=24,
            spaceAfter=15,
            textColor=self.primary_color,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=15,
            spaceAfter=10,
            textColor=self.secondary_color,
            fontName='Helvetica-Bold',
            borderPadding=5,
            borderWidth=0,
            borderColor=self.primary_color,
            borderRadius=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='NormalText',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#374151'),
            leading=13
        ))

        self.styles.add(ParagraphStyle(
            name='MatchContent',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#1F2937'),
            leading=12
        ))

    def generate(self):
        print(f"DEBUG: Generating PDF for Scan {self.scan.id}")
        try:
            doc = SimpleDocTemplate(
                self.buffer,
                pagesize=letter,
                rightMargin=40,
                leftMargin=40,
                topMargin=40,
                bottomMargin=40
            )
    
            elements = []
            
            # --- Header Section ---
            elements.append(Paragraph("PlagiaScan Academic & Forensic Audit Report", self.styles['ReportTitle']))
            
            # Public Verification URL & QR Code
            verify_url = f"http://localhost:5173/verify/{self.scan.id}"
            qr = QrCodeWidget(verify_url)
            b = qr.getBounds()
            w = b[2] - b[0]
            h = b[3] - b[1]
            qr_size = 62
            qr_d = Drawing(qr_size, qr_size, transform=[qr_size/w, 0, 0, qr_size/h, 0, 0])
            qr_d.add(qr)

            doc_title = getattr(self.scan, "document", None) and getattr(self.scan.document, "filename", None) or f"Document #{self.scan.document_id}"
            
            header_text = Paragraph(f"""
            <b>Document:</b> {doc_title}<br/>
            <b>Scan Reference:</b> #{self.scan.id} &nbsp;|&nbsp; <b>Date:</b> {datetime.now().strftime('%B %d, %Y')}<br/>
            <b>Engine:</b> Verbatim Web Overlap + Statistical AI Forensic Engine<br/>
            <b>Verification URL:</b> <font color="#4F46E5">{verify_url}</font>
            """, self.styles['NormalText'])

            qr_block = [
                qr_d,
                Paragraph("<font size=7 color='#6B7280'>Scan to Verify</font>", ParagraphStyle('QRLbl', alignment=TA_CENTER))
            ]

            meta_table = Table([[header_text, qr_block]], colWidths=[5.6*inch, 1.4*inch])
            meta_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (1,0), (1,-1), 'CENTER'),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            elements.append(meta_table)
            elements.append(Spacer(1, 0.15*inch))

            # --- Scores Section ---
            score = self.scan.overall_score
            ai_score = self.scan.report_data.get('ai_detection', {}).get('ai_probability', 0)
            
            # Determine colors based on score
            plag_color = colors.HexColor('#DC2626') if score > 20 else colors.HexColor('#16A34A')
            ai_color = colors.HexColor('#9333EA') if ai_score > 50 else colors.HexColor('#2563EB')
            
            score_data = [
                ["Plagiarism Index", "AI Probability Score"],
                [f"{score:.1f}%", f"{ai_score:.1f}%"]
            ]
            
            t = Table(score_data, colWidths=[3.5*inch, 3.5*inch])
            t.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 11),
                ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#4B5563')),
                
                ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,1), (-1,1), 28),
                ('TEXTCOLOR', (0,1), (0,1), plag_color),
                ('TEXTCOLOR', (1,1), (1,1), ai_color),
                
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,1), (-1,1), 10),
                ('BOTTOMPADDING', (0,1), (-1,1), 14),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAFAFA')),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.15 * inch))

            # Sub-scores breakdown if available
            rep = self.scan.report_data or {}
            if rep.get('verbatim_score') is not None:
                sub_data = [
                    ["Verbatim Match", "Paraphrase / Mosaic", "Verified Citations", "Sources Crawled"],
                    [
                        f"{rep.get('verbatim_score', 0):.1f}%",
                        f"{rep.get('paraphrase_score', 0):.1f}%",
                        f"{rep.get('exempted_citations_count', 0)} exempted",
                        f"{rep.get('sources_investigated', len(rep.get('web_matches', [])))} online"
                    ]
                ]
                sub_t = Table(sub_data, colWidths=[1.75*inch, 1.75*inch, 1.75*inch, 1.75*inch])
                sub_t.setStyle(TableStyle([
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,0), 8),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.gray),
                    ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,1), (-1,1), 10),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F9FAFB')),
                ]))
                elements.append(sub_t)
                elements.append(Spacer(1, 0.15 * inch))

            # --- Readability & Stylometrics Matrix ---
            readability = rep.get('readability')
            if readability:
                elements.append(Paragraph("Readability & Stylometrics Matrix", self.styles['SectionHeader']))
                read_data = [
                    ["Flesch Reading Ease", "Grade Level (FKGL)", "Gunning Fog Index", "Lexical Diversity (TTR)", "Passive Voice"],
                    [
                        f"{readability.get('flesch_reading_ease', 0):.1f} ({readability.get('reading_ease_level', 'N/A')})",
                        f"Grade {readability.get('flesch_kincaid_grade', 0):.1f}",
                        f"{readability.get('gunning_fog_index', 0):.1f} ({readability.get('fog_reading_level', 'N/A')})",
                        f"{readability.get('lexical_diversity_ttr', 0):.1f}%",
                        f"{readability.get('passive_voice_ratio', 0):.1f}% ({readability.get('passive_sentences_count', 0)} sents)"
                    ]
                ]
                read_t = Table(read_data, colWidths=[1.5*inch, 1.3*inch, 1.4*inch, 1.4*inch, 1.4*inch])
                read_t.setStyle(TableStyle([
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,0), 7.5),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#374151')),
                    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEF2FF')),
                    ('FONTNAME', (0,1), (-1,1), 'Helvetica'),
                    ('FONTSIZE', (0,1), (-1,1), 8.5),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                    ('BACKGROUND', (0,1), (-1,1), colors.white),
                ]))
                elements.append(read_t)
                elements.append(Spacer(1, 0.15 * inch))

            # --- Forensic Synthesis Summary ---
            synthesis = rep.get('synthesis_summary')
            if synthesis:
                elements.append(Paragraph("Forensic Synthesis Summary", self.styles['SectionHeader']))
                elements.append(Paragraph(synthesis, self.styles['NormalText']))
                elements.append(Spacer(1, 0.25 * inch))

            # --- Web Matches Section ---
            web_matches = rep.get('web_matches', [])
            if web_matches:
                elements.append(Paragraph("Web Sources Found", self.styles['SectionHeader']))
                for match in web_matches[:6]:
                    link = f'<a href="{match.get("source_url", match.get("url", ""))}" color="#4F46E5">{match.get("source_title", match.get("title", "Web Source"))}</a>'
                    match_type_label = match.get('match_type', '').replace('_', ' ').title()
                    match_text = f'''
                    <b>{match_type_label or "Matched Source"}</b> &mdash; {link}<br/>
                    <font color="gray" size="9">"{match.get('snippet', '')[:200]}"</font>
                    '''
                    elements.append(Paragraph(match_text, self.styles['NormalText']))
                    elements.append(Spacer(1, 8))
                elements.append(Spacer(1, 0.2 * inch))

            # --- Detailed Matches Section ---
            matches = self.scan.report_data.get('matches', [])
            if matches:
                elements.append(Paragraph("Detailed Content Analysis", self.styles['SectionHeader']))
                elements.append(Spacer(1, 10))
                
                for match in matches:
                    chunk_score = match['best_match']['score'] * 100
                    
                    # Header for the match
                    elements.append(Paragraph(f"<b>Segment #{match['chunk_index'] + 1}</b> <font color='red'>({chunk_score:.1f}% Match)</font>", self.styles['NormalText']))
                    elements.append(Spacer(1, 5))
                    
                    # Side-by-side comparison using a Table
                    # Left: User Text, Right: Source Text
                    
                    user_text = Paragraph(f"<b>Your Content:</b><br/><br/>{match['chunk_text']}", self.styles['MatchContent'])
                    source_text = Paragraph(f"<b>Matched Source (Doc {match['best_match']['source_doc_id']}):</b><br/><br/>{match['best_match']['text']}", self.styles['MatchContent'])
                    
                    comp_data = [[user_text, source_text]]
                    comp_table = Table(comp_data, colWidths=[3.2*inch, 3.2*inch])
                    comp_table.setStyle(TableStyle([
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
                        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#FFFBEB')), # Light Yellow for user
                        ('BACKGROUND', (1,0), (1,0), colors.HexColor('#FEF2F2')), # Light Red for source
                        ('PADDING', (0,0), (-1,-1), 8),
                    ]))
                    
                    elements.append(comp_table)
                    elements.append(Spacer(1, 15))

            # Build PDF
            doc.build(elements)
            self.buffer.seek(0)
            print("DEBUG: PDF generated successfully.")
            return self.buffer.getvalue()

        except Exception as e:
            print(f"ERROR building PDF: {e}")
            import traceback
            traceback.print_exc()
            raise e
