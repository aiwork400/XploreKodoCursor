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
import datetime
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
    mastery_scores_override: dict | None = Field(
        default=None,
        description="Direct Data Injection: Pass mastery_scores directly to bypass database isolation. If provided, skips DB query."
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
        Identify the Source of Truth: Query curriculum_progress.mastery_scores directly.
        This matches sync_academic_record logic which writes to curriculum_progress.mastery_scores.
        
        Target Table: curriculum_progress
        Key: candidate_id (NOT student_id - confirmed in db_manager.py)
        Column: mastery_scores (JSON)
        """
        # Remove SQL Query Fallback: If mastery_scores_override is present, totally disable SQL queries
        # Check both Field value and attribute (Pydantic stores Field values as attributes)
        override = getattr(self, 'mastery_scores_override', None)
        if override is not None:
            print(f"CRITICAL DEBUG: Using direct data injection (bypassing DB query): {override}")
            print(f"CRITICAL DEBUG: SQL queries are DISABLED when mastery_scores_override is present")
            return override
        
        # Only execute SQL query if no override is provided
        print(f"CRITICAL DEBUG: No mastery_scores_override provided, falling back to SQL query")
        
        db: Session = SessionLocal()
        try:
            import json
            from sqlalchemy import text
            from sqlalchemy import inspect
            
            # Force Session Synchronization: Ensure database engine is connected
            try:
                # Test connection with a simple query
                test_query = text("SELECT 1")
                db.execute(test_query)
                db.commit()  # Ensure transaction is active
                print(f"CRITICAL DEBUG: Database connection verified for candidate_id={candidate_id}")
            except Exception as conn_error:
                print(f"CRITICAL DEBUG: Database connection failed: {conn_error}")
                import traceback
                traceback.print_exc()
                return {}
            
            # Fix ID Column Conflict: Use candidate_id (confirmed in db_manager.py line 95)
            # The 'Mastery' Path: Query curriculum_progress.mastery_scores exactly as dashboard does
            sql_query = text("""
                SELECT 
                    mastery_scores,
                    dialogue_history
                FROM curriculum_progress
                WHERE candidate_id = :candidate_id
            """)
            
            result_set = db.execute(sql_query, {"candidate_id": candidate_id})
            row = result_set.fetchone()
            
            if not row:
                print(f"CRITICAL DEBUG: Raw DB Result for PDF: No record found for candidate_id={candidate_id}")
                return {}
            
            raw_mastery_scores = row[0] if row else None
            raw_dialogue_history = row[1] if row and len(row) > 1 else None
            
            # Debug Logging (Crucial)
            print(f"CRITICAL DEBUG: Raw DB Result for PDF: mastery_scores={raw_mastery_scores}, dialogue_history_length={len(raw_dialogue_history) if raw_dialogue_history else 0}")
            
            # Source of Truth: Read from mastery_scores column (matches sync_academic_record)
            mastery_scores = raw_mastery_scores
            
            # Handle different data types (dict, string, None)
            if mastery_scores is None:
                print(f"CRITICAL DEBUG: mastery_scores is None, checking dialogue_history")
                # Fallback: Try to calculate from dialogue_history if mastery_scores is empty
                if raw_dialogue_history:
                    return self._calculate_from_dialogue_history(raw_dialogue_history, candidate_id)
                return {}
            elif isinstance(mastery_scores, str):
                try:
                    mastery_scores = json.loads(mastery_scores)
                except json.JSONDecodeError:
                    print(f"CRITICAL DEBUG: Failed to parse mastery_scores JSON string")
                    return {}
            elif not isinstance(mastery_scores, dict):
                print(f"CRITICAL DEBUG: mastery_scores is not a dict: {type(mastery_scores)}")
                return {}
            
            # Ensure structure matches sync_academic_record format
            valid_tracks = ["Food/Tech", "Academic", "Care-giving"]
            valid_skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
            
            result = {}
            for track in valid_tracks:
                track_data = mastery_scores.get(track, {})
                if isinstance(track_data, dict) and track_data:
                    result[track] = {}
                    for skill in valid_skills:
                        score = track_data.get(skill)
                        if score is not None:
                            result[track][skill] = float(score)
                        else:
                            result[track][skill] = None
                else:
                    result[track] = {}
            
            # Remove tracks with no data
            result = {
                track: {skill: score for skill, score in skills.items() if score is not None}
                for track, skills in result.items()
                if any(score is not None for score in skills.values())
            }
            
            print(f"CRITICAL DEBUG: Processed mastery_scores result: {result}")
            return result
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting mastery scores from curriculum_progress: {e}")
            print(f"CRITICAL DEBUG: Exception in _calculate_mastery_scores: {e}")
            import traceback
            traceback.print_exc()
            return {}
        finally:
            db.close()
    
    def _calculate_from_dialogue_history(self, dialogue_history, candidate_id: str) -> dict:
        """Fallback: Calculate from dialogue_history if mastery_scores is empty."""
        import json
        
        if isinstance(dialogue_history, str):
            try:
                dialogue_history = json.loads(dialogue_history)
            except json.JSONDecodeError:
                return {}
        
        if not isinstance(dialogue_history, list):
            return {}
        
        valid_tracks = ["Food/Tech", "Academic", "Care-giving"]
        valid_skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
        
        track_scores = {track: {skill: [] for skill in valid_skills} for track in valid_tracks}
        
        for entry in dialogue_history:
            category = entry.get("category")
            if category not in valid_tracks:
                continue
            
            scores = entry.get("scores", {})
            pillar_scores = scores.get("pillar_scores", {})
            
            for skill in valid_skills:
                if skill in pillar_scores:
                    track_scores[category][skill].append(float(pillar_scores[skill]))
        
        result = {}
        for track in valid_tracks:
            result[track] = {}
            for skill in valid_skills:
                skill_scores = track_scores[track][skill]
                if skill_scores:
                    result[track][skill] = sum(skill_scores) / len(skill_scores)
                else:
                    result[track][skill] = None
        
        return {
            track: {skill: score for skill, score in skills.items() if score is not None}
            for track, skills in result.items()
            if any(score is not None for score in skills.values())
        }

    def _generate_llm_assessment(self, track: str, skills: dict) -> str:
        """
        Sensei's Assessment: Make assessment dynamic based on scores.
        If score < 30%: suggest "Foundational Vocabulary focus"
        If score > 70%: say "Ready for Advanced Honorifics"
        """
        # Format scores for prompt
        vocab_score = float(skills.get("Vocabulary", 0.0)) if skills.get("Vocabulary") is not None else 0.0
        tone_score = float(skills.get("Tone/Honorifics", 0.0)) if skills.get("Tone/Honorifics") is not None else 0.0
        logic_score = float(skills.get("Contextual Logic", 0.0)) if skills.get("Contextual Logic") is not None else 0.0
        avg_score = (vocab_score + tone_score + logic_score) / 3.0 if (vocab_score + tone_score + logic_score) > 0 else 0.0
        
        # Sensei's Assessment: Dynamic recommendations based on scores
        assessment_parts = []
        
        if vocab_score < 30:
            assessment_parts.append("Foundational Vocabulary focus is recommended to build core language skills.")
        elif vocab_score > 70:
            assessment_parts.append("Strong vocabulary foundation demonstrates readiness for advanced content.")
        
        if tone_score < 30:
            assessment_parts.append("Politeness and formality require more practice with honorifics.")
        elif tone_score > 70:
            assessment_parts.append("Ready for Advanced Honorifics and nuanced communication.")
        
        if logic_score < 30:
            assessment_parts.append("Contextual understanding needs improvement through more practice sessions.")
        elif logic_score > 70:
            assessment_parts.append("Excellent contextual logic shows strong comprehension skills.")
        
        # Generate LLM assessment if available
        if GEMINI_AVAILABLE:
            try:
                prompt = f"""Given these performance scores for the {track} track:
- Vocabulary: {vocab_score}%
- Tone/Honorifics: {tone_score}%
- Contextual Logic: {logic_score}%

Key observations: {' '.join(assessment_parts) if assessment_parts else 'Overall performance needs improvement.'}

Write a professional 3-4 sentence detailed assessment EXCLUSIVELY in English for the Official Performance Report.

Be encouraging but honest. Focus on strengths and specific areas for improvement. Provide actionable feedback."""
                
                client = genai.Client(api_key=config.GEMINI_API_KEY)
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=prompt
                )
                
                text = response.text.strip()
                if text:
                    return text
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error generating LLM assessment: {e}")
        
        # Fallback: Dynamic assessment based on scores
        if assessment_parts:
            base_assessment = f"Student demonstrates {avg_score:.1f}% average mastery in {track}. "
            return base_assessment + " ".join(assessment_parts)
        else:
            return f"Student demonstrates {avg_score:.1f}% average mastery in {track}. Focus on areas scoring below 70% for improvement."

    def _create_bar_chart(self, mastery_scores: dict) -> Drawing:
        """
        Radar Data Feed: Create bar chart using MasteryScores from lesson_history query results.
        Ensures Page 1 chart is populated by lesson_history query, not hardcoded defaults.
        """
        tracks = list(mastery_scores.keys())
        skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
        
        # Radar Data Feed: Use exact same variables from lesson_history query [cite: 2025-12-21]
        # Prepare data - handle None values (no hardcoded 0.0)
        data = []
        track_names = []
        for track in tracks:
            track_skills = mastery_scores.get(track, {})
            track_data = []
            for skill in skills:
                score = track_skills.get(skill)
                # Use actual DB value or skip if None (no hardcoded fallback)
                if score is not None:
                    track_data.append(float(score))
                else:
                    # Skip tracks with missing data
                    track_data = None
                    break
            if track_data is not None and len(track_data) == len(skills):
                data.append(track_data)
                track_names.append(track)
        
        # Create drawing
        drawing = Drawing(400, 300)
        
        # Only create chart if we have data
        if data:
            # Create bar chart
            bc = VerticalBarChart()
            bc.x = 50
            bc.y = 50
            bc.width = 300
            bc.height = 200
            bc.data = data
            bc.categoryAxis.categoryNames = skills
            
            # Color mapping for tracks
            color_map = {
                "Care-giving": colors.HexColor('#1976D2'),
                "Academic": colors.HexColor('#388E3C'),
                "Food/Tech": colors.HexColor('#F57C00')
            }
            
            # Assign colors based on track order
            for i, track in enumerate(track_names):
                if i < len(bc.bars):
                    bc.bars[i].fillColor = color_map.get(track, colors.HexColor('#757575'))
            
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

    def _calculate_career_readiness(self, mastery_scores: dict) -> dict:
        """
        Implement Dynamic Readiness Scale: Calculate readiness based on average scores per track.
        < 10%: "Not Ready (Foundation Phase)"
        20% - 40%: "Early Readiness (N5 Path)"
        40% - 60%: "Developing (N4 Path)"
        60% - 80%: "Advanced Readiness (N3 Path)"
        80%+: "Sufficiently Ready (Professional)"
        """
        career_readiness = {}
        readiness_status = {}
        
        valid_tracks = ["Food/Tech", "Academic", "Care-giving"]
        for track in valid_tracks:
            skills = mastery_scores.get(track, {})
            if not skills:
                continue
            
            # Calculate average score for the track
            scores = [float(v) for v in skills.values() if v is not None]
            if not scores:
                continue
            
            avg_score = sum(scores) / len(scores)
            
            # Dynamic Readiness Scale
            if avg_score < 10:
                readiness_pct = 10.0
                status = "Not Ready (Foundation Phase)"
            elif avg_score < 20:
                readiness_pct = 20.0
                status = "Not Ready (Foundation Phase)"
            elif avg_score < 40:
                readiness_pct = 30.0
                status = "Early Readiness (N5 Path)"
            elif avg_score < 60:
                readiness_pct = 50.0
                status = "Developing (N4 Path)"
            elif avg_score < 80:
                readiness_pct = 70.0
                status = "Advanced Readiness (N3 Path)"
            else:
                readiness_pct = 90.0
                status = "Sufficiently Ready (Professional)"
            
            career_readiness[track] = readiness_pct
            readiness_status[track] = status
        
        # Store status for later use
        self._readiness_status = readiness_status
        return career_readiness

    def _generate_pdf_report(self, candidate_id: str, mastery_scores: dict, output_path: str, lesson_history: list = None) -> str:
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
        
        # Fix Vertical Layout: Constraint - Set topMargin=0.5*inch and bottomMargin=0.5*inch
        doc = SimpleDocTemplate(
            output_path, 
            pagesize=letter,
            topMargin=0.5*inch,  # Constraint: Fixed at 0.5*inch
            bottomMargin=0.5*inch,  # Constraint: Fixed at 0.5*inch
            leftMargin=0.75*inch,
            rightMargin=0.75*inch
        )
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
        
        # Report metadata - Use primitive datetime for Windows stability [cite: 2025-12-21]
        import datetime
        report_date_display = datetime.datetime.now().strftime("%B %d, %Y")
        # Static Header: Check report_date for None safety [cite: 2025-12-21]
        header_date = report_date_display if report_date_display else "Date Pending"
        story.append(Paragraph(f"<b>Student:</b> {candidate_name}", styles['Normal']))
        story.append(Paragraph(f"<b>Student ID:</b> {candidate_id}", styles['Normal']))
        story.append(Paragraph(f"<b>Report Date:</b> {header_date}", styles['Normal']))
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
        
        # Calculate overall scores per track - Radar & Table Sync: Use same DB values [cite: 2025-12-21]
        track_summary_data = [["Track", "Overall Score", "Status"]]
        valid_tracks = ["Food/Tech", "Academic", "Care-giving"]
        for track in valid_tracks:
            # Use exact DB values - no hardcoded defaults
            skills = mastery_scores.get(track, {}) if isinstance(mastery_scores, dict) else {}
            if isinstance(skills, dict) and skills:
                # Filter out None values
                valid_scores = [float(v) for v in skills.values() if v is not None]
                if not valid_scores:
                    continue  # Skip tracks with no data
                avg_score = sum(valid_scores) / len(valid_scores) if skills else 0.0
            else:
                avg_score = 0.0
            
            # Implement Dynamic Readiness Scale for Status column
            # Repair Last Page Layout: Handle null values - if not mastery_scores: total_avg = 0.0
            if not mastery_scores or not skills or avg_score == 0.0:
                status = "Not Ready (Foundation Phase)"
            elif avg_score < 10:
                status = "Not Ready (Foundation Phase)"
            elif avg_score < 20:
                status = "Not Ready (Foundation Phase)"
            elif avg_score < 40:
                status = "Early Readiness (N5 Path)"
            elif avg_score < 60:
                status = "Developing (N4 Path)"
            elif avg_score < 80:
                status = "Advanced Readiness (N3 Path)"
            else:
                status = "Sufficiently Ready (Professional)"
            
            # Wrapping: Force Status cell to use Paragraph for text wrapping
            status_para = Paragraph(status, ParagraphStyle(
                'StatusCell',
                parent=styles['Normal'],
                fontSize=8,
                leading=10,
                alignment=1,  # Center
                wordWrap='CJK'  # Enable word wrapping
            ))
            track_summary_data.append([track, f"{avg_score:.1f}%", status_para])
        
        # Fix Table Wrapping: Set explicit column widths and word wrap [cite: 2025-12-21]
        track_table = Table(track_summary_data, colWidths=[1.5*inch, 1*inch, 2.5*inch])
        track_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#002147')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (2, -1), 10),  # Default font size for data rows
            ('FONTSIZE', (2, 1), (2, -1), 8),  # Decrease Status column to 8pt
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('WORDWRAP', (0, 0), (-1, -1), True),  # Enable word wrap
        ]))
        story.append(track_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Detailed Performance by Track with LLM Assessment
        story.append(PageBreak())
        story.append(Paragraph("Detailed Performance by Track", heading_style))
        
        # Safe Get: Iterate through valid tracks only [cite: 2025-12-21]
        valid_tracks = ["Food/Tech", "Academic", "Care-giving"]
        for track in valid_tracks:
            # Safe Get: Default to empty dict if track is missing [cite: 2025-12-21]
            skills = mastery_scores.get(track, {}) if isinstance(mastery_scores, dict) else {}
            if not isinstance(skills, dict):
                skills = {}
            
            # Track header
            story.append(KeepTogether([
                Paragraph(f"<b>{track} Track</b>", styles['Heading3']),
                Spacer(1, 0.1*inch)
            ]))
            
            # Radar & Table Sync: Use exact same variables from database [cite: 2025-12-21]
            skill_data = [["Skill Category", "Mastery Score", "Level"]]
            valid_skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
            for skill in valid_skills:
                # Use exact DB value - no hardcoded fallbacks
                score = skills.get(skill)
                if score is None:
                    # Skip skills with no data (no hardcoded 0.0)
                    continue
                
                # Metric Display Sync: Ensure PDF table uses 100% scale metrics (0-100 range) [cite: 2025-12-21]
                score = float(score)
                # Clamp to 0-100 range to ensure consistency with Hub displays
                score = max(0.0, min(100.0, score))
                
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
            
            # Truncation: If Sensei's Assessment is longer than 400 characters, truncate it with ... to save vertical space
            if len(english_assessment) > 400:
                english_assessment = english_assessment[:400] + "..."
            
            story.append(Paragraph("<b>Sensei's Assessment:</b>", styles['Normal']))
            story.append(Paragraph(english_assessment, assessment_style))
            
            story.append(Spacer(1, 0.15*inch))  # Reduced spacing
        
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
        
        # Hard Page Breaks: Insert story.append(PageBreak()) immediately before the "Career & Visa Outlook" section
        # to ensure it never overlaps with the previous track's data
        story.append(PageBreak())  # Hard page break to prevent overlap
        story.append(Paragraph("Career & Visa Outlook", heading_style))
        story.append(Spacer(1, 0.15*inch))  # Reduced spacing
        
        # Determine JLPT level and Career Readiness for each track
        track_jlpt_levels = self._determine_jlpt_levels(mastery_scores)
        # Implement Dynamic Readiness Scale: Use mastery_scores directly
        track_career_readiness = self._calculate_career_readiness(mastery_scores)
        
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
        
        # Display Career Readiness and Visa Outlook for each track - Safe Get [cite: 2025-12-21]
        valid_tracks = ["Food/Tech", "Academic", "Care-giving"]
        for track in valid_tracks:
            # Safe Get: Default to empty dict if track is missing [cite: 2025-12-21]
            skills = mastery_scores.get(track, {}) if isinstance(mastery_scores, dict) else {}
            if not isinstance(skills, dict):
                skills = {}
            
            # Repair Last Page Layout: Handle null values - if not mastery_scores: total_avg = 0.0
            if not mastery_scores:
                total_avg = 0.0
                print(f"CRITICAL DEBUG: mastery_scores is empty for {track}, setting total_avg=0.0")
            elif not skills:
                total_avg = 0.0
                print(f"CRITICAL DEBUG: skills dict is empty for {track}, setting total_avg=0.0")
            else:
                # Ensure Career Readiness uses total_avg from query, not default
                valid_scores = [float(v) for v in skills.values() if v is not None]
                if not valid_scores:
                    total_avg = 0.0
                    print(f"CRITICAL DEBUG: No valid scores for {track}, setting total_avg=0.0")
                else:
                    total_avg = sum(valid_scores) / len(valid_scores)  # Use query result, not default
            
            jlpt_level = track_jlpt_levels.get(track, "N5") if isinstance(track_jlpt_levels, dict) else "N5"
            career_readiness = float(track_career_readiness.get(track, 0.0)) if isinstance(track_career_readiness, dict) else 0.0
            readiness_status = getattr(self, '_readiness_status', {}).get(track, "Not Ready (Foundation Phase)")
            
            # Debug: Verify total_avg is from query
            print(f"CRITICAL DEBUG: Career Readiness for {track}: total_avg={total_avg:.1f}% (from query), career_readiness={career_readiness:.1f}%")
            
            # Fix Career Readiness Page Layout: Use fixed height rows and strict leading to prevent overlapping
            # Force table to use fixed height for rows or use Paragraph with strict leading
            track_heading_style = ParagraphStyle(
                'TrackHeading',
                parent=styles['Heading3'],
                fontSize=14,
                leading=16,  # Strict leading (line spacing)
                spaceAfter=6,
                keepWithNext=True  # Keep heading with next paragraph
            )
            story.append(Paragraph(f"<b>{track} Track</b>", track_heading_style))
            story.append(Spacer(1, 0.08*inch))  # Reduced spacing
            
            # Career Readiness Progress Bar (visual representation) - Dynamic Readiness Scale
            # Use Paragraph with strict leading to prevent text from pushing content off page
            career_heading_style = ParagraphStyle(
                'CareerHeading',
                parent=styles['Normal'],
                fontSize=11,
                leading=13,  # Strict leading
                spaceAfter=4
            )
            story.append(Paragraph("<b>Career Readiness:</b>", career_heading_style))
            
            status_para_style = ParagraphStyle(
                'StatusPara',
                parent=styles['Normal'],
                fontSize=10,
                leading=12,  # Strict leading
                spaceAfter=4
            )
            story.append(Paragraph(f"<b>Status:</b> {readiness_status}", status_para_style))
            
            # Determine color based on readiness
            if career_readiness >= 100:
                bar_color = colors.HexColor('#4CAF50')  # Green
            elif career_readiness >= 66:
                bar_color = colors.HexColor('#FF9800')  # Orange
            else:
                bar_color = colors.HexColor('#F44336')  # Red
            
            # Progress text with JLPT level - use strict leading
            progress_text = f"{career_readiness:.0f}% (JLPT {jlpt_level})"
            progress_style = ParagraphStyle(
                'ProgressText',
                parent=styles['Normal'],
                fontSize=11,
                leading=13,  # Strict leading
                textColor=bar_color,
                fontName='Helvetica-Bold',
                spaceAfter=6
            )
            story.append(Paragraph(progress_text, progress_style))
            
            # Visual progress bar using table with colored cells - fixed height
            progress_bar_width = 4.5 * inch
            bar_cells = 20  # 20 cells for 5% increments
            filled_cells = int(career_readiness / 5)
            fixed_bar_height = 0.12*inch  # Fixed height to prevent expansion
            
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
                        ('TOPPADDING', (0, 0), (0, 0), 2),
                        ('BOTTOMPADDING', (0, 0), (0, 0), 2),
                    ])
                    progress_cells.append(Table([['']], colWidths=[progress_bar_width / bar_cells], rowHeights=[fixed_bar_height]))
                    progress_cells[-1].setStyle(cell_style)
                else:
                    # Empty cell
                    cell_style = TableStyle([
                        ('BACKGROUND', (0, 0), (0, 0), colors.lightgrey),
                        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (0, 0), 0),
                        ('RIGHTPADDING', (0, 0), (0, 0), 0),
                        ('TOPPADDING', (0, 0), (0, 0), 2),
                        ('BOTTOMPADDING', (0, 0), (0, 0), 2),
                    ])
                    progress_cells.append(Table([['']], colWidths=[progress_bar_width / bar_cells], rowHeights=[fixed_bar_height]))
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
            story.append(Spacer(1, 0.1*inch))  # Reduced spacing
            
            # Visa Requirements - use Paragraph with strict leading
            visa_data = visa_info.get(track, {})
            visa_heading_style = ParagraphStyle(
                'VisaHeading',
                parent=styles['Normal'],
                fontSize=11,
                leading=13,  # Strict leading
                spaceAfter=4
            )
            story.append(Paragraph("<b>Visa Requirements:</b>", visa_heading_style))
            
            visa_text_style = ParagraphStyle(
                'VisaText',
                parent=styles['Normal'],
                fontSize=10,
                leading=12,  # Strict leading - prevents text from pushing content off page
                spaceAfter=6
            )
            story.append(Paragraph(visa_data.get("requirement", "No specific requirements available."), visa_text_style))
            story.append(Spacer(1, 0.08*inch))  # Reduced spacing
            
            # Career Outlook - use Paragraph with strict leading
            outlook_heading_style = ParagraphStyle(
                'OutlookHeading',
                parent=styles['Normal'],
                fontSize=11,
                leading=13,  # Strict leading
                spaceAfter=4
            )
            story.append(Paragraph("<b>Career Outlook:</b>", outlook_heading_style))
            
            outlook_text_style = ParagraphStyle(
                'OutlookText',
                parent=styles['Normal'],
                fontSize=10,
                leading=12,  # Strict leading - prevents text from pushing content off page
                spaceAfter=6
            )
            story.append(Paragraph(visa_data.get("outlook", "Positive outlook with continued learning."), outlook_text_style))
            story.append(Spacer(1, 0.15*inch))  # Reduced spacing between tracks
        
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
        # Use Primitive Datetime: Remove timezone dependency for Windows sub-process stability [cite: 2025-12-21]
        import datetime
        report_date = None
        report_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not REPORTLAB_AVAILABLE:
            return "Error: reportlab is required for PDF generation. Please install it with: pip install reportlab"
        
        try:
            # Remove SQL Query Fallback: If mastery_scores_override is present, totally disable SQL queries
            override = getattr(self, 'mastery_scores_override', None)
            if override is not None:
                print(f"CRITICAL DEBUG: Using direct data injection in run() method: {override}")
                print(f"CRITICAL DEBUG: SQL queries are DISABLED in run() when mastery_scores_override is present")
                mastery_scores = override
            else:
                # Only calculate from database if no override is provided
                print(f"CRITICAL DEBUG: No mastery_scores_override in run(), falling back to _calculate_mastery_scores()")
                mastery_scores = self._calculate_mastery_scores(self.candidate_id)
            
            # Repair PDF Generation: Load lesson_history from user_progress.json [cite: 2025-12-21]
            # Remove word_count calculations and use lesson_history exclusively
            # PDF Report "Real Data" Injection: Use same track filter as Radar Chart [cite: 2025-12-21]
            lesson_history = []
            try:
                import json
                progress_file = Path(__file__).parent.parent.parent / "assets" / "user_progress.json"
                if progress_file.exists():
                    with open(progress_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        lesson_history = data.get("lesson_history", [])
                        
                        # Filter by valid tracks (same as Radar Chart)
                        valid_tracks = ["Academic", "Food/Tech", "Care-giving"]
                        lesson_history = [
                            entry for entry in lesson_history
                            if entry.get("category") in valid_tracks
                        ]
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Could not load lesson_history: {e}")
            
            # PDF Report "Real Data" Injection: Debug print [cite: 2025-12-21]
            # Get student name for debug
            try:
                from database.db_manager import Candidate, SessionLocal
                db = SessionLocal()
                try:
                    candidate = db.query(Candidate).filter(Candidate.candidate_id == self.candidate_id).first()
                    student_name = candidate.name if candidate else self.candidate_id
                finally:
                    db.close()
            except:
                student_name = self.candidate_id
            
            print(f"DEBUG: PDF generating for {student_name} with {len(lesson_history)} records")
            
            # PDF Data Guard: Check if lesson_history is empty [cite: 2025-12-21]
            if not lesson_history:
                return "⚠️ No session data found. Please complete a session first before generating a report."
            
            # Standardize PDF Output: Use tempfile to prevent Windows file locking [cite: 2025-12-21]
            import tempfile
            import shutil
            
            # Determine output path
            if not self.output_path:
                # Use tempfile to prevent Windows file locking
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix=f"sensei_report_{self.candidate_id}_")
                output_path = temp_file.name
                temp_file.close()
            else:
                output_path = Path(self.output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path = str(output_path)
            
            # Generate PDF with lesson_history data
            pdf_path = self._generate_pdf_report(self.candidate_id, mastery_scores, output_path, lesson_history)
            
            return f"✅ Performance report generated successfully!\n\n📄 Report saved to: {pdf_path}\n\n📊 Summary:\n" + \
                   "\n".join([
                       f"  • {track}: {sum(skills.values())/len(skills):.1f}% average"
                       for track, skills in mastery_scores.items()
                   ])
            
        except Exception as e:
            # Traceback Safety: Ensure except block doesn't reference variables that might not exist [cite: 2025-12-21]
            import traceback
            import logging
            try:
                error_traceback = traceback.format_exc()
                error_message = f"Error generating performance report: {str(e)}\n\nFull traceback:\n{error_traceback}"
                logger = logging.getLogger(__name__)
                logger.error(error_message)
                return error_message
            except Exception as fallback_error:
                # Error Handling: Use primitive datetime instead of timezone to prevent crashes [cite: 2025-12-21]
                try:
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    return f"Error generating performance report: {str(e)}. Additional error in error handler: {str(fallback_error)} [Timestamp: {timestamp}]"
                except:
                    # Ultimate fallback - no datetime imports at all
                    return f"Error generating performance report: {str(e)}. Additional error in error handler: {str(fallback_error)}"


# Fix PDF Sub-process Error: Ensure multiprocessing logic is wrapped in if __name__ == "__main__" [cite: 2025-12-21]
# Note: The ReportGenerator class is already initialized inside the function call (in dashboard/app.py),
# not at module level, which prevents "pickling" errors during Uvicorn reload.
if __name__ == "__main__":
    # Only run multiprocessing code if this module is executed directly
    # When imported as a module (e.g., by Uvicorn), this block is skipped
    pass
