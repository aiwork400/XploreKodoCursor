"""
Performance Report Generator Tool

Generates PDF 'Sensei Performance Report' summarizing student's JLPT N5-N3 progress
across the three tracks (Care-giving, Academic, Food/Tech).

Features:
- Japanese font rendering with Unicode support
- Visual charts (Radar/Bar charts)
- LLM-powered bilingual assessment
- Professional report structure with logo and badges
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agency_swarm.tools import BaseTool
from pydantic import Field
from sqlalchemy.orm import Session

import config
from database.db_manager import Candidate, CurriculumProgress, SessionLocal

# Try to import reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.lib.fonts import addMapping
    from reportlab.graphics.shapes import Drawing, Rect, Line, Circle, Group, String
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    SimpleDocTemplate = None

# Try to import Gemini for LLM assessment
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class GeneratePerformanceReport(BaseTool):
    """
    Generate PDF performance report for a candidate.
    
    Pulls data from Mastery Heatmap logic and creates a comprehensive
    'Sensei Performance Report' summarizing JLPT N5-N3 progress across
    all three tracks with Japanese font support, visual charts, and
    LLM-powered bilingual assessment.
    """

    candidate_id: str = Field(..., description="Candidate identifier")
    output_path: str | None = Field(
        default=None,
        description="Optional output path for PDF file. If not provided, saves to static/reports/"
    )

    def _register_japanese_font(self):
        """
        Register Japanese font with fallback logic.
        Tries custom font from /assets/fonts/, falls back to UnicodeCIDFont.
        """
        if not REPORTLAB_AVAILABLE:
            return
        
        try:
            # Try to find custom Japanese font in assets/fonts/
            fonts_dir = project_root / "assets" / "fonts"
            fonts_dir.mkdir(parents=True, exist_ok=True)
            
            # Look for common Japanese fonts
            japanese_fonts = [
                "NotoSansJP-Regular.ttf",
                "NotoSansCJK-Regular.ttf",
                "HeiseiKakuGo-W5.ttf",
                "NotoSansJP.ttf"
            ]
            
            font_registered = False
            for font_name in japanese_fonts:
                font_path = fonts_dir / font_name
                if font_path.exists():
                    try:
                        # ATOMIC FIX: Bulletproof PDF Font Mapping using registerFontFamily
                        family_name = 'japanesefont'
                        pdfmetrics.registerFont(TTFont(family_name, str(font_path)))
                        
                        # Explicitly link the family name to itself for all styles
                        try:
                            # Try registerFontFamily (newer ReportLab versions)
                            pdfmetrics.registerFontFamily(
                                family_name,
                                normal=family_name,
                                bold=family_name,
                                italic=family_name,
                                boldItalic=family_name
                            )
                        except AttributeError:
                            # Fallback to addMapping for older ReportLab versions
                            addMapping(family_name, 0, 0, family_name)  # normal
                            addMapping(family_name, 1, 0, family_name)  # bold
                            addMapping(family_name, 0, 1, family_name)  # italic
                            addMapping(family_name, 1, 1, family_name)  # bold-italic
                        font_registered = True
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"Registered custom Japanese font: {font_name}")
                        break
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Failed to register {font_name}: {e}")
                        continue
            
            # Fallback to ReportLab's built-in Japanese CID font
            if not font_registered:
                try:
                    # ATOMIC FIX: Bulletproof PDF Font Mapping using registerFontFamily
                    family_name = 'japanesefont'
                    cid_font_name = 'HeiseiKakuGo-W5'
                    pdfmetrics.registerFont(UnicodeCIDFont(cid_font_name))
                    
                    # Explicitly link the family name to itself for all styles
                    try:
                        # Try registerFontFamily (newer ReportLab versions)
                        pdfmetrics.registerFontFamily(
                            family_name,
                            normal=cid_font_name,
                            bold=cid_font_name,
                            italic=cid_font_name,
                            boldItalic=cid_font_name
                        )
                    except AttributeError:
                        # Fallback to addMapping for older ReportLab versions
                        addMapping(family_name, 0, 0, cid_font_name)  # normal
                        addMapping(family_name, 1, 0, cid_font_name)  # bold
                        addMapping(family_name, 0, 1, cid_font_name)  # italic
                        addMapping(family_name, 1, 1, cid_font_name)  # bold-italic
                    font_registered = True
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info("Using ReportLab built-in Japanese CID font: HeiseiKakuGo-W5")
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to register Japanese CID font: {e}")
            
            return font_registered
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error registering Japanese font: {e}")
            return False

    def _calculate_mastery_scores(self, candidate_id: str) -> dict:
        """
        Calculate mastery scores (same logic as dashboard).
        Returns dict with track -> skill -> score mapping.
        """
        db: Session = SessionLocal()
        try:
            curriculum = db.query(CurriculumProgress).filter(
                CurriculumProgress.candidate_id == candidate_id
            ).first()
            
            if not curriculum or not curriculum.dialogue_history:
                tracks = ["Care-giving", "Academic", "Food/Tech"]
                skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
                return {
                    track: {skill: 0.0 for skill in skills}
                    for track in tracks
                }
            
            dialogue_history = curriculum.dialogue_history or []
            tracks = ["Care-giving", "Academic", "Food/Tech"]
            skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
            
            track_scores = {
                track: {skill: [] for skill in skills}
                for track in tracks
            }
            
            for entry in dialogue_history:
                track = None
                if "session_snapshot" in entry:
                    track = entry["session_snapshot"].get("track")
                elif "track" in entry:
                    track = entry.get("track")
                
                if not track or track not in tracks:
                    continue
                
                evaluation = entry.get("evaluation")
                if not evaluation:
                    continue
                
                status = evaluation.get("status", "")
                feedback = evaluation.get("feedback", "").lower()
                explanation = evaluation.get("explanation", "").lower()
                affected_skills = evaluation.get("affected_skills", [])
                
                if not affected_skills:
                    vocab_keywords = ["vocabulary", "terminology", "word", "term"]
                    tone_keywords = ["tone", "honorific", "desu", "masu", "keigo"]
                    logic_keywords = ["meaning", "context", "logic", "understand"]
                    
                    if any(kw in feedback or kw in explanation for kw in vocab_keywords):
                        affected_skills.append("Vocabulary")
                    if any(kw in feedback or kw in explanation for kw in tone_keywords):
                        affected_skills.append("Tone/Honorifics")
                    if any(kw in feedback or kw in explanation for kw in logic_keywords):
                        affected_skills.append("Contextual Logic")
                    
                    if not affected_skills:
                        affected_skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
                
                if status == "Acceptable":
                    score = 100.0
                elif status == "Partially Acceptable":
                    score = 50.0
                elif status == "Non-Acceptable":
                    score = 0.0
                else:
                    score = 50.0
                
                if status in ["Partially Acceptable", "Non-Acceptable"]:
                    for skill in affected_skills:
                        if skill in track_scores[track]:
                            track_scores[track][skill].append(score)
                else:
                    track_scores[track]["Vocabulary"].append(score)
                    track_scores[track]["Tone/Honorifics"].append(score)
                    track_scores[track]["Contextual Logic"].append(score)
            
            mastery_scores = {}
            for track in tracks:
                mastery_scores[track] = {}
                for skill in skills:
                    scores = track_scores[track][skill]
                    if scores:
                        avg_score = sum(scores) / len(scores)
                        mastery_scores[track][skill] = round(avg_score, 1)
                    else:
                        mastery_scores[track][skill] = 0.0
            
            return mastery_scores
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating mastery scores: {e}")
            tracks = ["Care-giving", "Academic", "Food/Tech"]
            skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
            return {
                track: {skill: 0.0 for skill in skills}
                for track in tracks
            }
        finally:
            db.close()

    def _generate_llm_assessment(self, track: str, skills: dict) -> str:
        """
        Generate English-only assessment using Gemini for the Official Performance Report.
        Returns english_assessment only.
        """
        if not GEMINI_AVAILABLE:
            return f"Student shows {sum(skills.values())/len(skills):.1f}% average mastery in {track}."
        
        try:
            # Format scores for prompt
            vocab_score = skills.get("Vocabulary", 0.0)
            tone_score = skills.get("Tone/Honorifics", 0.0)
            logic_score = skills.get("Contextual Logic", 0.0)
            
            # Pivot to English: Instruct LLM to generate detailed_assessment EXCLUSIVELY in English
            prompt = f"""Given these performance scores for the {track} track:
