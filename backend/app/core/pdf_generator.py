import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT

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
            fontSize=26,
            spaceAfter=30,
            textColor=self.primary_color,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceBefore=20,
            spaceAfter=15,
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
            fontSize=10,
            textColor=colors.HexColor('#374151'),
            leading=14
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
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=50
            )
    
            elements = []
            
            # --- Header Section ---
            elements.append(Paragraph("PlagiaScan Analysis Report", self.styles['ReportTitle']))
            
            # Meta Info Table
            meta_data = [
                [f"Scan ID: #{self.scan.id}", f"Date: {datetime.now().strftime('%B %d, %Y')}"]
            ]
            meta_table = Table(meta_data, colWidths=[3.5*inch, 3.5*inch])
            meta_table.setStyle(TableStyle([
                ('TEXTCOLOR', (0,0), (-1,-1), colors.gray),
                ('ALIGN', (1,0), (1,0), 'RIGHT'),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 20),
            ]))
            elements.append(meta_table)
            elements.append(Spacer(1, 0.2*inch))

            # --- Scores Section ---
            score = self.scan.overall_score
            ai_score = self.scan.report_data.get('ai_detection', {}).get('ai_probability', 0)
            
            # Determine colors based on score
            plag_color = colors.red if score > 20 else colors.green
            ai_color = colors.orange if ai_score > 50 else colors.blue
            
            score_data = [
                ["Plagiarism Score", "AI Probability"],
                [f"{score:.1f}%", f"{ai_score:.1f}%"]
            ]
            
            t = Table(score_data, colWidths=[3*inch, 3*inch])
            t.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica'),
                ('FONTSIZE', (0,0), (-1,0), 12),
                ('TEXTCOLOR', (0,0), (-1,0), colors.gray),
                
                ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,1), (-1,1), 32),
                ('TEXTCOLOR', (0,1), (0,1), plag_color),
                ('TEXTCOLOR', (1,1), (1,1), ai_color),
                
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ('TOPPADDING', (0,1), (-1,1), 20),  # Extra padding for large score text
                ('BOTTOMPADDING', (0,1), (-1,1), 25), # Extra padding for large score text
                ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FAFAFA')),
                ('ROUNDEDCORNERS', [10, 10, 10, 10]),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.5 * inch))

            # --- Web Matches Section ---
            web_matches = self.scan.report_data.get('ai_detection', {}).get('details', {}).get('web_matches', [])
            if web_matches:
                elements.append(Paragraph("Web Sources Found", self.styles['SectionHeader']))
                for match in web_matches:
                    # Create a card-like look for web matches
                    link = f'<a href="{match["url"]}" color="#4F46E5">{match["title"]}</a>'
                    match_text = f'''
                    <b>{match['similarity']}% Match</b><br/>
                    {link}<br/>
                    <font color="gray" size="9">"{match['snippet']}"</font>
                    '''
                    elements.append(Paragraph(match_text, self.styles['NormalText']))
                    elements.append(Spacer(1, 10))
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