- Vocabulary: {vocab_score}%
- Tone/Honorifics: {tone_score}%
- Contextual Logic: {logic_score}%

Write a professional 3-4 sentence detailed assessment EXCLUSIVELY in English for the Official Performance Report.

Be encouraging but honest. Focus on strengths and specific areas for improvement. Provide actionable feedback."""
            
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            
            text = response.text.strip()
            
            # Parse response - English-only assessment
            english_assessment = text.strip()
            
            if not english_assessment:
                # Fallback if parsing fails
                english_assessment = f"Student demonstrates {sum(skills.values())/len(skills):.1f}% average mastery in {track}. Focus on areas scoring below 70% for improvement."
            
            return english_assessment
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error generating LLM assessment: {e}")
            # Fallback
            avg_score = sum(skills.values())/len(skills)
            return f"Student demonstrates {avg_score:.1f}% average mastery in {track}. Focus on areas scoring below 70% for improvement."

    def _create_bar_chart(self, mastery_scores: dict) -> Drawing:
        """
        Create a color-coded bar chart for track performance.
        """
        tracks = list(mastery_scores.keys())
        skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
        
        # Prepare data
        data = []
        for track in tracks:
            track_data = [mastery_scores[track].get(skill, 0.0) for skill in skills]
            data.append(track_data)
        
        # Create drawing
        drawing = Drawing(400, 300)
        
        # Create bar chart
        bc = VerticalBarChart()
        bc.x = 50
        bc.y = 50
        bc.width = 300
        bc.height = 200
        bc.data = data
        bc.categoryAxis.categoryNames = skills
        bc.bars[0].fillColor = colors.HexColor('#1976D2')  # Care-giving
        bc.bars[1].fillColor = colors.HexColor('#388E3C')  # Academic
        bc.bars[2].fillColor = colors.HexColor('#F57C00')  # Food/Tech
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = 100
        bc.valueAxis.labelTextFormat = '%d%%'
        
        drawing.add(bc)
        
        # Add title
        title = String(200, 280, 'Mastery Scores by Track', textAnchor='middle')
        title.fontName = 'Helvetica-Bold'
        title.fontSize = 14
        drawing.add(title)
        
        # Add legend
        legend_y = 260
        legend_colors = [colors.HexColor('#1976D2'), colors.HexColor('#388E3C'), colors.HexColor('#F57C00')]
        for i, track in enumerate(tracks):
            legend_rect = Rect(320, legend_y - i*20, 15, 15, fillColor=legend_colors[i])
            drawing.add(legend_rect)
            legend_text = String(340, legend_y - i*20 + 12, track, fontSize=9)
            drawing.add(legend_text)
        
        return drawing

    def _determine_jlpt_levels(self, mastery_scores: dict) -> dict:
        """
        Determine JLPT level for each track based on mastery scores.
        Returns dict with track -> JLPT level (N5, N4, or N3).
        """
        track_levels = {}
        
        for track, skills in mastery_scores.items():
            avg_score = sum(skills.values()) / len(skills) if skills else 0.0
            
            # Determine JLPT level based on average mastery
            # N5: 0-50%, N4: 50-70%, N3: 70%+
            if avg_score >= 70:
                track_levels[track] = "N3"
            elif avg_score >= 50:
                track_levels[track] = "N4"
            else:
                track_levels[track] = "N5"
        
        return track_levels

    def _calculate_career_readiness(self, track_jlpt_levels: dict) -> dict:
        """
        Calculate Career Readiness percentage for each track.
        N5 = 33%, N4 = 66%, N3 = 100%
        """
        readiness_map = {
            "N5": 33.0,
            "N4": 66.0,
            "N3": 100.0
        }
        
        career_readiness = {}
        for track, jlpt_level in track_jlpt_levels.items():
            career_readiness[track] = readiness_map.get(jlpt_level, 0.0)
        
        return career_readiness

    def _generate_pdf_report(self, candidate_id: str, mastery_scores: dict, output_path: str) -> str:
        """Generate PDF report using reportlab - English-only report with standard fonts."""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation. Install with: pip install reportlab")
        
        # English-Only PDF Report: Remove Japanese font dependency
        # Use standard fonts (Helvetica or Times-Roman) to eliminate 'Can't map' errors permanently
        
        # Get candidate info
        db = SessionLocal()
        try:
            candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
            candidate_name = candidate.full_name if candidate else candidate_id
        finally:
            db.close()
        
        # Create PDF document
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles with standard fonts (English-only report)
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#002147'),
            spaceAfter=30,
            alignment=1,  # Center
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#002147'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        # Assessment style using standard font (no Japanese font dependency)
        assessment_style = ParagraphStyle(
            'AssessmentStyle',
            parent=styles['Normal'],
            fontSize=11,
            fontName='Helvetica',  # Use standard Helvetica font
            leading=14
        )
        
        # Header with Logo and Badge
        story.append(Spacer(1, 0.3*inch))
        
        # Try to load logo
        logo_path = project_root / "assets" / "logo.png"
        if not logo_path.exists():
            logo_path = project_root / "assets" / "logo.jpg"
        
        if logo_path.exists():
            try:
                logo = Image(str(logo_path), width=2*inch, height=0.8*inch)
                story.append(logo)
                story.append(Spacer(1, 0.2*inch))
            except Exception:
                pass  # Skip logo if there's an error
        
        # Title with badge
        title_table_data = [
            [Paragraph("🏛️ ExploraKodo", title_style), Paragraph("Certified Performance Record", ParagraphStyle('Badge', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#D32F2F'), alignment=1))]
        ]
        title_table = Table(title_table_data, colWidths=[4*inch, 2*inch])
        title_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(title_table)
        
        story.append(Paragraph("Sensei Performance Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Report metadata
        report_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
        story.append(Paragraph(f"<b>Student:</b> {candidate_name}", styles['Normal']))
        story.append(Paragraph(f"<b>Student ID:</b> {candidate_id}", styles['Normal']))
        story.append(Paragraph(f"<b>Report Date:</b> {report_date}", styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Visual Chart
        story.append(Paragraph("Performance Overview", heading_style))
        chart_drawing = self._create_bar_chart(mastery_scores)
        story.append(chart_drawing)
        story.append(Spacer(1, 0.3*inch))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Paragraph(
            "This report summarizes your Japanese language learning progress across the "
            "ExploraKodo Triple-Track Coaching system. Your performance is evaluated across "
            "three tracks (Care-giving, Academic, Food/Tech) and three skill categories "
            "(Vocabulary, Tone/Honorifics, Contextual Logic).",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.2*inch))
        
        # Track Performance Summary
        story.append(Paragraph("Track Performance Summary", heading_style))
        
        # Calculate overall scores per track
        track_summary_data = [["Track", "Overall Score", "Status"]]
        for track, skills in mastery_scores.items():
            avg_score = sum(skills.values()) / len(skills) if skills else 0.0
            if avg_score >= 70:
                status = "Excellent"
            elif avg_score >= 50:
                status = "Good"
            else:
                status = "Needs Improvement"
            track_summary_data.append([track, f"{avg_score:.1f}%", status])
        
        track_table = Table(track_summary_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        track_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002147')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(track_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Detailed Performance by Track with LLM Assessment
        story.append(PageBreak())
        story.append(Paragraph("Detailed Performance by Track", heading_style))
        
        for track, skills in mastery_scores.items():
            # Track header
            story.append(KeepTogether([
                Paragraph(f"<b>{track} Track</b>", styles['Heading3']),
                Spacer(1, 0.1*inch)
            ]))
            
            # Skill breakdown table
            skill_data = [["Skill Category", "Mastery Score", "Level"]]
            for skill, score in skills.items():
                if score >= 70:
                    level = "Proficient"
                elif score >= 50:
                    level = "Developing"
                else:
                    level = "Beginner"
                skill_data.append([skill, f"{score:.1f}%", level])
            
            skill_table = Table(skill_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
            skill_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(skill_table)
            story.append(Spacer(1, 0.15*inch))
            
            # LLM-Powered Bilingual Assessment
            # English-only assessment (no Japanese)
            english_assessment = self._generate_llm_assessment(track, skills)
            
            story.append(Paragraph("<b>Sensei's Assessment:</b>", styles['Normal']))
            story.append(Paragraph(english_assessment, assessment_style))
            
            story.append(Spacer(1, 0.2*inch))
        
        # Recommendations
        story.append(PageBreak())
        story.append(Paragraph("Recommendations", heading_style))
        
        # Find weakest areas
        all_scores = []
        for track, skills in mastery_scores.items():
            for skill, score in skills.items():
                all_scores.append((track, skill, score))
        
        if all_scores:
            all_scores.sort(key=lambda x: x[2])
            weakest = all_scores[:3]
            
            story.append(Paragraph("<b>Areas for Improvement:</b>", styles['Normal']))
            for i, (track, skill, score) in enumerate(weakest, 1):
                story.append(Paragraph(
                    f"{i}. <b>{track} - {skill}</b>: {score}% (Target: 70%+)",
                    styles['Normal']
                ))
                story.append(Paragraph(
                    f"   Recommendation: Focus on {track} track lessons and practice {skill.lower()}.",
                    styles['Normal']
                ))
                story.append(Spacer(1, 0.1*inch))
        else:
            story.append(Paragraph("No assessment data available yet. Complete video sessions to generate performance metrics.", styles['Normal']))
        
        # Career & Visa Outlook Section
        story.append(PageBreak())
        story.append(Paragraph("Career & Visa Outlook", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Determine JLPT level and Career Readiness for each track
        track_jlpt_levels = self._determine_jlpt_levels(mastery_scores)
        track_career_readiness = self._calculate_career_readiness(track_jlpt_levels)
        
        # Track-specific visa information
        visa_info = {
            "Care-giving": {
                "requirement": "N4 is the minimum requirement for the 'Specified Skilled Worker (i)' visa, while N3 significantly increases salary potential in elderly care facilities.",
                "outlook": "High demand for caregivers in Japan with specialized 'Kaigo' vocabulary."
            },
            "Academic": {
                "requirement": "N2/N1 targets for MEXT scholarships and entrance into top-tier Japanese Universities.",
                "outlook": "Graduates in Japan have access to the 'Designated Activities' visa for job hunting."
            },
            "Food/Tech": {
                "requirement": "N4/N3 combined with AI/ML skills contributes points toward the 'Highly Skilled Professional' visa category.",
                "outlook": "Growing 'Startup Visa' opportunities for foreign entrepreneurs in the tech sector."
            }
        }
        
        # Display Career Readiness and Visa Outlook for each track
        for track, skills in mastery_scores.items():
            avg_score = sum(skills.values()) / len(skills) if skills else 0.0
            jlpt_level = track_jlpt_levels.get(track, "N5")
            career_readiness = track_career_readiness.get(track, 0.0)
            
            story.append(Paragraph(f"<b>{track} Track</b>", styles['Heading3']))
            story.append(Spacer(1, 0.1*inch))
            
            # Career Readiness Progress Bar (visual representation)
            story.append(Paragraph("<b>Career Readiness:</b>", styles['Normal']))
            
            # Determine color based on readiness
            if career_readiness >= 100:
                bar_color = colors.HexColor('#4CAF50')  # Green
            elif career_readiness >= 66:
                bar_color = colors.HexColor('#FF9800')  # Orange
            else:
                bar_color = colors.HexColor('#F44336')  # Red
            
            # Progress text with JLPT level
            progress_text = f"{career_readiness:.0f}% (JLPT {jlpt_level})"
            progress_style = ParagraphStyle(
                'ProgressText',
                parent=styles['Normal'],
                fontSize=11,
                textColor=bar_color,
                fontName='Helvetica-Bold'
            )
            story.append(Paragraph(progress_text, progress_style))
            
            # Visual progress bar using table with colored cells
            progress_bar_width = 4.5 * inch
            bar_cells = 20  # 20 cells for 5% increments
            filled_cells = int(career_readiness / 5)
            
            # Create progress bar cells
            progress_cells = []
            for i in range(bar_cells):
                if i < filled_cells:
                    # Filled cell
                    cell_style = TableStyle([
                        ('BACKGROUND', (0, 0), (0, 0), bar_color),
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (0, 0), 0),
                        ('RIGHTPADDING', (0, 0), (0, 0), 0),
                        ('TOPPADDING', (0, 0), (0, 0), 3),
                        ('BOTTOMPADDING', (0, 0), (0, 0), 3),
                    ])
                    progress_cells.append(Table([['']], colWidths=[progress_bar_width / bar_cells], rowHeights=[0.15*inch]))
                    progress_cells[-1].setStyle(cell_style)
                else:
                    # Empty cell
                    cell_style = TableStyle([
                        ('BACKGROUND', (0, 0), (0, 0), colors.lightgrey),
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (0, 0), 0),
                        ('RIGHTPADDING', (0, 0), (0, 0), 0),
                        ('TOPPADDING', (0, 0), (0, 0), 3),
                        ('BOTTOMPADDING', (0, 0), (0, 0), 3),
                    ])
                    progress_cells.append(Table([['']], colWidths=[progress_bar_width / bar_cells], rowHeights=[0.15*inch]))
                    progress_cells[-1].setStyle(cell_style)
            
            # Create a horizontal progress bar table
            progress_bar_table = Table([progress_cells], colWidths=[progress_bar_width / bar_cells] * bar_cells)
            progress_bar_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(progress_bar_table)
            story.append(Spacer(1, 0.15*inch))
            
            # Visa Requirements
            visa_data = visa_info.get(track, {})
            story.append(Paragraph("<b>Visa Requirements:</b>", styles['Normal']))
            story.append(Paragraph(visa_data.get("requirement", "No specific requirements available."), styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
            
            # Career Outlook
            story.append(Paragraph("<b>Career Outlook:</b>", styles['Normal']))
            story.append(Paragraph(visa_data.get("outlook", "Positive outlook with continued learning."), styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Footer
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(
            "<i>This report is generated by ExploraKodo Sensei Performance System.</i>",
            styles['Normal']
        ))
        
        # Build PDF
        doc.build(story)
        return output_path

    def run(self) -> str:
        """Generate performance report PDF."""
        if not REPORTLAB_AVAILABLE:
            return "Error: reportlab is required for PDF generation. Please install it with: pip install reportlab"
        
        try:
            # Calculate mastery scores
            mastery_scores = self._calculate_mastery_scores(self.candidate_id)
            
            # Determine output path
            if not self.output_path:
                reports_dir = Path(__file__).parent.parent.parent / "static" / "reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                output_path = reports_dir / f"sensei_report_{self.candidate_id}_{timestamp}.pdf"
            else:
                output_path = Path(self.output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate PDF
            pdf_path = self._generate_pdf_report(self.candidate_id, mastery_scores, str(output_path))
            
            return f"✅ Performance report generated successfully!\n\n📄 Report saved to: {pdf_path}\n\n📊 Summary:\n" + \
                   "\n".join([
                       f"  • {track}: {sum(skills.values())/len(skills):.1f}% average"
                       for track, skills in mastery_scores.items()
                   ])
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating performance report: {e}")
            return f"Error generating performance report: {str(e)}"
