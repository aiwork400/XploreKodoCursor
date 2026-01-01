"""
ExploraKodo Global Command Center - Streamlit Dashboard

Provides:
- Candidate View: Searchable list with Travel-Ready status and JLPT progress
- Wisdom Hub: Latest Markdown reports from OperationsAgent
- Live Simulator: Chat interface for testing Socratic Sensei
- Financial Ledger: Summary of fees collected
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import os
import base64
import json
import logging
import pandas as pd
import streamlit as st
from datetime import datetime, timezone
from sqlalchemy import or_, text
from sqlalchemy.orm import Session
import time
from agency.training_agent.competency_grading_tool import CompetencyGradingTool
from agency.training_agent.video_socratic_assessment_tool import VideoSocraticAssessmentTool


try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    go = None
    px = None

import config

# Configure logger
logger = logging.getLogger(__name__)
from database.db_manager import Candidate, CurriculumProgress, Payment, DocumentVault, SessionLocal, StudentPerformance
try:
    from models.curriculum import Syllabus
    SYLLABUS_AVAILABLE = True
except ImportError:
    SYLLABUS_AVAILABLE = False
    Syllabus = None

# Try to import GetCurrentPhase for phase visualization
try:
    from agency.student_progress_agent.tools import GetCurrentPhase
    PHASE_TOOL_AVAILABLE = True
except ImportError:
    PHASE_TOOL_AVAILABLE = False
    GetCurrentPhase = None

# Page configuration
st.set_page_config(
    page_title="ExploraKodo Global Command Center",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load Custom CSS
css_path = Path(__file__).parent.parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f'<style>{{f.read()}}</style>', unsafe_allow_html=True)
else:
    # Fallback CSS if file doesn't exist
    st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
            color: #002147;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_db_session() -> Session:
    """Get database session."""
    return SessionLocal()


def load_candidates(search_term: str = "", status_filter: str = "All", track_filter: str = "All") -> pd.DataFrame:
    """Load candidates from database with filters."""
    db = get_db_session()
    try:
        query = db.query(
            Candidate.candidate_id,
            Candidate.full_name,
            Candidate.track,
            Candidate.status,
            Candidate.travel_ready,
            Candidate.has_150_hour_study_certificate,
            Candidate.has_financial_sponsor_docs,
            Candidate.has_jlpt_n4_or_n5,
            Candidate.has_kaigo_skills_test,
            Candidate.created_at,
        )

        # Apply filters
        if status_filter != "All":
            query = query.filter(Candidate.status == status_filter)
        if track_filter != "All":
            query = query.filter(Candidate.track == track_filter)
        if search_term:
            query = query.filter(
                or_(
                    Candidate.candidate_id.ilike(f"%{search_term}%"),
                    Candidate.full_name.ilike(f"%{search_term}%")
                )
            )

        candidates = query.all()

        # Get curriculum progress for each candidate
        data = []
        for candidate in candidates:
            curriculum = (
                db.query(CurriculumProgress)
                .filter(CurriculumProgress.candidate_id == candidate.candidate_id)
                .first()
            )

            jlpt_n5_progress = 0
            jlpt_n4_progress = 0
            jlpt_n3_progress = 0

            if curriculum:
                jlpt_n5_progress = (
                    (curriculum.jlpt_n5_units_completed / curriculum.jlpt_n5_total_units * 100)
                    if curriculum.jlpt_n5_total_units > 0
                    else 0
                )
                jlpt_n4_progress = (
                    (curriculum.jlpt_n4_units_completed / curriculum.jlpt_n4_total_units * 100)
                    if curriculum.jlpt_n4_total_units > 0
                    else 0
                )
                jlpt_n3_progress = (
                    (curriculum.jlpt_n3_units_completed / curriculum.jlpt_n3_total_units * 100)
                    if curriculum.jlpt_n3_total_units > 0
                    else 0
                )

            data.append(
                {
                    "Candidate ID": candidate.candidate_id,
                    "Full Name": candidate.full_name,
                    "Track": candidate.track.title(),
                    "Status": candidate.status,
                    "Travel-Ready": "✓" if candidate.travel_ready else "✗",
                    "JLPT N5 Progress": f"{jlpt_n5_progress:.1f}%",
                    "JLPT N4 Progress": f"{jlpt_n4_progress:.1f}%",
                    "JLPT N3 Progress": f"{jlpt_n3_progress:.1f}%",
                    "Created": candidate.created_at.strftime("%Y-%m-%d") if candidate.created_at else "N/A",
                }
            )

        return pd.DataFrame(data)
    except Exception as e:
        # Return empty DataFrame with error info
        error_msg = str(e)
        if "password authentication failed" in error_msg.lower():
            st.error("""
            **Database Connection Error: Password Authentication Failed**
            
            The dashboard cannot connect to PostgreSQL. Please check your database credentials.
            
            **To fix this:**
            1. Create or update your `.env` file in the project root
            2. Add the correct DATABASE_URL:
               ```
               DATABASE_URL=postgresql://username:password@localhost:5432/xplorekodo
               ```
            3. Replace `username` and `password` with your PostgreSQL credentials
            4. Ensure PostgreSQL is running and the database `xplorekodo` exists
            
            **Current connection string:** `{}`
            """.format(config.DATABASE_URL))
        elif "could not connect" in error_msg.lower() or "connection refused" in error_msg.lower():
            st.error("""
            **Database Connection Error: Cannot Connect to PostgreSQL**
            
            The dashboard cannot reach the PostgreSQL server.
            
            **To fix this:**
            1. Ensure PostgreSQL is running
            2. Check that PostgreSQL is listening on port 5432
            3. Verify your DATABASE_URL in `.env` file
            """)
        else:
            st.error(f"**Database Error:** {error_msg}")
        return pd.DataFrame()  # Return empty DataFrame
    finally:
        db.close()


def load_wisdom_reports() -> list[Path]:
    """Load latest wisdom reports from OperationsAgent."""
    reports_dir = Path(__file__).parent.parent / "operations" / "reports"
    if not reports_dir.exists():
        return []

    # Get all markdown reports, sorted by modification time (newest first)
    reports = sorted(reports_dir.glob("wisdom_report_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports


def load_financial_summary() -> dict:
    """Load financial summary from payments table."""
    db = get_db_session()
    try:
        # Total fees collected (successful payments only)
        total_query = text(
            """
            SELECT 
                COUNT(*) as total_payments,
                SUM(CAST(amount AS DECIMAL)) as total_amount,
                COUNT(DISTINCT candidate_id) as unique_candidates
            FROM payments
            WHERE status = 'success'
            """
        )
        result = db.execute(total_query).fetchone()

        total_payments = result[0] if result else 0
        total_amount = float(result[1]) if result and result[1] else 0.0
        unique_candidates = result[2] if result else 0

        # Payments by provider
        provider_query = text(
            """
            SELECT 
                provider,
                COUNT(*) as count,
                SUM(CAST(amount AS DECIMAL)) as amount
            FROM payments
            WHERE status = 'success'
            GROUP BY provider
            """
        )
        provider_results = db.execute(provider_query).fetchall()

        provider_breakdown = {}
        for provider, count, amount in provider_results:
            provider_breakdown[provider] = {"count": count, "amount": float(amount) if amount else 0.0}

        # Recent payments (last 10)
        recent_query = text(
            """
            SELECT 
                candidate_id,
                amount,
                currency,
                provider,
                status,
                created_at
            FROM payments
            ORDER BY created_at DESC
            LIMIT 10
            """
        )
        recent_payments = db.execute(recent_query).fetchall()

        return {
            "total_payments": total_payments,
            "total_amount": total_amount,
            "unique_candidates": unique_candidates,
            "provider_breakdown": provider_breakdown,
            "recent_payments": recent_payments,
        }
    except Exception as e:
        # Return empty summary on error
        return {
            "total_payments": 0,
            "total_amount": 0.0,
            "unique_candidates": 0,
            "provider_breakdown": {},
            "recent_payments": [],
            "error": str(e),
        }
    finally:
        db.close()


# Concierge Widget Functions
def render_concierge_avatar(talking: bool = False, show_intro_video: bool = False, intro_video_bytes: bytes | None = None):
    """
    Render the 2D Sensei Avatar in the sidebar using native Streamlit toggle.
    Pure Python implementation - no JavaScript.
    
    Args:
        talking: Whether the avatar should show talking state
        show_intro_video: If True, show intro video instead of static avatar
        intro_video_bytes: Video bytes to display if show_intro_video is True
    """
    import time
    
    # Initialize avatar talking state
    if "concierge_avatar_talking" not in st.session_state:
        st.session_state.concierge_avatar_talking = False
    
    # Use session state talking status
    if talking:
        st.session_state.concierge_avatar_talking = True
    
    # Show intro video if requested (first time widget is activated)
    # Video rendering is handled inside show_concierge_widget() sidebar block
    # This function only handles static avatar rendering
    pass
    
    # THE 'IS SPEAKING' LOGIC: Determine which image to show
    # Check if temp_voice.mp3 was modified in the last 10 seconds
    temp_audio_path = Path(__file__).parent.parent.resolve() / "static" / "audio" / "temp_voice.mp3"
    file_recently_modified = False
    if temp_audio_path.exists():
        try:
            file_mtime = temp_audio_path.stat().st_mtime
            time_since_modification = time.time() - file_mtime
            # File was modified in the last 10 seconds
            if time_since_modification < 10.0:
                file_recently_modified = True
        except Exception as e:
            logger.warning(f"Could not check file modification time: {e}")
    
    # is_talking_state is True if:
    # 1. st.session_state.concierge_avatar_talking is True OR
    # 2. The temp_voice.mp3 file was modified in the last 10 seconds
    is_talking_state = st.session_state.concierge_avatar_talking or file_recently_modified
    
    # ASSET GENERATION: Base64-encoded SVG images
    # IDLE_SVG: Closed mouth, calm expression
    IDLE_SVG = base64.b64encode("""
    <svg width=\"250\" height=\"250\" xmlns=\"http://www.w3.org/2000/svg\">
        <defs>
            <linearGradient id=\"bgGrad\" x1=\"0%\" y1=\"0%\" x2=\"100%\" y2=\"100%\">
                <stop offset=\"0%\" style=\"stop-color:#667eea;stop-opacity:1\" />
                <stop offset=\"100%\" style=\"stop-color:#764ba2;stop-opacity:1\" />
            </linearGradient>
        </defs>
        <rect width=\"250\" height=\"250\" fill=\"url(#bgGrad)"/>
        <circle cx=\"125\" cy=\"100\" r=\"60\" fill=\"#ffdbac\" stroke=\"#d4a574\" stroke-width=\"2"/>
        <circle cx=\"105\" cy=\"90\" r=\"6\" fill=\"#000"/>
        <circle cx=\"145\" cy=\"90\" r=\"6\" fill=\"#000"/>
        <path d=\"M 95 75 L 110 80 L 140 80 L 155 75\" stroke=\"#000\" stroke-width=\"3\" fill=\"none"/>
        <path d=\"M 110 120 Q 125 130 140 120\" stroke=\"#000\" stroke-width=\"3\" fill=\"none"/>
        <text x=\"125\" y=\"200\" font-family=\"Arial\" font-size=\"20\" font-weight=\"bold\" fill=\"white\" text-anchor=\"middle\">Sensei</text>
    </svg>
    """.encode('utf-8')).decode('utf-8')
    
    # TALKING_GIF_SVG: Open mouth, animated expression (medium size for talking)
    TALKING_GIF_SVG = base64.b64encode("""
    <svg width=\"250\" height=\"250\" xmlns=\"http://www.w3.org/2000/svg\">
        <defs>
            <linearGradient id=\"bgGrad2\" x1=\"0%\" y1=\"0%\" x2=\"100%\" y2=\"100%\">
                <stop offset=\"0%\" style=\"stop-color:#667eea;stop-opacity:1\" />
                <stop offset=\"100%\" style=\"stop-color:#764ba2;stop-opacity:1\" />
            </linearGradient>
        </defs>
        <rect width=\"250\" height=\"250\" fill=\"url(#bgGrad2)"/>
        <circle cx=\"125\" cy=\"100\" r=\"60\" fill=\"#ffdbac\" stroke=\"#d4a574\" stroke-width=\"2"/>
        <circle cx=\"105\" cy=\"90\" r=\"6\" fill=\"#000"/>
        <circle cx=\"145\" cy=\"90\" r=\"6\" fill=\"#000"/>
        <path d=\"M 95 75 L 110 80 L 140 80 L 155 75\" stroke=\"#000\" stroke-width=\"3\" fill=\"none"/>
        <ellipse cx=\"125\" cy=\"120\" rx=\"18\" ry=\"12\" fill=\"#000"/>
        <text x=\"125\" y=\"200\" font-family=\"Arial\" font-size=\"20\" font-weight=\"bold\" fill=\"white\" text-anchor=\"middle\">Sensei</text>
    </svg>
    """.encode('utf-8')).decode('utf-8')
    
    # Create data URIs
    IDLE_IMAGE = f"data:image/svg+xml;base64,{IDLE_SVG}"
    TALKING_IMAGE = f"data:image/svg+xml;base64,{TALKING_GIF_SVG}"
    
    # Container with professional styling
    status_text = "🗣️ Talking" if is_talking_state else "😌 Idle"
    st.sidebar.markdown(
        f"""
        <div class="concierge-avatar-container" style="margin: 10px 0; border-radius: 10px; overflow: hidden; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 10px;">
            <div style="text-align: center; color: white; font-size: 12px; margin-bottom: 5px;">
                {status_text} • Sensei
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # AUDIO-FIRST RENDERING: Place audio above the image
    if "concierge_audio_output" in st.session_state and st.session_state.concierge_audio_output:
        # AUDIO HANDSHAKE: Use unique key to force re-render and autoplay
        audio_key = f"audio_{int(time.time() * 1000)}"
        st.sidebar.markdown("**🔊 Audio Response:**")
        st.sidebar.audio(
            st.session_state.concierge_audio_output,
            format="audio/mp3",
            autoplay=True,
            muted=False,
            key=audio_key
        )
        st.sidebar.caption("💡 Audio is set to autoplay. If it doesn't play automatically, click the play button above.")
        st.sidebar.markdown("---")
    
    # NATIVE TOGGLE: Simple st.image() call based on state
    # Use is_talking_state which includes file modification check
    if is_talking_state:
        # Show talking image
        st.sidebar.image(
            TALKING_IMAGE,
            caption=None,
            width=250,
            clamp=False,
            channels="RGB",
            output_format="auto"
        )
    else:
        # Show idle image
        st.sidebar.image(
            IDLE_IMAGE,
            caption=None,
            width=250,
            clamp=False,
            channels="RGB",
            output_format="auto"
        )


def show_concierge_widget():
    """Display the ExploraKodo Concierge Widget - floating sidebar assistant."""
    # HARD-OVERRIDE: Wrap the entire Concierge UI in a strict sidebar block
    with st.sidebar:
        st.header("ExploraKodo Concierge")
        
        # Initialize session state for concierge (concierge_avatar_visible already initialized in main())
        if "concierge_language" not in st.session_state:
            st.session_state.concierge_language = "en"
        if "concierge_messages" not in st.session_state:
            st.session_state.concierge_messages = []
        if "pending_user_input" not in st.session_state:
            st.session_state.pending_user_input = None
        if "concierge_avatar_talking" not in st.session_state:
            st.session_state.concierge_avatar_talking = False
        if "concierge_audio_output" not in st.session_state:
            st.session_state.concierge_audio_output = None
        
        # Language Selector - Moved to top for video-language sync
        language_options = {
            'en': '🇺🇸 English',
            'ja': '🇯🇵 日本語',
            'ne': '🇳🇵 नेपाली'
        }
        
        selected_lang = st.selectbox(
            "🌐 Language",
            options=list(language_options.keys()),
            format_func=lambda x: language_options[x],
            key="concierge_lang_select",
            index=list(language_options.keys()).index(st.session_state.concierge_language) if st.session_state.concierge_language in language_options else 0
        )
        st.session_state.concierge_language = selected_lang
        
        # Map language code to full name for video selection
        lang_name_map = {'en': 'us English', 'ja': 'Japanese', 'ne': 'Nepali'}
        st.session_state.language = lang_name_map.get(selected_lang, 'us English')
        
        # Avatar Toggle - Use checkbox without manually updating state (widget handles it)
        st.checkbox("Show Avatar", key="concierge_avatar_visible")
        
        # Video rendering - ONLY if Show Avatar is checked
        # Re-render on Change: When language changes, lang_map immediately updates v_file so video refreshes
        if st.session_state.concierge_avatar_visible:
            # Pick ONLY the correct language file using lang_map (no looping)
            # Use current language state which updates immediately when selector changes
            lang_map = {'us English': 'intro_en.mp4', 'Japanese': 'intro_jp.mp4', 'Nepali': 'intro_ne.mp4'}
            current_lang = st.session_state.get('language', 'us English')
            v_file = lang_map.get(current_lang, 'intro_en.mp4')
            
            # Force layout inside sidebar with explicit height/width
            video_path = Path(__file__).parent.parent / "assets" / "videos" / "intro" / v_file
            if video_path.exists():
                # Welcome Video header only visible if avatar is checked
                st.markdown("### 🎬 Welcome Video")
                video_html = f'''<video width="100%" height="250" controls style="object-fit: cover; border-radius: 10px;">
                                 <source src="data:video/mp4;base64,{base64.b64encode(video_path.read_bytes()).decode()}" type="video/mp4">
                                 </video>'''
                st.components.v1.html(video_html, height=260)
            else:
                st.info(f"Video file not found: {v_file}")
        
        st.markdown("---")
        
        # Display conversation history
        if st.session_state.concierge_messages:
            st.markdown("**💬 Conversation History:**")
            for msg in st.session_state.concierge_messages[-5:]:
                if msg["role"] == "user":
                    with st.expander(f"**You:** {msg['content'][:60]}...", expanded=False):
                        st.markdown(msg['content'])
                else:
                    with st.expander(f"**🤖 Concierge:** {msg['content'][:60]}...", expanded=True):
                        st.markdown(msg['content'])
        
        st.markdown("---")
        
        # Hybrid Input: Chat + Mic Recorder - ALWAYS VISIBLE
        st.markdown("**💬 Ask the Concierge:**")
        input_method = st.radio(
            "Input Method",
            ["💬 Text", "🎤 Voice"],
            key="concierge_input_method",
            horizontal=True
        )
        
        user_input = None
        
        if input_method == "💬 Text":
            # Text input - use text_input with a send button (chat_input doesn't work in sidebar)
            text_input = st.text_input(
                "Type your message:",
                key="concierge_text_input",
                placeholder="Ask me anything about ExploraKodo..."
            )
            send_button = st.button("📤 Send", key="concierge_send_text", type="primary")
            if send_button and text_input:
                user_input = text_input
            elif send_button and not text_input:
                st.warning("⚠️ Please enter a message before sending.")
        else:
            # Voice input using streamlit-mic-recorder
            st.markdown("**🎤 Voice Recording:**")
            
            # Initialize recording state
            if "recorded_audio" not in st.session_state:
                st.session_state.recorded_audio = None
            
            try:
                from streamlit_mic_recorder import mic_recorder
                
                # Place mic_recorder in sidebar - this should render the button in the sidebar
                st.markdown("Click the button below to start recording:")
                audio_data = mic_recorder(
                    key="concierge_voice_recorder",
                    start_prompt="🎤 Start Recording",
                    stop_prompt="⏹️ Stop Recording",
                    just_once=False,
                )
                
                # If mic_recorder returns data, store it
                if audio_data:
                    st.session_state.recorded_audio = audio_data
                
            except ImportError:
                st.warning("⚠️ streamlit-mic-recorder not installed")
                st.code("pip install streamlit-mic-recorder")
                audio_data = None
            except Exception as e:
                st.warning(f"⚠️ Mic recorder error: {str(e)}")
                audio_data = None
                # Show fallback text input on error
                st.markdown("---")
                st.info("💡 Voice recording unavailable. Please use text input instead.")
                fallback_text = st.text_input("Type your message:", key="concierge_voice_fallback")
                if fallback_text:
                    user_input = fallback_text
            
            # Use recorded audio
            final_audio = st.session_state.recorded_audio if st.session_state.recorded_audio else audio_data
            
            if final_audio:
                st.markdown("---")
                st.success("✅ Recording complete! Listen to your recording:")
                
                # Playback audio - make it prominent
                # Handle both dict format (from mic_recorder) and direct bytes
                audio_bytes_for_playback = final_audio.get("bytes") if isinstance(final_audio, dict) else final_audio
                if audio_bytes_for_playback:
                    # Ensure it's bytes, not base64 string
                    if isinstance(audio_bytes_for_playback, str):
                        audio_bytes_for_playback = base64.b64decode(audio_bytes_for_playback)
                    st.audio(audio_bytes_for_playback, format="audio/wav", autoplay=False)
                    st.caption("🔊 Click the play button above to hear your recording")
                else:
                    st.warning("⚠️ Audio playback not available, but you can still send it for transcription.")
                
                # Show options
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Record Again", key="record_again_btn"):
                        st.session_state.recorded_audio = None
                        st.rerun()
                
                with col2:
                    send_voice_btn = st.button("📤 Send Voice", key="concierge_send_voice", type="primary")
                
                # Process voice input when Send is clicked
                if send_voice_btn:
                    st.info("🎤 Transcribing your voice...")
                    # Get audio bytes - handle both dict and bytes format
                    audio_bytes_for_transcription = final_audio.get("bytes") if isinstance(final_audio, dict) else final_audio
                    if not audio_bytes_for_transcription:
                        st.error("Error: No audio data found. Please record again.")
                    else:
                        # Ensure it's bytes, not base64 string
                        if isinstance(audio_bytes_for_transcription, str):
                            audio_bytes_for_transcription = base64.b64decode(audio_bytes_for_transcription)
                        
                        transcribed = process_concierge_voice(
                            audio_bytes_for_transcription,
                            st.session_state.concierge_language
                        )
                        if transcribed and not transcribed.startswith("Error"):
                            st.success(f"✅ Transcribed: \"{transcribed}\"" )
                            # Store transcribed text for processing
                            st.session_state.pending_user_input = transcribed
                            # Clear recorded audio after processing
                            st.session_state.recorded_audio = None
                            st.rerun()  # Rerun to process the transcribed text
                        elif transcribed and transcribed.startswith("Error"):
                            st.error(transcribed)
                            st.info("💡 Tip: Make sure you're speaking clearly and your microphone is working. You can also type your message below.")
            else:
                st.caption("💡 Click the microphone button above to start recording.")
            
            # Fallback text input if no audio recorded
            if not final_audio:
                st.markdown("---")
                fallback_input = st.text_input("Or type your message:", key="concierge_fallback_input")
                if fallback_input:
                    user_input = fallback_input
        
        # Check for pending input from voice transcription
        if "pending_user_input" in st.session_state and st.session_state.pending_user_input:
            user_input = st.session_state.pending_user_input
            del st.session_state.pending_user_input
        
        # Process user input
        if user_input and user_input.strip():
            # Add user message
            st.session_state.concierge_messages.append({
                "role": "user",
                "content": user_input
            })
            
            # Get response from SupportAgent with loading indicator
            # STATE LOGIC: Set avatar to talking while generating response
            st.session_state.concierge_avatar_talking = True
            st.info("🤖 Thinking...")
            try:
                response = get_concierge_response(user_input.strip(), st.session_state.concierge_language)
                
                # Add assistant message
                st.session_state.concierge_messages.append({
                    "role": "assistant",
                    "content": response
                })
                
                # Display response prominently (will be shown in conversation history after rerun)
                st.success("✅ Response generated!")
                st.markdown("---")
                st.markdown("**🤖 Concierge Response:**")
                st.markdown(response)
                st.markdown("---")
                
                # TEXT-TO-VOICE TRIGGER: Generate TTS audio for both text and voice input
                # This ensures the avatar talking animation is triggered
                # AUDIO SYNC: Always generate audio, even in Text mode, to trigger isTalking animation
                st.info("🔊 Generating audio...")
                audio_output = generate_trilingual_tts(response, st.session_state.concierge_language)
                if audio_output:
                    # ROBUST FILE WRITING: Save audio as temp_voice.mp3 using absolute path
                    import os
                    import time
                    
                    # Use absolute path to ensure file is written correctly
                    project_root = Path(__file__).parent.parent.resolve()
                    temp_audio_path = project_root / "static" / "audio" / "temp_voice.mp3"
                    temp_audio_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write file
                    try:
                        with open(temp_audio_path, "wb") as f:
                            f.write(audio_output)
                            f.flush()  # Force write to disk
                            os.fsync(f.fileno())  # Ensure OS has written to disk
                    except Exception as e:
                        logger.error(f"Failed to write audio file: {e}")
                        st.error(f"❌ Failed to save audio file: {e}")
                    
                    # ROBUST FILE WRITING: Verify file was created
                    if not temp_audio_path.exists():
                        logger.error('CRITICAL: Audio file not created!')
                        st.error("❌ CRITICAL: Audio file not created! TTS may have failed.")
                    elif temp_audio_path.stat().st_size == 0:
                        logger.error('CRITICAL: Audio file is 0 bytes!')
                        st.error("❌ CRITICAL: Audio file is 0 bytes! TTS generation may have failed.")
                    else:
                        logger.info(f"Audio file created successfully: {temp_audio_path} ({temp_audio_path.stat().st_size} bytes)")
                    
                    # AUDIO PATH VERIFICATION: Wait for file to be fully written and closed
                    time.sleep(0.5)  # Ensure file is closed before Streamlit tries to play it
                    
                    # Generate unique audio ID for this response
                    import uuid
                    audio_id = f"concierge_audio_{uuid.uuid4().hex[:8]}"
                    
                    # Set avatar talking state
                    st.session_state.concierge_avatar_talking = True
                    
                    # PATH SYNC: Get relative path for Streamlit static file serving
                    # Streamlit serves files from static/ directory at /static/ URL
                    # Add timestamp to prevent caching issues
                    timestamp = int(time.time())
                    audio_url = f"/static/audio/temp_voice.mp3?t={timestamp}"
                    
                    # Store audio URL and absolute path in session state
                    st.session_state.concierge_audio_url = audio_url
                    st.session_state.concierge_audio_path = str(temp_audio_path)
                    
                    # Fallback: base64 data URI in case static file serving has issues
                    audio_base64 = base64.b64encode(audio_output).decode('utf-8')
                    audio_data_uri = f"data:audio/mp3;base64,{audio_base64}"
                    
                    # Display audio player with JavaScript to trigger avatar animation
                    # Use file path primarily, with base64 fallback
                    st.markdown(
                        f"""
                        <audio id="{audio_id}" controls autoplay style="width: 100%; margin-top: 10px;">
                            <source src="{audio_url}" type="audio/mp3" onerror="this.onerror=null; this.src='{audio_data_uri}';">
                            <source src="{audio_data_uri}" type="audio/mp3">
                            Your browser does not support the audio element.
                        </audio>
                        <script>
                        (function() {{
                            const audio = document.getElementById('{audio_id}');
                            if (audio) {{
                                // Force autoplay (may require user interaction first)
                                setTimeout(function() {{
                                    audio.play().catch(function(error) {{
                                        console.log('Autoplay prevented:', error);
                                        // If autoplay fails, show a play button message
                                        const playMsg = document.createElement('div');
                                        playMsg.id = 'play_msg_{audio_id}';
                                        playMsg.innerHTML = '<p style="color: #666; font-size: 12px; margin-top: 5px; text-align: center;">🔊 Click play above to hear the response</p>';
                                        audio.parentNode.appendChild(playMsg);
                                    }});
                                }}, 100);
                                
                                // Audio event handlers (state managed by Python - no bridge needed)
                                audio.addEventListener('play', function() {{
                                    console.log('Audio playing');
                                    // Remove play message if it exists
                                    const playMsg = document.getElementById('play_msg_{audio_id}');
                                    if (playMsg) playMsg.remove();
                                }});
                                
                                audio.addEventListener('ended', function() {{
                                    console.log('Audio ended');
                                }});
                                
                                audio.addEventListener('pause', function() {{
                                    console.log('Audio paused');
                                }});
                                
                                // Handle load error - try fallback
                                audio.addEventListener('error', function(e) {{
                                    console.log('Audio load error, trying fallback');
                                    const sources = audio.querySelectorAll('source');
                                    if (sources.length > 1 && sources[0].src !== '{audio_data_uri}') {{
                                        audio.src = '{audio_data_uri}';
                                        audio.load();
                                    }}
                                }});
                            }} else {{
                                console.error('Audio element not found:', '{audio_id}');
                            }}
                        }})();
                        </script>
                        """,
                        unsafe_allow_html=True
                    )
                    # Store audio in session state for display below avatar
                    st.session_state.concierge_audio_output = audio_output
                    
                    st.success("✅ Audio ready! Avatar will animate while speaking.")
                else:
                    st.warning("⚠️ Audio generation unavailable")
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.concierge_messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
                import traceback
                if config.DEBUG:
                    st.code(traceback.format_exc())
            
            st.rerun()


def process_concierge_voice(audio_bytes: bytes, language: str) -> str:
    """Process voice input for concierge widget - transcription only, no database required."""
    try:
        # Import Google Cloud Speech-to-Text directly
        try:
            from google.cloud import speech
            GOOGLE_SPEECH_AVAILABLE = True
        except ImportError:
            return "Error: Google Cloud Speech-to-Text library not installed. Please install: pip install google-cloud-speech"
        
        # Determine language code for transcription
        language_codes = {
            'en': 'en-US',
            'ja': 'ja-JP',
            'ne': 'ne-NP'
        }
        lang_code = language_codes.get(language, 'en-US')
        
        # Initialize speech client
        client = None
        try:
            import os
            import config
            
            # Get credentials path from config
            creds_path = None
            if config.GOOGLE_APPLICATION_CREDENTIALS:
                creds_path = Path(config.GOOGLE_APPLICATION_CREDENTIALS)
                if not creds_path.is_absolute():
                    project_root = Path(__file__).parent.parent
                    creds_path = project_root / creds_path
                
                if creds_path.exists():
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(creds_path)
                    client = speech.SpeechClient.from_service_account_json(str(creds_path))
            
            # Fallback: try environment variable
            if not client and os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
                creds_path = Path(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
                if creds_path.exists():
                    client = speech.SpeechClient.from_service_account_json(str(creds_path))
            
            # Final fallback: use default credentials
            if not client:
                client = speech.SpeechClient()
                
        except Exception as e:
            return f"Error: Failed to initialize Speech-to-Text client: {str(e)}. Please check your Google Cloud credentials."
        
        if not client:
            return "Error: Could not initialize Speech-to-Text client. Please check your Google Cloud credentials."
        
        # Configure recognition
        try:
            # Try to detect sample rate from WAV header if possible
            sample_rate = 44100  # Default for mic_recorder (browser typically records at 44.1kHz)
            
            # Check if it's a WAV file and try to read the sample rate
            if len(audio_bytes) > 44 and audio_bytes[:4] == b'RIFF' and audio_bytes[8:12] == b'WAVE':
                try:
                    # WAV header: bytes 24-28 contain sample rate (little-endian)
                    sample_rate = int.from_bytes(audio_bytes[24:28], byteorder='little')
                except:
                    pass  # Use default if parsing fails
            
            # Try multiple configurations as fallback
            configs_to_try = [
                # Config 1: Auto-detect with detected sample rate
                speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                    sample_rate_hertz=sample_rate,
                    language_code=lang_code,
                    alternative_language_codes=["ja-JP", "ne-NP", "en-US"] if lang_code != "auto" else None,
                    enable_automatic_punctuation=True,
                    model="latest_long",
                ),
                # Config 2: Try LINEAR16 encoding (common for WAV)
                speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    sample_rate_hertz=sample_rate,
                    language_code=lang_code,
                    alternative_language_codes=["ja-JP", "ne-NP", "en-US"] if lang_code != "auto" else None,
                    enable_automatic_punctuation=True,
                    model="latest_long",
                ),
                # Config 3: Try with 16000 Hz (standard rate)
                speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                    sample_rate_hertz=16000,
                    language_code=lang_code,
                    alternative_language_codes=["ja-JP", "ne-NP", "en-US"] if lang_code != "auto" else None,
                    enable_automatic_punctuation=True,
                    model="latest_long",
                ),
            ]
            
            audio = speech.RecognitionAudio(content=audio_bytes)
            
            # Try each configuration until one works
            response = None
            last_error = None
            for config_obj in configs_to_try:
                try:
                    response = client.recognize(config=config_obj, audio=audio)
                    if response.results:
                        break  # Success!
                except Exception as e:
                    last_error = e
                    continue  # Try next config
            
            if not response:
                # If all configs failed, raise the last error
                raise last_error if last_error else Exception("All recognition configurations failed")
            
            # Extract transcript
            if response.results:
                transcript = ""
                for result in response.results:
                    transcript += result.alternatives[0].transcript + " "
                return transcript.strip()
            
            return "Error: No speech detected in the audio. Please try speaking more clearly or check your microphone."
            
        except Exception as e:
            error_str = str(e)
            if "403" in error_str or "permission" in error_str.lower() or "SERVICE_DISABLED" in error_str:
                return "Error: Speech-to-Text API access denied. Please check your Google Cloud credentials and ensure the Speech-to-Text API is enabled in your project."
            elif "400" in error_str or "invalid" in error_str.lower() or "InvalidArgument" in error_str:
                # More detailed error for invalid format
                detailed_msg = f"Error: Invalid audio format ({error_str[:100]}). "
                detailed_msg += "This might be due to:\n"
                detailed_msg += "• Audio sample rate mismatch\n"
                detailed_msg += "• Unsupported audio encoding\n"
                detailed_msg += "• Corrupted audio data\n\n"
                detailed_msg += "Please try:\n"
                detailed_msg += "• Recording again with a clear voice\n"
                detailed_msg += "• Using a different browser\n"
                detailed_msg += "• Checking your microphone settings"
                return detailed_msg
            elif "timeout" in error_str.lower():
                return "Error: Transcription timed out. Please try recording a shorter message."
            else:
                # Include more context in error message
                return f"Error processing voice: {error_str[:200]}. Please try recording again or type your message instead."
                
    except Exception as e:
        import traceback
        error_details = str(e)
        return f"Error processing voice: {error_details}. Please try again or type your message instead."


def get_sensei_response(
    user_input: str,
    conversation_history: list,
    transcript: str,
    timer_elapsed: int,
    track: str = "Food/Tech",
    current_page: str = None
) -> str:
    """
    Get response from Sensei using Socratic logic from sandbox_socratic_logic.py.
    
    Args:
        user_input: User's message
        conversation_history: List of previous messages with 'role' and 'content'
        transcript: Video transcript text
        timer_elapsed: Elapsed time in seconds (maps to video timestamp)
        track: Training track (default: "Food/Tech")
        current_page: Current page name (e.g., "📖 Academic Hub") to determine persona [cite: 2025-12-20]
    
    Returns:
        Sensei's response as a string
    """
    try:
        from google import genai
        import config
        
        if not config.GEMINI_API_KEY:
            return "Error: GEMINI_API_KEY not configured. Please set it in your .env file."
        
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        # Determine conversation phase based on timer
        if timer_elapsed < 180:
            phase = "helpful_assistant"
            phase_instruction = "You are in 'Helpful Assistant' mode. Guide the student with questions, but be supportive and encouraging."
        else:
            phase = "evaluator"
            phase_instruction = "You are now in 'Evaluator' mode. Assess the student's understanding more critically. Ask deeper questions to test their knowledge."
        
        # Build conversation history context
        history_text = ""
        if conversation_history:
            history_text = "\n\n**Previous Conversation:**\n"
            for msg in conversation_history[-5:]:  # Last 5 messages
                role_label = "Sensei" if msg['role'] == 'sensei' else "Student"
                history_text += f"- {role_label}: {msg['content']}\n"
        
        # Handle special initial greeting prompt (from show_academic_hub) [cite: 2025-12-20]
        # Simplified Trilingual Prompt: Direct and simple [cite: 2025-12-20]
        if user_input and (user_input.strip().startswith("The student has just started the lesson") or user_input.strip().startswith("Greeting:")):
            # This is a special prompt for initial greeting - use simplified format
            prompt = user_input  # Use the simplified prompt as-is
        # Handle initial greeting when user_input is empty [cite: 2025-12-20]
        elif not user_input or user_input.strip() == "":
            # Initial greeting for Academic Hub
            if current_page == "📖 Academic Hub" or current_page == "Academic Hub":
                prompt = f"""You are a Socratic Japanese Language Teacher. Your goal is to guide the student to understand grammar, particles, and kanji.

**System Context - Lesson Transcript:**
{transcript}

**Language Instructions:**
Based on the transcript context above, you should be prepared to speak in English, Japanese (Kanji/Kana), and Nepali (Devanagari) as needed. The transcript provides the lesson context that informs your responses.

**Initial Greeting:**
The student has just started this lesson. Provide a warm, encouraging greeting in English that:
1. Welcomes them to the JLPT lesson
2. Mentions the key topic from the transcript (if available)
3. Invites them to ask questions or share what they'd like to learn
4. Sets a supportive, Socratic tone

Keep it brief (2-3 sentences) and friendly.

**Your Response (as JLPT Sensei, in English, welcoming greeting):**
"""
            else:
                # Initial greeting for Food/Tech track
                prompt = f"""You are a Japanese Food Safety Sensei (Teacher) conducting a Socratic dialogue about HACCP and kitchen sanitization.

**System Context - Lesson Transcript:**
{transcript}

**Language Instructions:**
Based on the transcript context above, you should be prepared to speak in English, Japanese (Kanji/Kana), and Nepali (Devanagari) as needed. The transcript provides the lesson context that informs your responses.

**Initial Greeting:**
The student has just started this lesson. Provide a warm, encouraging greeting in English that:
1. Welcomes them to the Food Safety training
2. Mentions the key topic from the transcript (if available)
3. Invites them to ask questions or share what they'd like to learn
4. Sets a supportive, Socratic tone

Keep it brief (2-3 sentences) and friendly.

**Your Response (as Food Safety Sensei, in English, welcoming greeting):**
"""
        # Persona Pivot: Check if current page is Academic Hub [cite: 2025-12-20]
        elif current_page == "📖 Academic Hub" or current_page == "Academic Hub":
            # JLPT Sensei persona for Academic Hub [cite: 2025-12-20]
            # Transcript-to-Sensei: Ensure transcript is used as system prompt context [cite: 2025-12-20]
            prompt = f"""You are a Socratic Japanese Language Teacher. Your goal is to guide the student to understand grammar, particles, and kanji. Use the transcript provided. If they make a mistake with a particle (like wa vs ga), ask them to explain the function of the particle instead of correcting them immediately.

**System Context - Lesson Transcript:**
{transcript}

**Language Instructions:**
Based on the transcript context above, you should be prepared to speak in English, Japanese (Kanji/Kana), and Nepali (Devanagari) as needed. The transcript provides the lesson context that informs your responses.

**Your Role:**
- You are a Socratic teacher. You DO NOT give direct answers.
- You ask guiding questions that help the student discover the answers themselves.
- You focus on Japanese grammar, particles (wa, ga, ni, wo, de, etc.), kanji, and JLPT concepts.

**Language Detection:**
- Detect the language the student is using (English, Japanese, or Nepali).
- Respond in the SAME language the student uses.
- If the student mixes languages, respond in the primary language they're using.

**Current Phase: {phase.upper()}**
{phase_instruction}

**Key Topics to Explore:**
1. Particle usage: wa (は), ga (が), ni (に), wo (を), de (で), etc.
2. Kanji recognition and meaning
3. Grammar patterns (N5, N4, N3 level)
4. Sentence structure and word order
5. Verb conjugations and forms

**Socratic Method Rules:**
- NEVER give the answer directly. Instead, ask: "What do you think the particle 'wa' does in this sentence?"
- If the student is stuck, ask a simpler related question to guide them.
- If the student gives a partial answer, ask a follow-up to deepen understanding.
- Praise correct thinking, but challenge assumptions gently.
- Focus on helping them understand the WHY behind grammar rules, not just memorization.

**Example Questions You Might Ask:**
- "In the sentence '私は学生です', what role does the particle 'wa' play? Why is it used here instead of 'ga'?"
- "Can you explain the difference between 'ni' and 'de' when talking about location?"
- "What does this kanji mean? Can you break it down into its components?"

{history_text}

**Student's Latest Input:**
User input: {user_input!r}

**Your Response (as JLPT Sensei, in the student's language, using Socratic questioning):**
"""
        else:
            # Food/Tech Sensei persona (default)
            prompt = f"""You are a Japanese Food Safety Sensei (Teacher) conducting a Socratic dialogue about HACCP (Hazard Analysis and Critical Control Points) and kitchen sanitization.

**System Context - Lesson Transcript:**
{transcript}

**Language Instructions:**
Based on the transcript context above, you should be prepared to speak in English, Japanese (Kanji/Kana), and Nepali (Devanagari) as needed. The transcript provides the lesson context that informs your responses.

**Your Role:**
- You are a Socratic teacher. You DO NOT give direct answers.
- You ask guiding questions that help the student discover the answers themselves.
- You focus on HACCP principles and the 3-step sanitization process:
  * Seiso (清掃) - Cleaning: Removing visible dirt and debris
  * Sakkin (殺菌) - Disinfection: Killing harmful microorganisms
  * Kansou (乾燥) - Air-drying: Allowing surfaces to air-dry naturally (no towels)

**Language Detection:**
- Detect the language the student is using (English, Japanese, or Nepali).
- Respond in the SAME language the student uses.
- If the student mixes languages, respond in the primary language they're using.

**Current Phase: {phase.upper()}**
{phase_instruction}

**Key Topics to Explore:**
1. Temperature control: Cold storage (<10°C), Frozen storage (<-15°C)
2. 3-step sanitization: Why each step matters, what happens if you skip a step
3. Cross-contamination (Kousa-osen / 交差汚染)
4. Expiry management (Kigen-kanri / 期限管理)
5. Proper disinfection techniques (Shudoku / 消毒)

**Socratic Method Rules:**
- NEVER give the answer directly. Instead, ask: "What do you think would happen if...?"
- If the student is stuck, ask a simpler related question to guide them.
- If the student gives a partial answer, ask a follow-up to deepen understanding.
- Praise correct thinking, but challenge assumptions gently.
- If the student uses HACCP terminology (like Kousa-osen, Kigen-kanri, Shudoku), acknowledge it positively.

**Example Questions You Might Ask:**
- "The temperature log shows the walk-in freezer at -10°C. What does HACCP require for frozen storage?"
- "You're cleaning a prep table. Can you explain the difference between Seiso and Sakkin? Why is air-drying (Kansou) better than using a towel?"
- "What could happen if you skip the Kansou step and wipe the surface with a towel instead?"

{history_text}

**Student's Latest Input:**
User input: {user_input!r}

**Your Response (as Sensei, in the student's language, using Socratic questioning):**
"""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        return response.text.strip()
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting Sensei response: {e}")
        return f"I encountered an error: {str(e)}. Please try again."


def check_vocabulary_bonus_terms(user_input: str, track: str = "Food/Tech") -> list[str]:
    """
    Check if user input contains vocabulary bonus terms.
    
    Returns list of found terms.
    """
    if track != "Food/Tech":
        return []
    
    # Vocabulary bonus terms for Food/Tech track
    bonus_terms = [
        "Kousa-osen",
        "Kousa-osen",
        "Kigen-kanri",
        "Kigen-kanri",
        "Shudoku",
        "Shudoku",
        "交差汚染",  # Japanese for cross-contamination
        "期限管理",  # Japanese for expiry management
        "消毒"       # Japanese for disinfection
    ]
    
    found_terms = []
    user_lower = user_input.lower()
    
    for term in bonus_terms:
        if term.lower() in user_lower or term in user_input:
            found_terms.append(term)
    
    return found_terms


def transcribe_audio_with_gemini(audio_bytes: bytes) -> str:
    """
    Transcribe audio using Gemini 2.0 Flash with trilingual support.
    
    Args:
        audio_bytes: Audio data as bytes (WAV format from mic_recorder)
    
    Returns:
        Transcribed text string
    """
    try:
        import google.generativeai as genai
        import config
        
        # Get API key
        api_key = config.GEMINI_API_KEY if config and hasattr(config, 'GEMINI_API_KEY') else os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            return "Error: GEMINI_API_KEY not found. Set it in .env file."
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Prepare audio data
        audio_data = {
            "mime_type": "audio/wav",
            "data": audio_bytes
        }
        
        # Trilingual transcription prompt
        prompt = "Please transcribe this audio accurately. If it is in Japanese, provide the Kanji/Kana. If English or Nepali, transcribe accordingly. Output ONLY the transcript."
        
        # Generate transcription
        response = model.generate_content([prompt, audio_data])
        
        return response.text.strip()
        
    except Exception as e:
        import traceback
        logger.error(f"Error transcribing audio with Gemini: {e}")
        if config.DEBUG:
            logger.error(traceback.format_exc())
        return f"Error transcribing audio: {str(e)}"


def update_mastery_score_for_vocabulary(candidate_id: str, track: str, found_terms: list[str]):
    """
    Update mastery score for Vocabulary skill when bonus terms are used.
    Increments by 2 points per term found (capped at 100).
    """
    if not found_terms:
        return
    
    try:
        from database.db_manager import CurriculumProgress, SessionLocal
        import json
        
        db = SessionLocal()
        try:
            curriculum = db.query(CurriculumProgress).filter(
                CurriculumProgress.candidate_id == candidate_id
            ).first()
            
            if not curriculum:
                return
            
            # Get or initialize mastery_scores
            mastery_scores = curriculum.mastery_scores
            if mastery_scores is None:
                mastery_scores = {}
            elif isinstance(mastery_scores, str):
                try:
                    mastery_scores = json.loads(mastery_scores)
                except json.JSONDecodeError:
                    mastery_scores = {}
            elif not isinstance(mastery_scores, dict):
                mastery_scores = {}
            
            # Initialize track if needed
            if track not in mastery_scores:
                mastery_scores[track] = {}
            
            # Increment Vocabulary score (2 points per term, max 100)
            current_vocab_score = float(mastery_scores[track].get("Vocabulary", 0.0))
            increment = min(2.0 * len(found_terms), 100.0 - current_vocab_score)
            new_vocab_score = min(100.0, current_vocab_score + increment)
            mastery_scores[track]["Vocabulary"] = round(new_vocab_score, 1)
            
            # Save to database
            curriculum.mastery_scores = mastery_scores
            db.add(curriculum)
            db.commit()
            db.refresh(curriculum)
            
        finally:
            db.close()
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error updating mastery score for vocabulary: {e}")


def get_concierge_response(user_input: str, language: str) -> str:
    """Get response from SupportAgent for concierge widget."""
    # Handle empty input
    if not user_input or not user_input.strip():
        return "Please enter a message or question. I'm here to help! 😊"
    
    try:
        from agency.support_agent.support_agent import SupportAgent
        from agency.support_agent.tools import GetLifeInJapanAdvice
        from agency.support_agent.navigation_tool import NavigateToPage
        import config
        
        # Handle general platform questions first
        user_lower = user_input.lower().strip()
        
        # Handle greetings and casual conversation
        greeting_keywords = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
        if any(greeting in user_lower for greeting in greeting_keywords):
            greetings = {
                "en": "Hello! 👋 I'm the ExploraKodo Concierge. How can I help you today?",
                "ja": "こんにちは！👋 ExploraKodoコンシェルジュです。今日はどのようにお手伝いできますか？",
                "ne": "नमस्ते! 👋 म ExploraKodo Concierge हुँ। आज म तपाईंलाई कसरी मद्दत गर्न सक्छु?"
            }
            return greetings.get(language, greetings["en"])
        
        # Handle "how are you" and similar questions
        if any(phrase in user_lower for phrase in ["how are you", "how's it going", "how do you do", "what's up"]):
            responses = {
                "en": "I'm doing great, thank you! 😊 I'm here to help you with ExploraKodo platform questions, life-in-Japan advice, and navigation. What would you like to know?",
                "ja": "元気です、ありがとうございます！😊 ExploraKodoプラットフォームの質問、日本での生活に関するアドバイス、ナビゲーションをお手伝いします。何か知りたいことはありますか？",
                "ne": "म ठिक छु, धन्यवाद! 😊 म ExploraKodo प्लेटफर्म प्रश्नहरू, जापानमा जीवन सल्लाह, र नेभिगेसनमा मद्दत गर्न यहाँ छु। तपाईं के जान्न चाहनुहुन्छ?",
            }
            return responses.get(language, responses["en"])
        
        # Platform feature questions
        if any(keyword in user_lower for keyword in ["support", "language", "nepalese", "nepali", "japanese", "multilingual", "what languages", "which languages"]):
            if "nepal" in user_lower or "nepali" in user_lower or "ne" in user_lower:
                return """
✅ **Yes! ExploraKodo supports Nepali (नेपाली).**

The platform is **trilingual** and supports:
- 🇺🇸 **English** (en)
- 🇯🇵 **Japanese** (日本語) (ja)
- 🇳🇵 **Nepali** (नेपाली) (ne)

You can switch languages using the language selector in the Concierge widget. All features including voice recording, text-to-speech, and AI responses work in all three languages."""
            
            if "japan" in user_lower or "japanese" in user_lower or "ja" in user_lower:
                return """
✅ **Yes! ExploraKodo supports Japanese (日本語).**

The platform is **trilingual** and supports:
- 🇺🇸 **English** (en)
- 🇯🇵 **Japanese** (日本語) (ja)
- 🇳🇵 **Nepali** (नेपाली) (ne)

You can switch languages using the language selector in the Concierge widget. All features including voice recording, text-to-speech, and AI responses work in all three languages."""
            
            return """
✅ **ExploraKodo is a Trilingual Platform!**

The platform supports **three languages**:
- 🇺🇸 **English** (en)
- 🇯🇵 **Japanese** (日本語) (ja)
- 🇳🇵 **Nepali** (नेपाली) (ne)

**Features available in all languages:**
- Voice recording and transcription
- Text-to-speech responses
- AI-powered language coaching
- Virtual classroom with Sensei avatar
- Life-in-Japan support and advice

Switch languages using the 🌐 Language selector above!"""
        
        # Check if user wants to navigate
        navigation_keywords = ["go to", "take me to", "show me", "navigate to", "open"]
        if any(keyword in user_lower for keyword in navigation_keywords):
            # Use navigation tool
            nav_tool = NavigateToPage(page_name=user_input, reason=f"User requested navigation: {user_input}")
            return nav_tool.run()
        
        # Check if it's a general question about the platform
        platform_keywords = ["what is", "what can", "how does", "how to", "help", "features", "capabilities"]
        if any(keyword in user_lower for keyword in platform_keywords) and not any(kw in user_lower for kw in ["visa", "bank", "housing", "health", "legal"]):
            return """
🤖 **ExploraKodo Concierge can help you with:**

**Platform Features:**
- Language learning (N5-N3 Japanese proficiency)
- Voice coaching with AI Sensei
- Virtual classroom with 2D animated avatar
- Trilingual support (English, Japanese, Nepali)

**Life-in-Japan Support:**
- Visa and immigration questions
- Banking and financial services
- Healthcare and insurance
- Housing and utilities
- Legal rights and responsibilities

**Navigation:**
- Say \"take me to [page name]\" to navigate
- Available pages: Candidate View, Virtual Classroom, Life-in-Japan Support, etc.

Try asking about specific topics like \"visa renewal\" or \"banking in Japan\" for detailed information!"""
        
        # Otherwise, use GetLifeInJapanAdvice for life-in-Japan questions
        advice_tool = GetLifeInJapanAdvice(
            query=user_input,
            language=language
        )
        result = advice_tool.run()
        
        # If no results found, use AI to answer general questions
        if "❌ No information found" in result:
            # Try using Gemini AI for general platform questions
            try:
                from google import genai
                import config
                
                if config.GEMINI_API_KEY:
                    client = genai.Client(api_key=config.GEMINI_API_KEY)
                    
                    # Create a comprehensive prompt for platform questions
                    prompt = f"""
You are the ExploraKodo Concierge, an AI assistant for the ExploraKodo platform.

**Platform Overview:**
ExploraKodo is a 360° AI-powered lifecycle platform for Nepali human capital preparing for work in Japan. It provides:
- Trilingual training (N5-N3 Japanese proficiency, Kaigo caregiving, AI/ML tech)
- Voice coaching with AI Sensei and 2D animated avatar
- Virtual classroom with live voice interaction
- Life-in-Japan support (visa, banking, housing, legal)
- Document vault and compliance tracking
- Multi-phase progression system

**User Question:** {user_input}

**Instructions:**
- Answer the question helpfully and accurately about ExploraKodo platform features
- If the question is about life in Japan (visa, banking, housing, etc.), acknowledge that specific information wasn't found in the knowledge base
- Be conversational, friendly, and helpful
- If you don't know something, suggest where the user can find more information
- Keep responses concise (2-3 paragraphs max)

**Response (in {language}):**"""
                    
                    ai_response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt
                    )
                    
                    response_text = ai_response.text.strip()
                    
                    # Add helpful context
                    return f"""{response_text}\n\n---\n\n💡 **Need more specific help?**\n- Life-in-Japan questions: Try \"visa renewal\", \"banking in Japan\", \"housing\"
- Platform features: Ask about \"virtual classroom\", \"voice coaching\", \"language learning\"
- Navigation: Say \"take me to [page name]\" to navigate"""
                    
            except Exception as ai_error:
                # Fallback if AI fails
                fallback_text = """I couldn't find specific information, but I can help with:
- **Life-in-Japan:** Visa, banking, housing, healthcare, legal rights
- **Platform Features:** Language learning, virtual classroom, voice coaching, trilingual support
- **Navigation:** Say "take me to [page name]" to navigate

**Try asking:**
- "What is the virtual classroom?"
- "How does voice coaching work?"
- "Tell me about visa renewal"
- "What languages are supported?"

Or rephrase your question and I'll do my best to help!"""
                return f"{result}\n\n{fallback_text}"
        
        return result
        
    except Exception as e:
        # Enhanced error handling with AI fallback
        try:
            from google import genai
            import config
            
            if config.GEMINI_API_KEY:
                client = genai.Client(api_key=config.GEMINI_API_KEY)
                
                prompt_parts = [
                    "You are the ExploraKodo Concierge. A user asked: ",
                    repr(user_input),
                    "\n\nAn error occurred: ",
                    str(e),
                    "\n\nProvide a helpful, friendly response that:\n",
                    "1. Acknowledges the question\n",
                    "2. Provides general guidance about ExploraKodo platform\n",
                    "3. Suggests alternative ways to get help\n",
                    "4. Keeps it concise and helpful\n\n",
                    f"Response (in {language}):"
                ]
                prompt = "".join(prompt_parts)
                
                ai_response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                
                note_text = "*Note: There was a technical issue, but I've provided a helpful response above.*"
                response_text = ai_response.text.strip()
                return f"{response_text}\n\n{note_text}"
        except Exception as ai_error:
            # Fallback if AI error handling fails
            pass
        
        help_lines = [
            "I can help you with:",
            "- Questions about ExploraKodo platform features",
            "- Life-in-Japan advice (visa, banking, housing, etc.)",
            "- Navigation to different pages",
            "- General platform guidance",
            "",
            "**Try asking:**",
            '- "What can you help me with?"',
            '- "How does the virtual classroom work?"',
            '- "Tell me about language learning"',
            "",
            "Or rephrase your question and I'll do my best to help!"
        ]
        help_section = "\n".join(help_lines)
        
        error_msg = f"I apologize, but I encountered an error: {str(e)}"
        return f"{error_msg}\n\n{help_section}"


def generate_trilingual_tts(text: str, language: str, track: str | None = None) -> bytes | None:
    """
    Generate TTS audio in the specified language with track-based personality.
    
    Args:
        text: Text to convert to speech
        language: Language code ('en', 'ja', 'ne')
        track: Optional track type ('Care-giving', 'Academic', 'Food/Tech') for personality adjustment
    """
    try:
        from google.cloud import texttospeech
        import config
        
        tts_client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Get voice based on language
        voice_name = config.LANGUAGE_TTS_VOICES.get(language, 'en-US-Neural2-C')
        
        # Determine language code
        lang_codes = {
            'en': 'en-US',
            'ja': 'ja-JP',
            'ne': 'ne-NP'
        }
        lang_code = lang_codes.get(language, 'en-US')
        
        # Get track-based personality settings if track is provided
        personality = None
        if track and track in config.TRACK_TTS_PERSONALITY:
            personality = config.TRACK_TTS_PERSONALITY[track]
        
        # Determine SSML gender based on track personality or default to NEUTRAL
        ssml_gender = texttospeech.SsmlVoiceGender.NEUTRAL
        if personality:
            gender_str = personality.get('ssml_gender', 'NEUTRAL')
            if gender_str == 'FEMALE':
                ssml_gender = texttospeech.SsmlVoiceGender.FEMALE
            elif gender_str == 'MALE':
                ssml_gender = texttospeech.SsmlVoiceGender.MALE
            else:
                ssml_gender = texttospeech.SsmlVoiceGender.NEUTRAL
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            name=voice_name,
            ssml_gender=ssml_gender
        )
        
        # Apply track-based personality settings
        speaking_rate = 1.0
        pitch = 0.0
        if personality:
            speaking_rate = personality.get('speaking_rate', 1.0)
            pitch = personality.get('pitch', 0.0)
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch
        )
        
        tts_response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return tts_response.audio_content
        
    except Exception as e:
        st.sidebar.warning(f"TTS unavailable: {str(e)}")
        return None


# Main App
def main():
    """Main Streamlit app."""
    # ATOMIC FIX: Initialize session state at the very top, before any UI calls
    if 'concierge_avatar_visible' not in st.session_state:
        st.session_state.concierge_avatar_visible = True
    
    st.markdown('<h1 class="main-header">🌏 ExploraKodo Global Command Center</h1>', unsafe_allow_html=True)

    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    # Admin Mode Toggle (Security Check)
    admin_mode = st.sidebar.checkbox("🔒 Admin Mode", key="admin_mode", help="Enable to access Admin Dashboard")
    
    # Check for critical logs (notification badge)
    if admin_mode:
        try:
            from utils.activity_logger import ActivityLogger
            critical_logs = ActivityLogger.get_recent_critical_logs(hours=1)
            if critical_logs:
                st.sidebar.warning(f"⚠️ {len(critical_logs)} critical event(s) in last hour")
        except Exception:
            pass
    
    page_options = ["Candidate View", "Wisdom Hub", "Video Hub", "📖 Academic Hub", "Progress", "Live Simulator", "Financial Ledger", "Compliance", "Life-in-Japan Support", "Virtual Classroom"]
    if admin_mode:
        page_options.append("Admin Dashboard")
    
    page = st.sidebar.radio(
        "Select View",
        page_options,
    )
    
    # Store current page in session state for persona detection
    st.session_state.page = page
    st.session_state.current_page = page  # Also store as current_page for compatibility
    
    # Initialize Academic Hub session state variables [cite: 2025-12-21]
    if 'academic_chat_history' not in st.session_state:
        st.session_state.academic_chat_history = []
    if 'academic_competency_response' not in st.session_state:
        st.session_state.academic_competency_response = ""
    
    # Show Concierge Widget (after page selection to avoid conflicts)
    # Always show widget - it's a core feature
    # HARD-OVERRIDE: Widget is wrapped in strict sidebar block inside show_concierge_widget()
    try:
        show_concierge_widget()
    except Exception as e:
        # If widget fails completely, show a fallback message
        with st.sidebar:
            st.markdown("---")
            st.error(f"⚠️ Concierge Widget Error: {str(e)}")
            import traceback
            if config.DEBUG:
                with st.expander("Debug Info"):
                    st.code(traceback.format_exc())

    # Page routing with error handling
    try:
        if page == "Candidate View":
            show_candidate_view()
        elif page == "Wisdom Hub":
            show_wisdom_hub()
        elif page == "Video Hub":
            show_video_hub()
        elif page == "📖 Academic Hub":
            show_academic_hub()
        elif page == "Progress":
            show_progress_dashboard()
        elif page == "Live Simulator":
            show_live_simulator()
        elif page == "Financial Ledger":
            show_financial_ledger()
        elif page == "Compliance":
            show_compliance_view()
        elif page == "Life-in-Japan Support":
            show_support_hub()
        elif page == "Virtual Classroom":
            # Import and show virtual classroom page
            try:
                from dashboard.pages.virtual_classroom import main as show_virtual_classroom
                show_virtual_classroom()
            except ImportError:
                st.error("Virtual Classroom page not found. Please ensure dashboard/pages/virtual_classroom.py exists.")
            except Exception as e:
                st.error(f"Error loading Virtual Classroom: {str(e)}")
                if config.DEBUG:
                    import traceback
                    with st.expander("Debug Info"):
                        st.code(traceback.format_exc())
        elif page == "Admin Dashboard":
            if admin_mode:
                show_admin_dashboard()
            else:
                st.error("🔒 Admin Mode must be enabled to access this page.")
    except Exception as page_error:
        st.error(f"⚠️ Error loading page '{page}': {str(page_error)}")
        import traceback
        if config.DEBUG:
            with st.expander("Debug Info"):
                st.code(traceback.format_exc())
        st.info("💡 Please try refreshing the page or selecting a different view.")


def show_candidate_view():
    """Display candidate view with searchable list."""
    st.header("👥 Candidate View")

    # AI Daily Briefing Section (at the top)
    st.markdown("---")
    st.subheader("🎓 AI Daily Briefing")
    
    # Get candidate list for briefing selection
    db = get_db_session()
    try:
        candidates = db.query(Candidate).all()
        candidate_options = {f"{c.full_name} ({c.candidate_id})": c.candidate_id for c in candidates}
        
        if candidate_options:
            selected_briefing_candidate = st.selectbox(
                "Select Candidate for Briefing",
                options=list(candidate_options.keys()),
                key="briefing_candidate_select"
            )
            
            selected_candidate_id = candidate_options[selected_briefing_candidate]
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info("💡 Click the button below to generate an AI-powered executive summary of the candidate's progress in the last 24 hours.")
            with col2:
                if st.button("🔄 Generate Briefing", key="generate_briefing_btn"):
                    try:
                        from agency.student_progress_agent.tools import GenerateDailyBriefing
                        
                        briefing_tool = GenerateDailyBriefing(candidate_id=selected_candidate_id)
                        briefing_result = briefing_tool.run()
                        
                        if briefing_result and not briefing_result.startswith("Error"):
                            st.success("**📊 Daily Briefing:**")
                            st.info(briefing_result)
                        else:
                            st.warning(briefing_result if briefing_result else "Unable to generate briefing.")
                    except Exception as e:
                        st.error(f"Error generating briefing: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
        else:
            st.info("No candidates available for briefing generation.")
    except Exception as e:
        st.error(f"Error loading candidates: {str(e)}")
    finally:
        db.close()
    
    st.markdown("---")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search_term = st.text_input("🔍 Search (ID or Name)", "")
    with col2:
        status_filter = st.selectbox("Status Filter", ["All", "Incomplete", "ReadyForSubmission", "Travel-Ready"])
    with col3:
        track_filter = st.selectbox("Track Filter", ["All", "student", "jobseeker"])

    # Load candidates
    try:
        df = load_candidates(search_term, status_filter, track_filter)

        if df.empty:
            st.info("No candidates found matching the criteria.")
        else:
            st.metric("Total Candidates", len(df))

            # Display dataframe with styling
            st.dataframe(
                df,
                width='stretch',
                hide_index=True,
            )

            # Show detailed view for selected candidate
            if len(df) > 0:
                st.subheader("📋 Candidate Details")
                selected_id = st.selectbox("Select Candidate", df["Candidate ID"].tolist())

                if selected_id:
                    db = get_db_session()
                    try:
                        candidate = db.query(Candidate).filter(Candidate.candidate_id == selected_id).first()
                        curriculum = (
                            db.query(CurriculumProgress)
                            .filter(CurriculumProgress.candidate_id == selected_id)
                            .first()
                        )

                        if candidate:
                            col1, col2 = st.columns(2)

                            with col1:
                                st.write("**Basic Information:**")
                                st.write(f"- **ID:** {candidate.candidate_id}")
                                st.write(f"- **Name:** {candidate.full_name}")
                                st.write(f"- **Track:** {candidate.track.title()}")
                                st.write(f"- **Status:** {candidate.status}")
                                st.write(f"- **Travel-Ready:** {'✓ Yes' if candidate.travel_ready else '✗ No'}")

                            with col2:
                                st.write("**Requirements:**")
                                if candidate.track == "student":
                                    st.write(f"- 150-hour Certificate: {'✓' if candidate.has_150_hour_study_certificate else '✗'}")
                                    st.write(f"- Financial Sponsor Docs: {'✓' if candidate.has_financial_sponsor_docs else '✗'}")
                                else:
                                    st.write(f"- JLPT N4/N5: {'✓' if candidate.has_jlpt_n4_or_n5 else '✗'}")
                                    st.write(f"- Kaigo Skills Test: {'✓' if candidate.has_kaigo_skills_test else '✗'}")

                            if curriculum:
                                st.write("**Curriculum Progress:**")
                                st.progress(
                                    curriculum.jlpt_n5_units_completed / curriculum.jlpt_n5_total_units
                                    if curriculum.jlpt_n5_total_units > 0
                                    else 0,
                                    text=f"JLPT N5: {curriculum.jlpt_n5_units_completed}/{curriculum.jlpt_n5_total_units} units",
                                )
                                st.progress(
                                    curriculum.jlpt_n4_units_completed / curriculum.jlpt_n4_total_units
                                    if curriculum.jlpt_n4_total_units > 0
                                    else 0,
                                    text=f"JLPT N4: {curriculum.jlpt_n4_units_completed}/{curriculum.jlpt_n4_total_units} units",
                                )
                                
                                # Goal Tracker - Adaptive Level Indicator
                                st.markdown("---")
                                show_goal_tracker(selected_id)
                                
                                # Show Phase Unlock Progress
                                st.markdown("---")
                                st.subheader("🚪 Phase Unlock Progress")
                                show_phase_unlock_progress(selected_id)
                                
                                # Show Learning Curve
                                st.markdown("---")
                                st.subheader("📈 Learning Curve")
                                show_learning_curve(selected_id)
                                
                                # Show Socratic Training History
                                st.markdown("---")
                                st.subheader("📚 Socratic Training History")
                                show_socratic_history(curriculum.dialogue_history, selected_id)
                    except Exception as e:
                        st.error(f"Error loading candidate details: {str(e)}")
                    finally:
                        db.close()
    except Exception as e:
        # Error already handled in load_candidates, but catch any other exceptions
        pass


def show_wisdom_hub():
    """Display wisdom reports from OperationsAgent."""
    st.header("📊 Wisdom Hub")

    reports = load_wisdom_reports()

    if not reports:
        st.info("No wisdom reports found. Generate one using the OperationsAgent.")
    else:
        st.metric("Available Reports", len(reports))

        # Select report
        report_files = [r.name for r in reports]
        selected_report = st.selectbox("Select Report", report_files)

        if selected_report:
            report_path = Path(__file__).parent.parent / "operations" / "reports" / selected_report
            with open(report_path, "r", encoding="utf-8") as f:
                report_content = f.read()

            st.markdown("---")
            st.markdown(report_content)


def calculate_mastery_scores(candidate_id: str) -> tuple[dict, datetime | None]:
    """
    Get mastery scores (0-100%) from CurriculumProgress.mastery_scores JSON field.
    
    Returns:
        Tuple of (mastery_scores_dict, last_updated_timestamp)
        {
            "Food/Tech": {
                "Vocabulary": 75.0,
                "Tone/Honorifics": 60.0,
                "Contextual Logic": 80.0
            },
            "Academic": {...},
            "Care-giving": {...}
        }
    """
    db = get_db_session()
    try:
        import json
        from datetime import datetime, timezone
        
        # Get curriculum progress - refresh to ensure latest data
        curriculum = db.query(CurriculumProgress).filter(
            CurriculumProgress.candidate_id == candidate_id
        ).first()
        
        if not curriculum:
            # Return default scores if no curriculum found
            tracks = ["Food/Tech", "Academic", "Care-giving"]
            skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
            return {
                track: {skill: 0.0 for skill in skills}
                for track in tracks
            }, None
        
        # Refresh to ensure we have the latest mastery_scores from database
        db.refresh(curriculum)
        
        # Get mastery_scores from JSON field
        mastery_scores = curriculum.mastery_scores
        
        # Get last updated timestamp
        last_updated = curriculum.updated_at
        
        # Handle different data types (dict, string, None)
        if mastery_scores is None:
            mastery_scores = {}
        elif isinstance(mastery_scores, str):
            try:
                mastery_scores = json.loads(mastery_scores)
            except json.JSONDecodeError:
                mastery_scores = {}
        elif not isinstance(mastery_scores, dict):
            mastery_scores = {}
        
        # Initialize default structure
        tracks = ["Food/Tech", "Academic", "Care-giving"]
        skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
        
        # Ensure all tracks and skills exist with default values
        result = {}
        for track in tracks:
            result[track] = {}
            track_data = mastery_scores.get(track, {})
            for skill in skills:
                result[track][skill] = float(track_data.get(skill, 0.0))
        
        return result, last_updated
        
    except Exception as e:
        logger.error(f"Error getting mastery scores from CurriculumProgress: {e}")
        # Return default scores on error
        tracks = ["Food/Tech", "Academic", "Care-giving"]
        skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
        return {
            track: {skill: 0.0 for skill in skills}
            for track in tracks
        }, None
    finally:
        db.close()


def generate_weak_point_summary(mastery_scores: dict, candidate_id: str) -> str:
    """
    Generate AI-powered summary of weak points and recommendations.
    """
    try:
        from google import genai
        
        if not config.GEMINI_API_KEY:
            return _generate_fallback_summary(mastery_scores)
        
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        # Build summary of scores
        score_summary = []
        for track, skills in mastery_scores.items():
            track_scores = []
            for skill, score in skills.items():
                track_scores.append(f"{skill}: {score}%")
            score_summary.append(f"{track}: {', '.join(track_scores)}")
        
        prompt = f"""
You are Sensei, a wise Japanese language teacher. Analyze the following student performance data and provide a personalized, encouraging summary.

Student Performance Data:
{chr(10).join(score_summary)}

Provide a brief, encouraging summary (2-3 sentences) that:
1. Highlights what the student is excelling in
2. Identifies the weakest area (lowest score)
3. Provides a specific recommendation (e.g., "Try Session #4 again" or "Focus on Care-giving track's Honorifics practice")

Format: "Sensei says: [your summary]"

Be encouraging and specific. Use the track names and skill categories from the data."""
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        summary = response.text.strip()
        
        # Clean up the response
        if "Sensei says:" not in summary:
            summary = f"Sensei says: {summary}"
        
        return summary
        
    except Exception as e:
        logger.warning(f"Error generating AI summary: {e}")
        return _generate_fallback_summary(mastery_scores)


def _generate_fallback_summary(mastery_scores: dict) -> str:
    """Generate a fallback summary without AI."""
    # Find highest and lowest scores
    all_scores = []
    for track, skills in mastery_scores.items():
        for skill, score in skills.items():
            all_scores.append((track, skill, score))
    
    if not all_scores:
        return "Sensei says: Keep practicing! Your progress will be tracked as you complete assessments."
    
    # Find best and worst
    all_scores.sort(key=lambda x: x[2], reverse=True)
    best = all_scores[0]
    worst = all_scores[-1]
    
    # Build summary
    summary = f"Sensei says: You are excelling in {best[0]} {best[1]} ({best[2]}%), "
    summary += f"but your {worst[1]} in the {worst[0]} track needs more practice ({worst[2]}%). "
    summary += f"Try reviewing the {worst[0]} track lessons again."
    
    return summary


def show_progress_dashboard():
    """Display Student Performance Heatmap with mastery scores."""
    st.header("📊 Progress Dashboard - Student Performance Heatmap")
    
    # Get candidate ID
    candidate_id = st.session_state.get('selected_candidate_id')
    if not candidate_id:
        # Try to get from database
        db = get_db_session()
        try:
            candidates = db.query(Candidate).limit(10).all()
            if candidates:
                candidate_options = {f"{c.full_name} ({c.candidate_id})": c.candidate_id for c in candidates}
                selected_candidate = st.selectbox(
                    "Select Candidate:",
                    options=list(candidate_options.keys()),
                    key="progress_candidate_select"
                )
                candidate_id = candidate_options.get(selected_candidate)
            else:
                candidate_id = st.text_input("Enter Candidate ID:", key="progress_candidate_id_input")
        finally:
            db.close()
    
    if not candidate_id:
        st.info("Please select or enter a candidate ID to view progress.")
        return
    
    # Calculate mastery scores
    with st.spinner("Calculating mastery scores..."):
        mastery_scores, last_updated = calculate_mastery_scores(candidate_id)
    
    # Display Last Evaluated timestamp
    if last_updated:
        from datetime import datetime, timezone
        # Convert to local time if needed, or display in UTC
        if isinstance(last_updated, datetime):
            # Format timestamp
            formatted_time = last_updated.strftime("%Y-%m-%d %H:%M:%S UTC")
            # Calculate time ago
            now = datetime.now(timezone.utc)
            if last_updated.tzinfo is None:
                # If no timezone info, assume UTC
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            time_diff = now - last_updated
            if time_diff.days > 0:
                time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
            elif time_diff.seconds > 3600:
                hours = time_diff.seconds // 3600
                time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif time_diff.seconds > 60:
                minutes = time_diff.seconds // 60
                time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                time_ago = "just now"
            
            st.caption(f"🕒 Last Evaluated: {formatted_time} ({time_ago})")
    
    # Display overview metrics
    st.subheader("📈 Overall Mastery Scores")
    col1, col2, col3 = st.columns(3)
    
    tracks = ["Care-giving", "Academic", "Food/Tech"]
    track_icons = {"Care-giving": "🏥", "Academic": "📖", "Food/Tech": "🍜"}
    
    for i, track in enumerate(tracks):
        with [col1, col2, col3][i]:
            avg_score = sum(mastery_scores[track].values()) / len(mastery_scores[track]) if mastery_scores[track] else 0
            st.metric(
                f"{track_icons[track]} {track}",
                f"{avg_score:.1f}%",
                delta=f"{avg_score - 50:.1f}%" if avg_score > 50 else None
            )
    
    st.markdown("---")
    
    # Create heatmap visualization
    st.subheader("🔥 Performance Heatmap")
    
    # Verification: Show that we're pulling from mastery_scores JSON
    if "Food/Tech" in mastery_scores and "Vocabulary" in mastery_scores["Food/Tech"]:
        vocab_score = mastery_scores["Food/Tech"]["Vocabulary"]
        if vocab_score > 0:
            st.success(f"✅ Vocabulary score from Video Hub: {vocab_score:.1f}% (pulled from CurriculumProgress.mastery_scores JSON)")
    
    if not PLOTLY_AVAILABLE:
        st.warning("Plotly is not available. Please install it with: pip install plotly")
        # Fallback: Show as table
        df = pd.DataFrame(mastery_scores).T
        st.dataframe(df, width='stretch')
    else:
        # Prepare data for heatmap
        tracks = ["Care-giving", "Academic", "Food/Tech"]
        skills = ["Vocabulary", "Tone/Honorifics", "Contextual Logic"]
        
        # Create matrix - pulling directly from mastery_scores JSON field
        z_data = []
        for track in tracks:
            row = [mastery_scores[track].get(skill, 0.0) for skill in skills]
            z_data.append(row)
        
        # Create heatmap
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=skills,
            y=tracks,
            colorscale='RdYlGn',
            zmin=0,
            zmax=100,
            text=[[f"{val:.1f}%" for val in row] for row in z_data],
            texttemplate='%{text}',
            textfont={"size": 12, "color": "black"},
            colorbar=dict(title=dict(text="Mastery Score (%)", side="right"))
        ))
        
        fig.update_layout(
            title="Student Performance Heatmap by Track and Skill",
            xaxis_title="Skill Categories",
            yaxis_title="Tracks",
            width=800,
            height=400,
            font=dict(size=12)
        )
        
        st.plotly_chart(fig, width='stretch')
        
        # Also create a radar chart for better visualization
        st.subheader("📊 Performance Radar Chart")
        
        # Create radar chart data
        fig_radar = go.Figure()
        
        for track in tracks:
            fig_radar.add_trace(go.Scatterpolar(
                r=[mastery_scores[track].get(skill, 0.0) for skill in skills],
                theta=skills,
                fill='toself',
                name=track
            ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=True,
            title="Performance Comparison Across Tracks",
            width=700,
            height=500
        )
        
        st.plotly_chart(fig_radar, width='stretch')
    
    st.markdown("---")
    
    # Weak Point Alert
    st.subheader("💡 Sensei's Feedback")
    with st.spinner("Generating personalized feedback..."):
        summary = generate_weak_point_summary(mastery_scores, candidate_id)
    
    st.info(summary)
    
    # Detailed breakdown
    with st.expander("📋 Detailed Score Breakdown"):
        for track in tracks:
            st.markdown(f"### {track_icons[track]} {track}")
            for skill, score in mastery_scores[track].items():
                # Create progress bar
                progress_color = "green" if score >= 70 else "orange" if score >= 50 else "red"
                st.progress(score / 100.0, text=f"{skill}: {score}%")
    
    # Recommendations
    st.markdown("---")
    st.subheader("🎯 Recommendations")
    
    # Find weakest areas
    weakest_areas = []
    for track in tracks:
        for skill, score in mastery_scores[track].items():
            if score < 70:
                weakest_areas.append((track, skill, score))
    
    if weakest_areas:
        weakest_areas.sort(key=lambda x: x[2])  # Sort by score (lowest first)
        
        st.markdown("**Areas needing improvement:**")
        for track, skill, score in weakest_areas[:3]:  # Top 3 weakest
            st.markdown(f"- **{track} - {skill}**: {score}% (Target: 70%+)")
            st.markdown(f"  → Review {track} track lessons and practice {skill.lower()}.")
    else:
        st.success("🎉 Excellent! All areas are above 70%. Keep up the great work!")
    
    # Download Official Report
    st.markdown("---")
    st.subheader("📄 Official Performance Report")
    
    try:
        from agency.training_agent.report_generator import GeneratePerformanceReport
        
        if st.button("📥 Download Official Report", type="primary"):
            with st.spinner("Generating PDF report..."):
                # Generate report
                report_tool = GeneratePerformanceReport(candidate_id=candidate_id)
                result = report_tool.run()
                
                # Extract file path from result
                if "Report saved to:" in result:
                    import re
                    path_match = re.search(r"Report saved to: (.+)", result)
                    if path_match:
                        pdf_path = Path(path_match.group(1))
                        
                        if pdf_path.exists():
                            # Read PDF file
                            with open(pdf_path, "rb") as pdf_file:
                                pdf_bytes = pdf_file.read()
                            
                            # Provide download button
                            st.success("✅ Report generated successfully!")
                            st.download_button(
                                label="📥 Download Sensei Performance Report",
                                data=pdf_bytes,
                                file_name=f"sensei_report_{candidate_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf",
                                mime="application/pdf",
                                type="primary",
                                width='stretch'
                            )
                            
                            # Show summary
                            st.info(result)
                        else:
                            st.error("Report file was not created. Please check the error message above.")
                    else:
                        st.info(result)
                else:
                    st.error(result)
    except ImportError as e:
        st.warning(f"Report generator not available: {str(e)}. Please ensure reportlab is installed: pip install reportlab")
    except Exception as e:
        st.error(f"Error generating report: {str(e)}")
        import traceback
        if config.DEBUG:
            with st.expander("Debug Info"):
                st.code(traceback.format_exc())


def show_video_hub():
    """Display Video Hub with Triple-Track Coaching and Socratic assessment."""
    st.header("🎥 Video & Audio Hub - Triple-Track Coaching")

    # Get candidate ID from session state (must be set elsewhere, e.g., on login)
    if 'selected_candidate_id' not in st.session_state:
        st.error("No candidate selected. Please select a candidate from the 'Candidate View'.")
        # As a fallback for development, let's use a placeholder.
        # In production, this should be a hard error.
        st.session_state.selected_candidate_id = "CANDIDATE_001"
        st.info("Using placeholder candidate ID: CANDIDATE_001")

    candidate_id = st.session_state.selected_candidate_id

    # Track Selection
    st.subheader("📚 Select Your Track")
    track_options = {
        "Food/Tech": "🍜 Food/Tech (HACCP)",
        "Academic": "📖 Academic (JLPT)",
        "Tech & AI": "🤖 AI & Startup"
    }
    # Per GEMINI.md, Food/Tech is the default.
    if 'video_hub_track' not in st.session_state:
        st.session_state.video_hub_track = "Food/Tech"

    selected_track = st.radio(
        "Choose your coaching track:",
        options=list(track_options.keys()),
        format_func=lambda x: track_options[x],
        key="video_hub_track_radio",
        horizontal=True,
        index=list(track_options.keys()).index(st.session_state.video_hub_track)
    )
    st.session_state.video_hub_track = selected_track

    st.markdown("---")

    # --- Sidebar Controls ---
    with st.sidebar:
        st.header("Interactive Controls")
        interactive_mode = st.toggle('Interactive Mode', key='interactive_mode_toggle', value=False, help="Enable real-time Socratic assessment and feedback.")
        selected_language = st.radio('Language', ['En', 'Ne', 'Ja'], key='video_language_radio', horizontal=True)
        
        # --- Sensei Concierge Sidebar Container ---
        st.markdown("---")
        st.subheader("🎓 Sensei Concierge")
        
        # Initialize chat history in session state if not exists
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # Toggle to activate/deactivate Sensei chat
        sensei_chat_active = st.toggle(
            'Chat with Sensei',
            key='sensei_chat_active',
            value=False,
            help="Enable chat interface to interact with the Sensei during video playback."
        )
        
        # Input Method Toggle (Text or Audio)
        if sensei_chat_active:
            input_method = st.radio(
                "Input Method:",
                options=["text", "audio"],
                format_func=lambda x: "⌨️ Text" if x == "text" else "🎤 Audio",
                key="sensei_input_method",
                horizontal=True,
                help="Choose how to interact with Sensei: Text input or Audio recording"
            )
        else:
            input_method = "text"  # Default to text
        
        # Display chat interface if active
        if sensei_chat_active:
            st.markdown("**Chat with your Sensei:**")
            
            # Initialize video timestamp tracking
            if 'video_start_time' not in st.session_state:
                st.session_state.video_start_time = time.time()
            
            # Calculate timer_elapsed (maps to video timestamp)
            timer_elapsed = int(time.time() - st.session_state.video_start_time)
            
            # Load transcript from selected video
            transcript = ""
            if lessons and 'video_hub_lesson_select' in st.session_state and st.session_state.video_hub_lesson_select is not None:
                selected_lesson_idx = st.session_state.video_hub_lesson_select
                if selected_lesson_idx is not None and selected_lesson_idx < len(lessons):
                    selected_lesson = lessons[selected_lesson_idx]
                    video_path_str = selected_lesson.get("video_path")
                    video_path = Path(project_root) / video_path_str if video_path_str else None
                    
                    # Try alternative paths if needed
                    if video_path and not video_path.exists() and selected_lesson.get("module_name") == "Food/Tech":
                        video_filename = selected_lesson.get("video_filename", video_path.name)
                        alt_path = Path(project_root) / "static" / "videos" / "food_tech" / video_filename
                        if alt_path.exists():
                            video_path = alt_path
                        else:
                            alt_path2 = Path(project_root) / "assets" / "videos" / "food_tech" / video_filename
                            if alt_path2.exists():
                                video_path = alt_path2
                    
                    # Load transcript
                    if video_path and video_path.exists():
                        transcript_path = video_path.with_name(f"{video_path.stem}_En.txt")
                        if transcript_path.exists():
                            try:
                                transcript = transcript_path.read_text(encoding='utf-8').strip()
                            except Exception as e:
                                transcript = "Transcript file found but could not be read."
                        else:
                            transcript = "No transcript found for this video. Using default HACCP context."
                    else:
                        transcript = "Video not found. Using default HACCP context."
                else:
                    transcript = "Please select a lesson first. Using default HACCP context."
            else:
                transcript = "Please select a lesson first. Using default HACCP context."
            
            # Display chat history
            if st.session_state.chat_history:
                for message in st.session_state.chat_history:
                    if message['role'] == 'sensei':
                        with st.chat_message("assistant"):
                            st.write(message['content'])
                    elif message['role'] == 'user':
                        with st.chat_message("user"):
                            st.write(message['content'])
            
            # Initialize audio processing state
            if 'last_audio_hash' not in st.session_state:
                st.session_state.last_audio_hash = None
            if 'is_final_competency_mode' not in st.session_state:
                st.session_state.is_final_competency_mode = False
            
            # Chat input for user messages (Text mode)
            if input_method == "text":
                user_message = st.chat_input("Type your message to Sensei...")
            else:
                # Audio mode - mic_recorder
                user_message = None
                try:
                    from streamlit_mic_recorder import mic_recorder
                    
                    st.markdown("**🎤 Voice Input:**")
                    audio = mic_recorder(
                        start_prompt="🎤 Start Recording",
                        stop_prompt="🛑 Stop & Transcribe",
                        key="sensei_audio_recorder_sidebar",
                        use_container_width=True
                    )
                    
                    # Process audio when recording stops
                    if audio and isinstance(audio, dict) and 'bytes' in audio:
                        # Check if this is new audio (not already processed)
                        import hashlib
                        audio_hash = hashlib.md5(audio['bytes']).hexdigest()
                        
                        if audio_hash != st.session_state.last_audio_hash:
                            st.session_state.last_audio_hash = audio_hash
                            
                            # Show spinner during transcription
                            with st.spinner("🎤 Sensei is transcribing your voice..."):
                                # Transcribe audio
                                transcribed_text = transcribe_audio_with_gemini(audio['bytes'])
                                
                                if transcribed_text and not transcribed_text.startswith("Error"):
                                    # Check if we're in Final Competency mode
                                    if st.session_state.is_final_competency_mode:
                                        # Append to final competency response
                                        current_response = st.session_state.get('final_competency_response', '')
                                        st.session_state.final_competency_response = current_response + " " + transcribed_text if current_response else transcribed_text
                                        st.success(f"✅ Voice transcribed and added to Final Competency Statement: {transcribed_text}")
                                    else:
                                        # Append to chat history and trigger Sensei response
                                        st.session_state.chat_history.append({
                                            'role': 'user',
                                            'content': transcribed_text
                                        })
                                        
                                        # Check for vocabulary bonus terms
                                        found_terms = check_vocabulary_bonus_terms(transcribed_text, selected_track)
                                        if found_terms:
                                            update_mastery_score_for_vocabulary(candidate_id, selected_track, found_terms)
                                            st.toast(f"🎯 Bonus vocabulary detected: {', '.join(set(found_terms))}")
                                        
                                        # Get Sensei response immediately
                                        # Pass current page to determine persona
                                        current_page = st.session_state.get('page', 'Video Hub')
                                        sensei_response = get_sensei_response(
                                            user_input=transcribed_text,
                                            conversation_history=st.session_state.chat_history,
                                            transcript=transcript,
                                            timer_elapsed=timer_elapsed,
                                            track=selected_track,
                                            current_page=current_page
                                        )
                                        
                                        st.session_state.chat_history.append({
                                            'role': 'sensei',
                                            'content': sensei_response
                                        })
                                        
                                        st.success(f"✅ Voice transcribed: {transcribed_text}")
                                    
                                    # Rerun to update display
                                    st.rerun()
                                else:
                                    st.error(f"❌ Transcription failed: {transcribed_text}")
                except ImportError:
                    st.warning("⚠️ streamlit-mic-recorder not installed. Install with: pip install streamlit-mic-recorder")
                    st.info("💡 Please use text input mode instead.")
                except Exception as e:
                    st.error(f"❌ Audio recording error: {str(e)}")
            
            if user_message:
                # Add user message to chat history
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': user_message
                })
                
                # Check for vocabulary bonus terms and update mastery scores
                found_terms = check_vocabulary_bonus_terms(user_message, selected_track)
                if found_terms:
                    update_mastery_score_for_vocabulary(candidate_id, selected_track, found_terms)
                    # Show toast notification
                    st.toast(f"🎯 Bonus vocabulary detected: {', '.join(set(found_terms))}")
                
                # Get Sensei response using Socratic logic
                # Pass current page to determine persona
                current_page = st.session_state.get('page', 'Video Hub')
                sensei_response = get_sensei_response(
                    user_input=user_message,
                    conversation_history=st.session_state.chat_history,
                    transcript=transcript,
                    timer_elapsed=timer_elapsed,
                    track=selected_track,
                    current_page=current_page
                )
                
                st.session_state.chat_history.append({
                    'role': 'sensei',
                    'content': sensei_response
                })
                
                # Rerun to update the chat display
                st.rerun()
            
            # Display timer and phase indicator
            phase_indicator = "Evaluator" if timer_elapsed >= 180 else "Helpful Assistant"
            st.caption(f"⏱️ Timer: {timer_elapsed}s | Phase: {phase_indicator}")
            
            # Clear chat button
            if st.button("Clear Chat History", key="clear_sensei_chat"):
                st.session_state.chat_history = []
                st.session_state.video_start_time = time.time()  # Reset timer
                st.rerun()
            
            # Mastery Score Preview
            st.markdown("---")
            st.subheader("📊 Mastery Score Preview")
            mastery_scores, _ = calculate_mastery_scores(candidate_id)
            if selected_track in mastery_scores:
                track_scores = mastery_scores[selected_track]
                for skill, score in track_scores.items():
                    st.metric(
                        label=skill,
                        value=f"{score:.1f}%",
                        help=f"Current mastery level for {skill} in {selected_track} track"
                    )
            else:
                st.info("No mastery scores yet. Start chatting with Sensei to earn points!")
        else:
            # Show message when chat is inactive
            st.info("Toggle 'Chat with Sensei' to start a conversation during video playback.")
    
    # Load lessons after sidebar so selected_language is available
    lessons = load_video_lessons(selected_track, selected_language)

    # --- Main Video Hub UI ---

    if not lessons:
        st.warning(f"No video lessons found for track '{selected_track}' in language '{selected_language}'.")
        return

    # --- Socratic Assessment Callback ---
    def socratic_assessment_callback():
        """
        Triggered on lesson selection. This function initializes the Socratic questioning
        and stores the first question in the session state.
        """
        selected_lesson_index = st.session_state.get("video_hub_lesson_select")
        if selected_lesson_index is None or selected_lesson_index >= len(lessons):
            return

        selected_lesson = lessons[selected_lesson_index]
        video_name = selected_lesson.get("video_filename") # Assumes lesson dict has video_filename

        if not video_name:
            st.session_state.sensei_question_buffer = "Error: Lesson has no associated video file."
            return

        try:
            from agency.training_agent.video_socratic_assessment_tool import VideoSocraticAssessmentTool
            # The tool likely needs context, like the video identifier and candidate
            assessment_tool = VideoSocraticAssessmentTool(
                video_name=video_name,
                candidate_id=candidate_id,
                track=selected_track
            )
            # .run() should return the first question
            initial_question = assessment_tool.run()
            # Save ONLY the question to the buffer as requested
            st.session_state.sensei_question_buffer = initial_question
            st.toast(f"Sensei is ready to ask about {selected_lesson.get('lesson_title')}")
        except ImportError:
            st.session_state.sensei_question_buffer = "Error: Socratic assessment tool is not available."
        except Exception as e:
            st.session_state.sensei_question_buffer = f"Error starting assessment: {e}"


    # --- Lesson Selection and Video Player ---
    st.subheader("📹 Select Lesson")
    lesson_titles = [f"{lesson.get('lesson_number', i+1)}. {lesson.get('lesson_title', 'Untitled')}" for i, lesson in enumerate(lessons)]

    # The selectbox that triggers the Socratic assessment
    selected_lesson_idx = st.selectbox(
        "Choose a lesson to begin:",
        options=range(len(lesson_titles)),
        format_func=lambda x: lesson_titles[x],
        key="video_hub_lesson_select",
        on_change=socratic_assessment_callback,
        index=None, # Prompt user to select
        placeholder="Select a lesson..."
    )

    # Display video and transcript if a lesson is selected
    if selected_lesson_idx is not None:
        selected_lesson = lessons[selected_lesson_idx]
        video_path_str = selected_lesson.get("video_path") # Assumes load_video_lessons provides the relative path string
        
        video_path = Path(project_root) / video_path_str if video_path_str else None

        # If path doesn't exist, try alternative locations (for Food/Tech track)
        if video_path and not video_path.exists() and selected_lesson.get("module_name") == "Food/Tech":
            # Try static/videos/food_tech/ instead
            video_filename = selected_lesson.get("video_filename", video_path.name)
            alt_path = Path(project_root) / "static" / "videos" / "food_tech" / video_filename
            if alt_path.exists():
                video_path = alt_path
            else:
                # Try assets/videos/food_tech/ as another fallback
                alt_path2 = Path(project_root) / "assets" / "videos" / "food_tech" / video_filename
                if alt_path2.exists():
                    video_path = alt_path2

        if video_path and video_path.exists():
            # Center the video with padding using columns layout
            col_left, col_video, col_right = st.columns([1, 6, 1])
            with col_video:
                st.video(str(video_path))

            # Immersion-Bridge Logic: Fetch and display bilingual transcript
            # This part is from GEMINI.md
            transcript_path = video_path.with_name(f"{video_path.stem}_En.txt")
            if transcript_path.exists():
                with st.expander("Bilingual Transcript (English / Nepali)"):
                    try:
                        english_transcript = transcript_path.read_text(encoding='utf-8')
                        st.markdown("<h5>English Transcript</h5>", unsafe_allow_html=True)
                        st.markdown(f"<div style='height: 150px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; border-radius: 5px;'>{english_transcript}</div>", unsafe_allow_html=True)

                        # LLM Translation to Nepali
                        # This would require a call to an LLM, which I can't do directly here.
                        # I'll mock the call and put a placeholder.
                        st.markdown("<h5 style='margin-top: 15px;'>Nepali Translation (via LLM)</h5>", unsafe_allow_html=True)
                        nepali_transcript_placeholder = f"[[This is a placeholder for the Nepali translation of the transcript for '{video_path.name}'. The backend would use an LLM to generate this.]]"
                        st.markdown(f"<div style='height: 150px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; border-radius: 5px;'>{nepali_transcript_placeholder}</div>", unsafe_allow_html=True)

                    except Exception as e:
                        st.error(f"Error loading or translating transcript: {e}")
            else:
                st.info("No English transcript found for this video.")
            
            # --- Final Competency Submission Area ---
            st.markdown("---")
            with st.expander("📝 Final Competency Submission", expanded=False):
                st.markdown("**Submit your final response for competency assessment (up to 3,000 words):**")
                
                # Toggle for Final Competency mode (affects audio transcription destination)
                final_competency_mode = st.checkbox(
                    "🎤 Use voice input for Final Competency Statement",
                    key="final_competency_voice_mode",
                    help="When enabled, voice recordings will be appended to this text area instead of the chat."
                )
                st.session_state.is_final_competency_mode = final_competency_mode
                
                # Initialize final response in session state
                if 'final_competency_response' not in st.session_state:
                    st.session_state.final_competency_response = ""
                
                # Text area with live word counter
                final_response = st.text_area(
                    "Your final competency response:",
                    value=st.session_state.final_competency_response,
                    key="final_response_text_area",
                    height=300,
                    help="Write your comprehensive response here. The word counter will update in real-time."
                )
                
                # Live word counter
                word_count = len(final_response.split()) if final_response else 0
                max_words = 3000
                word_count_color = "green" if word_count <= max_words else "red"
                st.markdown(
                    f"<p style='text-align: right; color: {word_count_color}; font-weight: bold;'>"
                    f"Words: {word_count} / {max_words}</p>",
                    unsafe_allow_html=True
                )
                
                # Update session state
                st.session_state.final_competency_response = final_response
                
                # Submit button
                col_submit1, col_submit2, col_submit3 = st.columns([2, 1, 2])
                with col_submit2:
                    submit_clicked = st.button(
                        "🚀 Submit to Sensei",
                        key="submit_final_response",
                        type="primary",
                        use_container_width=True,
                        disabled=word_count == 0 or word_count > max_words
                    )
                
                if submit_clicked:
                    if word_count == 0:
                        st.error("Please enter a response before submitting.")
                    elif word_count > max_words:
                        st.error(f"Response exceeds {max_words} words. Please shorten your response.")
                    else:
                        # Show spinner and grade
                        with st.spinner("Grading in Progress... Please wait while Sensei evaluates your response."):
                            try:
                                from agency.training_agent.competency_grading_tool import CompetencyGradingTool
                                
                                # Map language code
                                lang_map = {"En": "en", "Ne": "ne", "Ja": "ja"}
                                language_code = lang_map.get(selected_language, "en")
                                
                                # Call CompetencyGradingTool
                                # Force Initialization: Tool initialization verified [cite: 2025-12-21]
                                grading_tool = CompetencyGradingTool()
                                
                                # The Call: Verify arguments match tool definition [cite: 2025-12-21]
                                # Get lesson name if available (for Video Hub)
                                current_lesson_name = st.session_state.get('current_lesson_name', None)
                                
                                grading_result = grading_tool.run(
                                    response=final_response,
                                    candidate_id=candidate_id,
                                    track=selected_track,
                                    language=language_code,
                                    lesson_name=current_lesson_name  # Pass lesson_name to match signature
                                )
                                
                                # Display results
                                st.success("✅ Assessment Complete! Your response has been graded.")
                                
                                # Show grading results
                                if isinstance(grading_result, dict):
                                    st.markdown("### 📊 Grading Results")
                                    col_grade1, col_grade2 = st.columns(2)
                                    with col_grade1:
                                        st.metric("Overall Grade", f"{grading_result.get('grade', 'N/A')}/10")
                                    with col_grade2:
                                        st.info(f"**Accuracy:** {grading_result.get('accuracy_feedback', 'No feedback')}")
                                    st.info(f"**Grammar:** {grading_result.get('grammar_feedback', 'No feedback')}")
                                
                                # Success toast
                                st.toast("🎉 Your competency assessment has been submitted successfully!")
                                
                                # Link to Progress Dashboard
                                st.markdown("---")
                                st.markdown("### 📊 View Your Progress")
                                st.info(
                                    "Your scores have been updated. Click the button below to view your detailed progress report."
                                )
                                if st.button("📈 Go to Progress Dashboard", key="go_to_progress_dashboard"):
                                    # Switch to Progress Dashboard page
                                    st.session_state.page = "Progress Dashboard"
                                    st.rerun()
                                
                                # Clear the response after successful submission
                                st.session_state.final_competency_response = ""
                                
                            except ImportError:
                                st.error("Competency grading tool is not available. Please ensure all dependencies are installed.")
                            except Exception as e:
                                st.error(f"An error occurred during grading: {str(e)}")
                                import traceback
                                if config.DEBUG:
                                    with st.expander("Debug Info"):
                                        st.code(traceback.format_exc())

        else:
            st.error(f"Video file not found for the selected lesson at path: {video_path}")


    # --- Sensei Guardrails & Interactive Mode Logic ---
    if interactive_mode:
        st.markdown("---")
        st.subheader("🎙️ Socratic Practice Zone")

        # Initialize timer and word count for the session
        if 'audio_start_time' not in st.session_state:
            st.session_state.audio_start_time = time.time()
        if 'word_count' not in st.session_state:
            st.session_state.word_count = 0 # This should be updated by the chat input component

        # Display the question from the buffer
        if 'sensei_question_buffer' in st.session_state:
            st.info(f"**Sensei asks:** {st.session_state.sensei_question_buffer}")
        else:
            st.info("Select a lesson to begin your Socratic practice.")

        # Placeholder for chat/voice input to respond to Sensei
        # This component would update `st.session_state.word_count` and `st.session_state.dialogue_history`
        user_response = st.text_area("Your response to Sensei:", key="socratic_response_input", height=150)
        if st.button("Submit Response"):
             # In a real app, this would trigger more logic
             st.session_state.word_count += len(user_response.split())
             # Append to history, get next question, etc.
             st.toast("Response recorded.")


        # Guardrail Timer & Trigger
        elapsed_time = time.time() - st.session_state.audio_start_time
        countdown = 180 - elapsed_time

        st.sidebar.metric("Session Timer", f"{int(countdown)}s remaining")
        st.sidebar.metric("Session Word Count", f"{st.session_state.word_count} words")


        if countdown <= 0 or st.session_state.word_count > 3000:
            st.warning("Session limit reached. Activating Competency Grading Tool...")
            try:
                # Assume dialogue_history is being populated by the chat component
                if 'dialogue_history' in st.session_state:
                    from agency.training_agent.competency_grading_tool import CompetencyGradingTool
                    # Convert dialogue_history to a single response string
                    dialogue_text = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in st.session_state.dialogue_history]) if st.session_state.dialogue_history else ""
                    # Force Initialization: Tool initialization verified [cite: 2025-12-21]
                    grading_tool = CompetencyGradingTool()
                    # The Call: Verify arguments match tool definition [cite: 2025-12-21]
                    grading_result = grading_tool.run(
                        response=dialogue_text,
                        candidate_id=candidate_id,
                        track="Academic",  # Default track
                        language="en",  # Default language
                        lesson_name=None  # Explicitly pass lesson_name to match signature
                    )
                    st.success("Competency assessment complete! Your Progress Report has been updated.")
                    st.info(f"Grading Result: {grading_result}")

                    # Reset the guardrails for the next session
                    del st.session_state['audio_start_time']
                    st.session_state.word_count = 0
                    del st.session_state.sensei_question_buffer
                else:
                    st.error("Could not grade competency: No dialogue history found in session.")

            except Exception as e:
                st.error(f"An error occurred during competency grading: {e}")

def load_transcript_and_translate(video_filename: str, video_path: str) -> tuple[str | None, str | None]:
    """
    Load English transcript file and generate Nepali translation using Gemini.
    
    Returns: (english_transcript, nepali_transcript) or (None, None) if not found
    """
    try:
        # Extract base filename (without extension)
        base_name = Path(video_filename).stem
        
        # Determine transcript path based on video path location
        if "static/videos" in str(video_path):
            # New Immersion-Bridge structure: static/videos/[track]/[file]
            video_dir = Path(__file__).parent.parent / Path(video_path).parent
        else:
            # Old structure fallback: assets/videos/[track]/[file]
            video_dir = Path(__file__).parent.parent / Path(video_path).parent
        
        transcript_path = video_dir / f"{base_name}_En.txt"
        
        if not transcript_path.exists():
            return None, None
        
        # Read English transcript
        english_transcript = transcript_path.read_text(encoding='utf-8').strip()
        
        if not english_transcript:
            return None, None
        
        # Generate Nepali translation using Gemini
        nepali_transcript = None
        try:
            from google import genai
            if config.GEMINI_API_KEY:
                client = genai.Client(api_key=config.GEMINI_API_KEY)
                prompt = f"""
Translate the following English text to Nepali (नेपाली). 
Keep technical terms and proper nouns in their original form if commonly used.
Return only the translation, no explanations.

English text:
{english_transcript}"""
                
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=prompt
                )
                nepali_transcript = response.text.strip()
        except Exception as e:
            logger.warning(f"Error translating transcript to Nepali: {e}")
            nepali_transcript = None
        
        return english_transcript, nepali_transcript
        
    except Exception as e:
        logger.warning(f"Error loading transcript: {e}")
        return None, None


def load_video_lessons(track: str, language: str) -> list[dict]:
    """
    Load video lessons for the specified track and language.
    
    First tries to load from database (Syllabus model), then falls back to file system.
    """
    lessons = []
    
    # Try to load from database
    if SYLLABUS_AVAILABLE:
        db = get_db_session()
        try:
            syllabus_lessons = db.query(Syllabus).filter(
                Syllabus.track == track,
                Syllabus.language == language
            ).order_by(Syllabus.sequence_order, Syllabus.lesson_number).all()
            
            for lesson in syllabus_lessons:
                # Normalize video_path to fix incorrect directory names (e.g., "food/tech" -> "food_tech", "tech" -> "food_tech")
                video_path = lesson.video_path
                if video_path:
                    # Fix common path issues
                    video_path = video_path.replace("food/tech", "food_tech")
                    video_path = video_path.replace("food\\tech", "food_tech")
                    # Fix "tech" directory to "food_tech" for Food/Tech track
                    if track == "Food/Tech" and "/tech/" in video_path:
                        video_path = video_path.replace("/tech/", "/food_tech/")
                    if track == "Food/Tech" and "\\tech\\" in video_path:
                        video_path = video_path.replace("\\tech\\", "\\food_tech\\")
                    # Ensure .mp4 extension (fix truncated extensions like .mp)
                    if video_path.endswith(".mp") and not video_path.endswith(".mp4"):
                        video_path = video_path + "4"
                
                lessons.append({
                    'id': lesson.id,
                    'lesson_title': lesson.lesson_title,
                    'lesson_description': lesson.lesson_description,
                    'lesson_number': lesson.lesson_number,
                    'video_path': video_path,
                    'video_filename': lesson.video_filename,
                    'topic': lesson.topic,
                    'duration_minutes': lesson.duration_minutes,
                    'difficulty_level': lesson.difficulty_level,
                    'module_name': lesson.module_name,
                    'source': 'database'
                })
        except Exception as e:
            logger.warning(f"Error loading lessons from database: {e}")
        finally:
            db.close()
    
    # Fallback to file system if no database lessons found
    if not lessons:
        # Try new Immersion-Bridge directory structure first: static/videos/[track]/
        track_dir_map = {
            "Food/Tech": "food_tech",
            "Academic": "academic",
            "Care-giving": "care_giving",
            "Tech/AI": "tech_ai"
        }
        track_dir = track_dir_map.get(track, track.lower().replace("-", "_"))
        
        # Special handling for Academic track: check subfolders n5, n4, n3 [cite: 2025-12-21]
        if track == "Academic":
            # Point to assets/videos/academic/ with lowercase subfolders [cite: 2025-12-21]
            academic_base = Path(__file__).parent.parent / "assets" / "videos" / "academic"
            found_in_static = False
            
            # Path Debug: Show search path in sidebar [cite: 2025-12-21]
            target_path = str(academic_base)
            st.sidebar.write(f'🔍 Searching path: {target_path}')
            
            # Check for n5, n4, n3 subfolders (case-insensitive) [cite: 2025-12-21]
            jlpt_levels = ["n5", "n4", "n3"]
            level_display_map = {"n5": "N5", "n4": "N4", "n3": "N3"}  # Map to display format
            
            # Get all subdirectories and match case-insensitively
            if academic_base.exists():
                actual_subdirs = [d.name for d in academic_base.iterdir() if d.is_dir()]
                for level in jlpt_levels:
                    # Case-insensitive matching [cite: 2025-12-21]
                    matching_dir = None
                    for actual_dir in actual_subdirs:
                        if actual_dir.lower() == level.lower():
                            matching_dir = actual_dir
                            break
                    
                    if matching_dir:
                        level_dir = academic_base / matching_dir
                        # Path Debug: Show level directory path [cite: 2025-12-21]
                        st.sidebar.write(f'🔍 Checking level dir: {level_dir}')
                        
                        # Try to find video files first
                        video_files = list(level_dir.glob("*.mp4")) + list(level_dir.glob("*.webm")) + list(level_dir.glob("*.ogg"))
                        
                        # Fallback Logic: If no video files, use .txt files [cite: 2025-12-20]
                        if not video_files:
                            txt_files = list(level_dir.glob("*_En.txt")) + list(level_dir.glob("*.txt"))
                            if txt_files:
                                st.sidebar.write(f'⚠️ No video files found, using .txt files: {len(txt_files)} found')
                                
                                # Lesson Data: Special handling for specific lessons [cite: 2025-12-21]
                                # Define custom lesson titles and ordering for known files
                                custom_lesson_map = {
                                    'n5_kitchen_safety': {
                                        'title': 'N5 Kitchen Safety & Hygiene',
                                        'order': 2  # Ensure it appears as lesson 2
                                    },
                                    'n5_particles_wa_ga': {
                                        'title': 'N5 Particles Wa Ga',
                                        'order': 1  # Ensure it appears as lesson 1
                                    }
                                }
                                
                                # Sort files with custom ordering
                                def get_file_sort_key(txt_file):
                                    base_name = txt_file.stem.replace("_En", "").replace("_en", "")
                                    if base_name in custom_lesson_map:
                                        return (custom_lesson_map[base_name]['order'], base_name)
                                    return (999, base_name)  # Unknown files go to end
                                
                                sorted_txt_files = sorted(txt_files, key=get_file_sort_key)
                                
                                for idx, txt_file in enumerate(sorted_txt_files, 1):
                                    # Extract base name (remove _En.txt or .txt)
                                    base_name = txt_file.stem.replace("_En", "").replace("_en", "")
                                    
                                    # File Link: Map n5_kitchen_safety to correct path [cite: 2025-12-20, 2025-12-21]
                                    # Check if this is the kitchen safety lesson
                                    if base_name == 'n5_kitchen_safety':
                                        # Ensure transcript path points to assets/videos/academic/n5/n5_kitchen_safety.txt
                                        transcript_path = str(txt_file)
                                        if not transcript_path.endswith('n5_kitchen_safety.txt'):
                                            # Construct correct path
                                            transcript_path = str(level_dir / 'n5_kitchen_safety.txt')
                                        
                                        lesson_title = 'N5 Kitchen Safety & Hygiene'
                                    elif base_name in custom_lesson_map:
                                        lesson_title = custom_lesson_map[base_name]['title']
                                        transcript_path = str(txt_file)
                                    else:
                                        # Default title generation
                                        lesson_title = f"{level_display_map.get(level, level.upper())} - {base_name.replace('_', ' ').title()}"
                                        transcript_path = str(txt_file)
                                    
                                    # Create a placeholder video path (will be handled gracefully by UI)
                                    video_path = f"assets/videos/academic/{matching_dir}/{base_name}.mp4"
                                    display_level = level_display_map.get(level, level.upper())
                                    
                                    lessons.append({
                                        'id': f"file_{level}_{idx}_txt",
                                        'lesson_title': lesson_title,
                                        'lesson_description': f"JLPT {display_level} lesson from Academic track (Transcript only)",
                                        'lesson_number': idx,
                                        'video_path': None,  # No video file
                                        'video_filename': None,
                                        'transcript_path': transcript_path,  # Store transcript path
                                        'topic': f'jlpt_{level}',
                                        'duration_minutes': None,
                                        'difficulty_level': display_level,
                                        'module_name': f"Academic ({display_level})",
                                        'source': 'filesystem_txt'
                                    })
                                continue  # Skip video file processing for this level
                        
                        # Process video files if found
                        for idx, video_file in enumerate(sorted(video_files), 1):
                            video_path = f"assets/videos/academic/{matching_dir}/{video_file.name}"
                            display_level = level_display_map.get(level, level.upper())
                            lessons.append({
                                'id': f"file_{level}_{idx}",
                                'lesson_title': f"{display_level} - {video_file.stem.replace('_', ' ').title()}",
                                'lesson_description': f"JLPT {display_level} lesson from Academic track",
                                'lesson_number': idx,
                                'video_path': video_path,
                                'video_filename': video_file.name,
                                'topic': f'jlpt_{level}',
                                'duration_minutes': None,
                                'difficulty_level': display_level,
                                'module_name': f"Academic ({display_level})",
                                'source': 'filesystem'
                            })
        else:
            # Try static/videos/[track]/ first (Immersion-Bridge standard)
            video_dir = Path(__file__).parent.parent / "static" / "videos" / track_dir
            found_in_static = True
            
            # Path Debug: Show search path in sidebar [cite: 2025-12-21]
            target_path = str(video_dir)
            st.sidebar.write(f'🔍 Searching path: {target_path}')
            
            if not video_dir.exists():
                # Fallback to old assets/videos/ structure
                # Use track_dir_map to ensure correct directory name (e.g., "food_tech" not "food/tech")
                video_dir = Path(__file__).parent.parent / "assets" / "videos" / track_dir
                found_in_static = False
                # Path Debug: Show fallback path [cite: 2025-12-21]
                target_path = str(video_dir)
                st.sidebar.write(f'🔍 Fallback path: {target_path}')
            
            if video_dir.exists():
                # Try to find video files first
                video_files = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.webm")) + list(video_dir.glob("*.ogg"))
                
                # Fallback Logic: If no video files, use .txt files [cite: 2025-12-20]
                if not video_files:
                    txt_files = list(video_dir.glob("*_En.txt")) + list(video_dir.glob("*.txt"))
                    if txt_files:
                        st.sidebar.write(f'⚠️ No video files found, using .txt files: {len(txt_files)} found')
                        for idx, txt_file in enumerate(sorted(txt_files), 1):
                            # Extract base name (remove _En.txt or .txt)
                            base_name = txt_file.stem.replace("_En", "").replace("_en", "")
                            # Determine video path based on which directory was found
                            if found_in_static:
                                video_path = f"static/videos/{track_dir}/{base_name}.mp4"
                            else:
                                video_path = f"assets/videos/{track_dir}/{base_name}.mp4"
                            
                            lessons.append({
                                'id': f"file_{idx}_txt",
                                'lesson_title': base_name.replace("_", " ").title(),
                                'lesson_description': f"Video lesson from {track} track (Transcript only)",
                                'lesson_number': idx,
                                'video_path': None,  # No video file
                                'video_filename': None,
                                'transcript_path': str(txt_file),  # Store transcript path
                                'topic': 'knowledge_base',  # Default topic
                                'duration_minutes': None,
                                'difficulty_level': None,
                                'module_name': track,
                                'source': 'filesystem_txt'
                            })
                else:
                    # Process video files if found
                    for idx, video_file in enumerate(sorted(video_files), 1):
                        # Determine video path based on which directory was found
                        if found_in_static:
                            video_path = f"static/videos/{track_dir}/{video_file.name}"
                        else:
                            video_path = f"assets/videos/{track_dir}/{video_file.name}"
                        
                        lessons.append({
                            'id': f"file_{idx}",
                            'lesson_title': video_file.stem.replace("_", " ").title(),
                            'lesson_description': f"Video lesson from {track} track",
                            'lesson_number': idx,
                            'video_path': video_path,
                            'video_filename': video_file.name,
                            'topic': 'knowledge_base',  # Default topic
                            'duration_minutes': None,
                            'difficulty_level': None,
                            'module_name': track,
                            'source': 'filesystem'
                        })
    
    return lessons


def load_mastery_stats():
    """
    UI Sync: Load mastery stats from persistent JSON file [cite: 2025-12-21]
    Returns total_word_count from assets/user_progress.json
    """
    import json
    import os
    from pathlib import Path
    
    progress_file = Path(__file__).parent.parent / "assets" / "user_progress.json"
    
    if progress_file.exists():
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("total_word_count", 0)
        except (json.JSONDecodeError, KeyError, IOError):
            return 0
    return 0


def show_academic_hub():
    """Display Academic Hub with JLPT-focused Socratic assessment."""
    st.header("📖 Academic Hub - JLPT Mastery")
    
    # Mastery Dashboard: Display total word count at top of Academic Hub [cite: 2025-12-21]
    total_count = load_mastery_stats()
    st.metric(
        label="Global Vocabulary Count",
        value=total_count,
        delta="Target: 3,000"
    )
    st.markdown("---")
    
    # Get candidate ID from session state
    if 'selected_candidate_id' not in st.session_state:
        st.error("No candidate selected. Please select a candidate from the 'Candidate View'.")
        st.session_state.selected_candidate_id = "CANDIDATE_001"
        st.info("Using placeholder candidate ID: CANDIDATE_001")
    
    candidate_id = st.session_state.selected_candidate_id
    
    # --- Sidebar Controls (mirroring Video Hub structure) ---
    with st.sidebar:
        st.header("Academic Hub Controls")
        selected_language = st.radio('Language', ['En', 'Ne', 'Ja'], key='academic_language_radio', horizontal=True)
        
        # Level Filter Selectbox (N5, N4, N3) [cite: 2025-12-21]
        st.markdown("---")
        st.subheader("📚 JLPT Level Filter")
        if 'academic_jlpt_level' not in st.session_state:
            st.session_state.academic_jlpt_level = "N5"
        
        level_filter = st.selectbox(
            "Select JLPT Level:",
            options=["N5", "N4", "N3"],
            key="academic_level_filter",
            index=["N5", "N4", "N3"].index(st.session_state.academic_jlpt_level),
            help="Filter lessons by JLPT level (N5, N4, or N3) [cite: 2025-12-21]"
        )
        st.session_state.academic_jlpt_level = level_filter
        selected_level = level_filter  # Use for filtering lessons
        
        # --- Sensei Concierge Sidebar Container (mirroring Video Hub) ---
        st.markdown("---")
        st.subheader("🎓 JLPT Sensei")
        
        # Remove Toggle Dependency: Force sensei_chat_active = True for Academic Hub [cite: 2025-12-21]
        sensei_chat_active = True  # Always active for JLPT mastery
        
        # Input Method Toggle (Text or Audio) - mirroring Video Hub
        input_method = st.radio(
            "Input Method:",
            options=["text", "audio"],
            format_func=lambda x: "⌨️ Text" if x == "text" else "🎤 Audio",
            key="academic_input_method",
            horizontal=True,
            help="Choose how to interact with Sensei: Text input or Audio recording"
        )
        
        # Persistent Greeting: Display static trilingual greeting block in sidebar [cite: 2025-12-20, 2025-12-21]
        # Verify Sidebar Placement: Ensure Sensei Introduction is inside with st.sidebar: block [cite: 2025-12-21]
        # UTF-8 encoding is used by default in Python 3 strings
        st.markdown("---")
        # Get lesson name from session state if available (will be updated when lesson is selected)
        current_lesson_display = st.session_state.get('academic_current_lesson_name', 'Your JLPT Lesson')
        
        with st.expander("🎓 Sensei Introduction", expanded=True):
            st.markdown("### Welcome to Your JLPT Lesson!")
            st.markdown("""
            **English:** Welcome! I'm your JLPT Sensei. Let's explore Japanese grammar together.
            
            **日本語 (Japanese):** ようこそ！私はあなたのJLPT先生です。
            
            **नेपाली (Nepali):** स्वागत छ! म तपाईंको JLPT Sensei हुँ।
            """)
            st.caption(f"📚 Current Lesson: {current_lesson_display}")
    
    # Load lessons for Academic track
    lessons = load_video_lessons("Academic", selected_language)
    
    # Filter lessons by selected JLPT level
    if lessons:
        lessons = [lesson for lesson in lessons if selected_level in lesson.get('module_name', '') or selected_level in lesson.get('difficulty_level', '')]
    
    if not lessons:
        st.warning(f"No lessons found for JLPT {selected_level}.")
        return
    
    # Lesson Selection
    st.subheader("📹 Select Lesson")
    lesson_titles = [f"{lesson.get('lesson_number', i+1)}. {lesson.get('lesson_title', 'Untitled')}" for i, lesson in enumerate(lessons)]
    
    selected_lesson_idx = st.selectbox(
        "Choose a lesson:",
        options=range(len(lesson_titles)),
        format_func=lambda x: lesson_titles[x],
        key="academic_lesson_select",
        index=None,
        placeholder="Select a lesson..."
    )
    
    # Display video and chat interface
    if selected_lesson_idx is not None:
        selected_lesson = lessons[selected_lesson_idx]
        # Correct Lesson Name formatting: Match dropdown format 'N5 Particles Wa Ga' [cite: 2025-12-21]
        lesson_number = selected_lesson.get("lesson_number", selected_lesson_idx + 1)
        lesson_title = selected_lesson.get("lesson_title", "Untitled Lesson")
        lesson_name = f"{lesson_number}. {lesson_title}"  # Format: "1. N5 Particles Wa Ga"
        lesson_id = selected_lesson.get("id", f"lesson_{selected_lesson_idx}")
        video_path_str = selected_lesson.get("video_path")
        video_path = Path(project_root) / video_path_str if video_path_str else None
        
        # Clear chat history if a different lesson is selected
        if 'academic_current_lesson_id' not in st.session_state:
            st.session_state.academic_current_lesson_id = None
        
        if st.session_state.academic_current_lesson_id != lesson_id:
            # Reset Logic: Clear chat history when new lesson is selected [cite: 2025-12-21]
            st.session_state.academic_chat_history = []  # Explicitly set to empty list for fresh Socratic discussion
            st.session_state.academic_current_lesson_id = lesson_id
            st.session_state.academic_video_start_time = time.time()  # Reset timer
            # Session State: Update lesson name for sidebar display [cite: 2025-12-21]
            st.session_state.academic_current_lesson_name = lesson_name
        
        # Load transcript (handle both video-based and transcript-only lessons)
        # Transcript Variable: Ensure current_lesson_transcript is populated from .txt file [cite: 2025-12-20]
        current_lesson_transcript = ""
        transcript_path = None
        
        # Check if this is a transcript-only lesson (no video file)
        if video_path_str is None or (video_path and not video_path.exists()):
            # Try to load from transcript_path if available (transcript-only lessons)
            transcript_path_str = selected_lesson.get("transcript_path")
            if transcript_path_str:
                transcript_path = Path(transcript_path_str)
                if transcript_path.exists():
                    try:
                        current_lesson_transcript = transcript_path.read_text(encoding='utf-8').strip()
                    except Exception as e:
                        current_lesson_transcript = "Transcript file found but could not be read."
                else:
                    current_lesson_transcript = f"JLPT {selected_level} lesson on Japanese grammar and kanji."
            else:
                # Fallback: try to find transcript based on lesson title
                current_lesson_transcript = f"JLPT {selected_level} lesson on Japanese grammar and kanji."
        else:
            # Video-based lesson: load transcript from video directory
            if video_path and video_path.exists():
                # Center the video
                col_left, col_video, col_right = st.columns([1, 6, 1])
                with col_video:
                    st.video(str(video_path))
                
                # Load transcript
                transcript_path = video_path.with_name(f"{video_path.stem}_En.txt")
                if transcript_path.exists():
                    try:
                        current_lesson_transcript = transcript_path.read_text(encoding='utf-8').strip()
                    except Exception as e:
                        current_lesson_transcript = "Transcript file found but could not be read."
                else:
                    current_lesson_transcript = f"JLPT {selected_level} lesson on Japanese grammar and kanji."
            else:
                current_lesson_transcript = f"JLPT {selected_level} lesson on Japanese grammar and kanji."
        
        # Store transcript in session state for chat interface
        st.session_state.current_lesson_transcript = current_lesson_transcript
        
        # Persistent Greeting: Static greeting is now displayed in chat sidebar, no auto-trigger needed [cite: 2025-12-20, 2025-12-21]
        
        # Chat interface (mirroring Video Hub exactly) [cite: 2025-12-21]
        if sensei_chat_active:
            st.markdown("---")
            st.subheader("💬 Chat with JLPT Sensei")
            
            # Initialize video timestamp tracking (mirroring Video Hub)
            if 'academic_video_start_time' not in st.session_state:
                st.session_state.academic_video_start_time = time.time()
            
            # Calculate timer_elapsed (maps to video timestamp)
            timer_elapsed = int(time.time() - st.session_state.academic_video_start_time)
            
            # Initialize audio processing state (MD5 hash check - mirroring Video Hub) [cite: 2025-12-21]
            # Debug Check: Ensure MD5 hash check doesn't block first recording [cite: 2025-12-21]
            if 'academic_last_audio_hash' not in st.session_state:
                st.session_state.academic_last_audio_hash = None  # Initialize to None, not empty string
            
            # Session State Alignment: Initialize academic_audio_buffer to avoid conflicts [cite: 2025-12-21]
            if 'academic_audio_buffer' not in st.session_state:
                st.session_state.academic_audio_buffer = None
            
            # Get current lesson transcript from session state
            current_lesson_transcript = st.session_state.get('current_lesson_transcript', '')
            
            # Note: Persistent Greeting is now displayed in the sidebar (moved for better placement) [cite: 2025-12-21]
            
            # Manual Chat Spark: Add button to start Socratic discussion [cite: 2025-12-21]
            if len(st.session_state.academic_chat_history) == 0:
                if st.button("💬 Start Socratic Discussion", key="start_academic_discussion", type="primary", use_container_width=True):
                    # Verify transcript is populated
                    if not current_lesson_transcript or not current_lesson_transcript.strip():
                        current_lesson_transcript = st.session_state.get('current_lesson_transcript', '')
                    
                    if current_lesson_transcript and current_lesson_transcript.strip():
                        current_page = st.session_state.get('current_page', '📖 Academic Hub')
                        
                        # Simplified Trilingual Prompt: Direct and simple [cite: 2025-12-20]
                        initial_greeting_prompt = f"""Greeting: English first, then Japanese, then Nepali. Then ask one question about "{lesson_name}".

**Lesson Transcript:**
{current_lesson_transcript}

**Your Response (trilingual greeting + one Socratic question):**
"""
                        
                        # Call get_sensei_response with simplified prompt
                        with st.spinner("🎓 Sensei is preparing your first question..."):
                            initial_greeting = get_sensei_response(
                                user_input=initial_greeting_prompt,
                                conversation_history=[],
                                transcript=current_lesson_transcript,
                                timer_elapsed=0,
                                track="Academic",
                                current_page=current_page
                            )
                        
                        st.session_state.academic_chat_history.append({
                            'role': 'sensei',
                            'content': initial_greeting
                        })
                        
                        st.rerun()
                    else:
                        st.warning("⚠️ Lesson transcript not available. Please select a lesson first.")
            
            # Display chat history
            if st.session_state.academic_chat_history:
                for message in st.session_state.academic_chat_history:
                    if message['role'] == 'sensei':
                        with st.chat_message("assistant"):
                            st.write(message['content'])
                    elif message['role'] == 'user':
                        with st.chat_message("user"):
                            st.write(message['content'])
            if 'academic_is_final_competency_mode' not in st.session_state:
                st.session_state.academic_is_final_competency_mode = False
            
            # Chat input for user messages (Text mode)
            if input_method == "text":
                user_message = st.chat_input("Type your message to JLPT Sensei...")
            else:
                # Audio mode - mic_recorder (mirroring Video Hub)
                user_message = None
                try:
                    from streamlit_mic_recorder import mic_recorder
                    
                    st.markdown("**🎤 Voice Input:**")
                    # Recording Indicator: Add key and styling consistent with Concierge [cite: 2025-12-21]
                    audio = mic_recorder(
                        start_prompt="🎤 Start Recording",
                        stop_prompt="🛑 Stop & Transcribe",
                        key="academic_mic",  # Use academic_mic key for consistency [cite: 2025-12-21]
                        use_container_width=True
                    )
                    
                    # Microphone Status: Recording indicator placed directly above chat input area [cite: 2025-12-21]
                    # Check if mic_recorder is currently recording
                    if audio is not None:
                        # If audio exists, it means recording has completed
                        if isinstance(audio, dict) and 'bytes' in audio:
                            st.success("✅ Recording complete! Processing...")
                        elif isinstance(audio, dict):
                            # Recording might be in progress - show status directly above chat input
                            st.info("🎙️ Recording...")  # Microphone Status: Directly above chat input [cite: 2025-12-21]
                    else:
                        # No recording state - show ready state
                        st.caption("💡 Click the button above to start recording")
                    
                    # Process audio when recording stops (with MD5 hash check) [cite: 2025-12-21]
                    # Session State Alignment: Save to academic_audio_buffer to avoid conflicts [cite: 2025-12-21]
                    if audio and isinstance(audio, dict) and 'bytes' in audio:
                        # Store audio in academic-specific buffer
                        st.session_state.academic_audio_buffer = audio['bytes']
                        
                        # Check if this is new audio (not already processed) - MD5 hash check
                        # Debug Check: Ensure MD5 hash check doesn't block first recording [cite: 2025-12-21]
                        import hashlib
                        audio_hash = hashlib.md5(audio['bytes']).hexdigest()
                        
                        # Allow processing if hash is None (first recording) or different from last
                        if st.session_state.academic_last_audio_hash is None or audio_hash != st.session_state.academic_last_audio_hash:
                            st.session_state.academic_last_audio_hash = audio_hash
                            
                            # Show spinner during transcription
                            with st.spinner("🎤 Sensei is transcribing your voice..."):
                                # Transcribe audio from academic_audio_buffer
                                transcribed_text = transcribe_audio_with_gemini(st.session_state.academic_audio_buffer)
                                
                                if transcribed_text and not transcribed_text.startswith("Error"):
                                    # Check if we're in Final Competency mode
                                    if st.session_state.academic_is_final_competency_mode:
                                        # Append to final competency response
                                        current_response = st.session_state.get('academic_competency_response', '')
                                        st.session_state.academic_competency_response = current_response + " " + transcribed_text if current_response else transcribed_text
                                        st.success(f"✅ Voice transcribed and added to Final Competency Statement: {transcribed_text}")
                                    else:
                                        # Microphone-to-Chat: Automatically append transcription to chat history [cite: 2025-12-21]
                                        st.session_state.academic_chat_history.append({
                                            'role': 'user',
                                            'content': transcribed_text
                                        })
                                        
                                        # Get Sensei response immediately with Academic Hub persona
                                        # Transcript-to-Sensei: Ensure current_lesson_transcript is passed as system prompt context [cite: 2025-12-20]
                                        current_page = st.session_state.get('current_page', '📖 Academic Hub')
                                        current_lesson_transcript = st.session_state.get('current_lesson_transcript', '')
                                        
                                        # Ensure transcript is populated before calling get_sensei_response
                                        if not current_lesson_transcript or not current_lesson_transcript.strip():
                                            # Fallback: try to get from session state
                                            current_lesson_transcript = st.session_state.get('current_lesson_transcript', '')
                                        
                                        sensei_response = get_sensei_response(
                                            user_input=transcribed_text,
                                            conversation_history=st.session_state.academic_chat_history,
                                            transcript=current_lesson_transcript,  # Transcript passed as system context [cite: 2025-12-20]
                                            timer_elapsed=timer_elapsed,
                                            track="Academic",
                                            current_page=current_page
                                        )
                                        
                                        st.session_state.academic_chat_history.append({
                                            'role': 'sensei',
                                            'content': sensei_response
                                        })
                                        
                                        st.success(f"✅ Voice transcribed: {transcribed_text}")
                                    
                                    # Rerun to update display
                                    st.rerun()
                                else:
                                    st.error(f"❌ Transcription failed: {transcribed_text}")
                except ImportError:
                    st.warning("⚠️ streamlit-mic-recorder not installed. Install with: pip install streamlit-mic-recorder")
                    st.info("💡 Please use text input mode instead.")
                except Exception as e:
                    st.error(f"❌ Audio recording error: {str(e)}")
            
            if user_message:
                # Add user message to chat history
                st.session_state.academic_chat_history.append({
                    'role': 'user',
                    'content': user_message
                })
                
                # Get Sensei response using Socratic logic with Academic Hub persona
                current_page = st.session_state.get('current_page', '📖 Academic Hub')
                current_lesson_transcript = st.session_state.get('current_lesson_transcript', '')
                sensei_response = get_sensei_response(
                    user_input=user_message,
                    conversation_history=st.session_state.academic_chat_history,
                    transcript=current_lesson_transcript,
                    timer_elapsed=timer_elapsed,
                    track="Academic",
                    current_page=current_page
                )
                
                st.session_state.academic_chat_history.append({
                    'role': 'sensei',
                    'content': sensei_response
                })
                
                # Rerun to update the chat display
                st.rerun()
            
            # Display timer and phase indicator
            phase_indicator = "Evaluator" if timer_elapsed >= 180 else "Helpful Assistant"
            st.caption(f"⏱️ Timer: {timer_elapsed}s | Phase: {phase_indicator}")
            
            # Clear chat button
            if st.button("Clear Chat History", key="clear_academic_chat"):
                st.session_state.academic_chat_history = []
                st.session_state.academic_video_start_time = time.time()  # Reset timer
                st.rerun()
            
            # Mastery Score Preview (mirroring Video Hub)
            st.markdown("---")
            st.subheader("📊 Mastery Score Preview")
            mastery_scores, _ = calculate_mastery_scores(candidate_id)
            if "Academic" in mastery_scores:
                track_scores = mastery_scores["Academic"]
                for skill, score in track_scores.items():
                    st.metric(
                        label=skill,
                        value=f"{score:.1f}%",
                        help=f"Current mastery level for {skill} in Academic track"
                    )
            else:
                st.info("No mastery scores yet. Start chatting with Sensei to earn points!")
        else:
            # Show message when chat is inactive
            st.info("Toggle 'Chat with Sensei' to start a conversation during video playback.")
        
        # Final Competency Submission (mirroring Video Hub exactly) [cite: 2025-12-21]
        # Always accessible, regardless of chat state
        st.markdown("---")
        with st.expander("📝 Final Competency Submission", expanded=False):
                st.markdown("**Submit your final response for JLPT competency assessment (up to 3,000 words):**")
                
                # Toggle for Final Competency mode (affects audio transcription destination)
                final_competency_mode = st.checkbox(
                    "🎤 Use voice input for Final Competency Statement",
                    key="academic_final_competency_voice_mode",
                    help="When enabled, voice recordings will be appended to this text area instead of the chat."
                )
                st.session_state.academic_is_final_competency_mode = final_competency_mode
                
                # Initialize final response in session state
                if 'academic_competency_response' not in st.session_state:
                    st.session_state.academic_competency_response = ""
                
                # Text area with live word counter (mirroring Video Hub) [cite: 2025-12-21]
                final_response = st.text_area(
                    "Your final competency response:",
                    value=st.session_state.academic_competency_response,
                    key="academic_final_response_text_area",
                    height=300,
                    help="Write your comprehensive response here. The word counter will update in real-time."
                )
                
                # Live word counter (mirroring Video Hub) [cite: 2025-12-21]
                word_count = len(final_response.split()) if final_response else 0
                max_words = 3000
                word_count_color = "green" if word_count <= max_words else "red"
                st.markdown(
                    f"<p style='text-align: right; color: {word_count_color}; font-weight: bold;'>"
                    f"Words: {word_count} / {max_words}</p>",
                    unsafe_allow_html=True
                )
                
                # Update session state
                st.session_state.academic_competency_response = final_response
                
                # Submit button (mirroring Video Hub)
                col_submit1, col_submit2, col_submit3 = st.columns([2, 1, 2])
                with col_submit2:
                    submit_clicked = st.button(
                        "🚀 Submit to Sensei",
                        key="submit_academic_response",
                        type="primary",
                        use_container_width=True,
                        disabled=word_count == 0 or word_count > max_words
                    )
                
                if submit_clicked:
                    if word_count == 0:
                        st.error("Please enter a response before submitting.")
                    elif word_count > max_words:
                        st.error(f"Response exceeds {max_words} words. Please shorten your response.")
                    else:
                        # Show spinner and grade
                        with st.spinner("Grading in Progress... Please wait while Sensei evaluates your response."):
                            try:
                                from agency.training_agent.competency_grading_tool import CompetencyGradingTool
                                
                                # Map language code
                                lang_map = {"En": "en", "Ne": "ne", "Ja": "ja"}
                                language_code = lang_map.get(selected_language, "en")
                                
                                # Call CompetencyGradingTool
                                # Force Initialization: Tool initialization verified [cite: 2025-12-21]
                                grading_tool = CompetencyGradingTool()
                                
                                # Get lesson name from session state for progress persistence [cite: 2025-12-21]
                                current_lesson_name = st.session_state.get('academic_current_lesson_name', 'Unknown Lesson')
                                
                                grading_result = grading_tool.run(
                                    response=final_response,
                                    candidate_id=candidate_id,
                                    track="Academic",
                                    language=language_code,
                                    lesson_name=current_lesson_name  # Pass lesson name for progress persistence
                                )
                                
                                # Display results
                                st.success("✅ Assessment Complete! Your response has been graded.")
                                
                                # Show grading results
                                if isinstance(grading_result, dict):
                                    st.markdown("### 📊 Grading Results")
                                    col_grade1, col_grade2 = st.columns(2)
                                    with col_grade1:
                                        st.metric("Overall Grade", f"{grading_result.get('grade', 'N/A')}/10")
                                    with col_grade2:
                                        st.info(f"**Accuracy:** {grading_result.get('accuracy_feedback', 'No feedback')}")
                                    st.info(f"**Grammar:** {grading_result.get('grammar_feedback', 'No feedback')}")
                                
                                # Success toast
                                st.toast("🎉 Your competency assessment has been submitted successfully!")
                                
                                # Link to Progress Dashboard
                                st.markdown("---")
                                st.markdown("### 📊 View Your Progress")
                                st.info(
                                    "Your scores have been updated. Click the button below to view your detailed progress report."
                                )
                                if st.button("📈 Go to Progress Dashboard", key="go_to_progress_from_academic"):
                                    # Switch to Progress Dashboard page
                                    st.session_state.page = "Progress"
                                    st.session_state.current_page = "Progress"
                                    st.rerun()
                                
                                # Clear the response after successful submission
                                st.session_state.academic_competency_response = ""
                                
                            except ImportError:
                                st.error("Competency grading tool is not available. Please ensure all dependencies are installed.")
                            except Exception as e:
                                st.error(f"An error occurred during grading: {str(e)}")
                                import traceback
                                if config.DEBUG:
                                    with st.expander("Debug Info"):
                                        st.code(traceback.format_exc())


def show_live_simulator():
    """Live simulator for testing Socratic Sensei."""
    st.header("🎓 Live Simulator - Socratic Sensei")

    st.info(
        "Test the Socratic Sensei by interacting with the LanguageCoachAgent through the FastAPI endpoints. "
        "This simulates candidate interactions with the Phase 2 immersive training features."
    )

    # API endpoint configuration - hardcode to 127.0.0.1:8000 for stable routing
    api_base_url = "http://127.0.0.1:8000"

    # Candidate selection
    db = get_db_session()
    try:
        candidates = db.query(Candidate).all()
        candidate_ids = [c.candidate_id for c in candidates]
    finally:
        db.close()

    if not candidate_ids:
        st.warning("No candidates found. Create a candidate first.")
        return

    selected_candidate = st.selectbox("Select Candidate", candidate_ids)

    # Mode selection
    mode = st.radio("Interaction Mode", ["Start Lesson", "Process Voice"])

    if mode == "Start Lesson":
        st.subheader("📚 Start Lesson")

        col1, col2 = st.columns(2)
        with col1:
            module_type = st.selectbox("Module Type", ["jlpt", "kaigo"])
        with col2:
            if module_type == "jlpt":
                jlpt_level = st.selectbox("JLPT Level", ["N5", "N4", "N3"])
                kaigo_module = None
            else:
                jlpt_level = None
                kaigo_module = st.selectbox("Kaigo Module", ["kaigo_basics", "communication_skills", "physical_care"])

        if st.button("🚀 Generate Lesson Script"):
            import requests

            payload = {
                "candidate_id": selected_candidate,
                "module_type": module_type,
                "jlpt_level": jlpt_level,
                "kaigo_module": kaigo_module,
            }

            try:
                response = requests.post(f"{api_base_url}/start-lesson", json=payload, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    st.success("Lesson script generated successfully!")
                    st.code(result.get("lesson_script", ""), language="markdown")
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Connection error: {str(e)}")

    elif mode == "Process Voice":
        st.subheader("🎤 Process Voice (Nepali -> Japanese)")

        st.info("Upload an audio file or provide base64-encoded audio data.")

        audio_input_method = st.radio("Input Method", ["Upload File", "Base64 String"])

        tts_voice = st.selectbox("TTS Voice", ["alloy", "shimmer"])

        if audio_input_method == "Upload File":
            uploaded_file = st.file_uploader("Upload Audio File", type=["wav", "mp3", "m4a"])
            if uploaded_file and st.button("🎤 Process Voice"):
                import base64
                import requests

                audio_bytes = uploaded_file.read()
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

                payload = {
                    "candidate_id": selected_candidate,
                    "audio_base64": audio_base64,
                    "tts_voice": tts_voice,
                }

                try:
                    response = requests.post(f"{api_base_url}/process-voice", json=payload, timeout=30)
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("success"):
                            st.success("Voice processed successfully!")
                            st.write("**Transcribed Text (Nepali):**")
                            st.write(result.get("transcribed_text", "N/A"))
                            st.write("**Translated Text (Japanese):**")
                            st.write(result.get("translated_text", "N/A"))
                            st.write("**Audio Output Path:**")
                            st.code(result.get("audio_output_path", "N/A"))
                        else:
                            st.error(f"Error: {result.get('message', 'Unknown error')}")
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
        else:
            audio_base64 = st.text_area("Base64 Audio String", height=100)
            if audio_base64 and st.button("🎤 Process Voice"):
                import requests

                payload = {
                    "candidate_id": selected_candidate,
                    "audio_base64": audio_base64,
                    "tts_voice": tts_voice,
                }

                try:
                    response = requests.post(f"{api_base_url}/process-voice", json=payload, timeout=30)
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("success"):
                            st.success("Voice processed successfully!")
                            st.write("**Transcribed Text (Nepali):**")
                            st.write(result.get("transcribed_text", "N/A"))
                            st.write("**Translated Text (Japanese):**")
                            st.write(result.get("translated_text", "N/A"))
                            st.write("**Audio Output Path:**")
                            st.code(result.get("audio_output_path", "N/A"))
                        else:
                            st.error(f"Error: {result.get('message', 'Unknown error')}")
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")


def show_financial_ledger():
    """Display financial ledger summary."""
    st.header("💰 Financial Ledger")

    summary = load_financial_summary()

    # Check for database errors
    if "error" in summary:
        error_msg = summary["error"]
        if "password authentication failed" in error_msg.lower():
            st.error("""
            **Database Connection Error: Password Authentication Failed**
            
            Please check your PostgreSQL credentials in the `.env` file.
            Update `DATABASE_URL` with the correct username and password.
            """)
        elif "could not connect" in error_msg.lower() or "connection refused" in error_msg.lower():
            st.error("""
            **Database Connection Error: Cannot Connect to PostgreSQL**
            
            Ensure PostgreSQL is running and accessible.
            """)
        else:
            st.error(f"**Database Error:** {error_msg}")
        return

    # Key metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Payments", summary["total_payments"])
    with col2:
        st.metric("Total Amount Collected", f"${summary['total_amount']:,.2f}")
    with col3:
        st.metric("Unique Candidates", summary["unique_candidates"])

    # Provider breakdown
    if summary["provider_breakdown"]:
        st.subheader("💳 Payment Provider Breakdown")
        provider_df = pd.DataFrame(
            [
                {
                    "Provider": provider.title(),
                    "Count": data["count"],
                    "Amount": f"${data['amount']:,.2f}",
                }
                for provider, data in summary["provider_breakdown"].items()
            ]
        )
        st.dataframe(provider_df, width='stretch', hide_index=True)

    # Recent payments
    if summary["recent_payments"]:
        st.subheader("📋 Recent Payments")
        recent_df = pd.DataFrame(
            [
                {
                    "Candidate ID": payment[0],
                    "Amount": f"{payment[1]} {payment[2]}",
                    "Provider": payment[3].title(),
                    "Status": payment[4].title(),
                    "Date": payment[5].strftime("%Y-%m-%d %H:%M:%S") if payment[5] else "N/A",
                }
                for payment in summary["recent_payments"]
            ]
        )
        st.dataframe(recent_df, width='stretch', hide_index=True)


def show_socratic_history(dialogue_history: list | None, candidate_id: str):
    """
    Display Socratic training history as a chat interface with Japanese/Nepali support.
    Includes Play Audio buttons for each question.
    """
    if not dialogue_history:
        st.info("No Socratic training history yet. Start a training session to see questions here.")
        return
    
    # Create a chat-like interface
    st.markdown("""
    <style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .question-bubble {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .answer-bubble {
        background-color: #f1f8e9;
        border-left: 4px solid #8bc34a;
    }
    </style>
    """, unsafe_allow_html=True)
    
    for i, entry in enumerate(dialogue_history):
        if "question" not in entry:
            continue
        
        question_data = entry.get("question", {})
        question_en = question_data.get("english", "")
        question_ja = question_data.get("japanese", "")
        question_ne = question_data.get("nepali", "")
        audio_files = entry.get("audio_files", {})
        timestamp = entry.get("question_timestamp", "")
        
        # Question bubble
        with st.container():
            st.markdown(f'<div class="chat-message question-bubble">', unsafe_allow_html=True)
            
            # Question number and timestamp
            st.markdown(f"**Question {i+1}** ({timestamp[:10] if timestamp else 'N/A'})")
            
            # English question
            st.markdown("**🇬🇧 English:**")
            st.write(question_en)
            
            # Japanese question with audio
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown("**🇯🇵 Japanese:**")
                st.write(question_ja)
            with col2:
                if audio_files.get("japanese"):
                    audio_path = Path(__file__).parent.parent / audio_files["japanese"]
                    if audio_path.exists():
                        with open(audio_path, "rb") as audio_file:
                            audio_bytes = audio_file.read()
                            st.audio(audio_bytes, format="audio/mp3")
                    else:
                        st.info("Audio not found")
            
            # Nepali question with audio
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown("**🇳🇵 Nepali:**")
                st.write(question_ne)
            with col2:
                if audio_files.get("nepali"):
                    audio_path = Path(__file__).parent.parent / audio_files["nepali"]
                    if audio_path.exists():
                        with open(audio_path, "rb") as audio_file:
                            audio_bytes = audio_file.read()
                            st.audio(audio_bytes, format="audio/mp3")
                    else:
                        st.info("Audio not found")
            
            # Learning objective
            if entry.get("learning_objective"):
                st.markdown(f"**📚 Learning Objective:** {entry['learning_objective']}")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Candidate answer (if provided)
        if entry.get("candidate_answer"):
            with st.container():
                st.markdown(f'<div class="chat-message answer-bubble">', unsafe_allow_html=True)
                st.markdown("**💭 Your Answer:**")
                st.write(entry["candidate_answer"])
                answer_timestamp = entry.get("answer_timestamp", "")
                if answer_timestamp:
                    st.caption(f"Answered: {answer_timestamp[:19] if len(answer_timestamp) > 19 else answer_timestamp}")
                
                # Show grading if available
                if entry.get("grading"):
                    grading = entry["grading"]
                    grade = grading.get("grade", 0)
                    grade_color = "🟢" if grade >= 8 else "🟡" if grade >= 6 else "🔴"
                    st.metric("Overall Grade", f"{grade_color} {grade}/10")
                    
                    st.markdown("**✅ Accuracy:**")
                    st.write(grading.get("accuracy_feedback", "N/A"))
                    
                    st.markdown("**📝 Grammar:**")
                    st.write(grading.get("grammar_feedback", "N/A") )
                    
                    st.markdown("**🎯 Pronunciation Hint:**")
                    st.info(grading.get("pronunciation_hint", "N/A") )
                
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Record answer section (if no answer yet or allow re-recording)
        question_id = entry.get("question_id", f"question_{i}")
        st.markdown("**🎤 Record Your Answer:**")
        
        # Language selection for recording
        record_language = st.radio(
            "Select Language",
            ["Japanese (ja-JP)", "Nepali (ne-NP)"],
            key=f"lang_{question_id}",
            horizontal=True
        )
        language_code = "ja-JP" if "Japanese" in record_language else "ne-NP"
        
        # Mic recorder
        try:
            from streamlit_mic_recorder import mic_recorder
            
            audio_data = mic_recorder(
                key=f"recorder_{question_id}",
                start_prompt="🎤 Click to Record",
                stop_prompt="⏹️ Click to Stop",
                just_once=False,
            )
            
            if audio_data:
                # Show recorded audio player
                st.audio(audio_data["bytes"], format="audio/wav")
                
                # Process audio when recorded
                if st.button(f"📤 Submit & Grade Answer", key=f"submit_{question_id}"):
                    import base64
                    from agency.training_agent.language_coaching_tool import LanguageCoachingTool
                    
                    # Convert audio_data to base64
                    audio_bytes = audio_data["bytes"]
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                    
                    # Get expected answer from question data if available
                    expected_answer = None
                    if entry.get("question"):
                        expected_answer = entry["question"].get("english", "")
                    
                    # Get concept reference for better context
                    if entry.get("concept_reference"):
                        concept_title = entry["concept_reference"].get("concept_title", "")
                        if concept_title and not expected_answer:
                            expected_answer = f"Explain the meaning of '{concept_title}' in Japanese caregiving context."
                    
                    # Create tool instance
                    transcript_tool = LanguageCoachingTool(
                        candidate_id=candidate_id,
                        audio_base64=audio_base64,
                        language_code=language_code,
                        question_id=question_id,
                        expected_answer=expected_answer,
                    )
                    
                    # Step 1: Transcribe audio
                    with st.spinner("🎤 Transcribing your audio..."):
                        try:
                            # Transcribe audio
                            audio_content = base64.b64decode(audio_base64)
                            transcript = transcript_tool._transcribe_audio(audio_content, language_code)
                            
                            if not transcript:
                                st.error("❌ Failed to transcribe audio. Please check your microphone and try again.")
                                st.stop()
                            
                            # Display transcript immediately
                            st.markdown("**📝 What the AI heard:**")
                            st.info(f'"{transcript}"')
                            st.markdown("---")
                            
                        except Exception as e:
                            st.error(f"❌ Transcription error: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
                            st.stop()
                    
                    # Step 2: Grade response
                    with st.spinner("🤖 AI is grading your answer..."):
                        try:
                            # Grade the transcript
                            grading_result = transcript_tool._grade_response_with_gemini(
                                transcript=transcript,
                                language=language_code,
                                expected_answer=expected_answer
                            )
                            
                            # Step 3: Save to database
                            from database.db_manager import SessionLocal, CurriculumProgress
                            from datetime import datetime, timezone
                            
                            db = SessionLocal()
                            try:
                                curriculum = db.query(CurriculumProgress).filter(
                                    CurriculumProgress.candidate_id == candidate_id
                                ).first()
                                
                                if not curriculum:
                                    curriculum = CurriculumProgress(candidate_id=candidate_id)
                                    db.add(curriculum)
                                    db.flush()
                                
                                # Update dialogue_history
                                dialogue_history = curriculum.dialogue_history or []
                                
                                # Find the question entry if question_id is provided
                                entry_updated = False
                                if question_id:
                                    for entry in dialogue_history:
                                        if entry.get("question_id") == question_id:
                                            # Update existing entry with response
                                            entry["candidate_answer"] = transcript
                                            entry["answer_timestamp"] = datetime.now(timezone.utc).isoformat()
                                            entry["grading"] = {
                                                "grade": grading_result["grade"],
                                                "accuracy_feedback": grading_result["accuracy_feedback"],
                                                "grammar_feedback": grading_result["grammar_feedback"],
                                                "pronunciation_hint": grading_result["pronunciation_hint"],
                                                "grading_timestamp": datetime.now(timezone.utc).isoformat(),
                                            }
                                            entry_updated = True
                                            break
                                
                                if not entry_updated:
                                    # Create new entry
                                    dialogue_history.append({
                                        "question_id": question_id,
                                        "candidate_answer": transcript,
                                        "answer_timestamp": datetime.now(timezone.utc).isoformat(),
                                        "grading": {
                                            "grade": grading_result["grade"],
                                            "accuracy_feedback": grading_result["accuracy_feedback"],
                                            "grammar_feedback": grading_result["grammar_feedback"],
                                            "pronunciation_hint": grading_result["pronunciation_hint"],
                                            "grading_timestamp": datetime.now(timezone.utc).isoformat(),
                                        },
                                    })
                                
                                # Save to database
                                curriculum.dialogue_history = dialogue_history
                                db.commit()
                                
                                # Also record in student_performance table
                                from agency.student_progress_agent.tools import RecordProgress
                                
                                # Try to get word_title from dialogue_history
                                word_title = None
                                category = None
                                if question_id:
                                    for entry in dialogue_history:
                                        if entry.get("question_id") == question_id:
                                            if "concept_reference" in entry:
                                                word_title = entry["concept_reference"].get("concept_title")
                                            break
                                
                                if word_title:
                                    record_tool = RecordProgress(
                                        candidate_id=candidate_id,
                                        word_title=word_title,
                                        score=grading_result["grade"],
                                        feedback=f"Accuracy: {grading_result['accuracy_feedback']}\nGrammar: {grading_result['grammar_feedback']}",
                                        accuracy_feedback=grading_result["accuracy_feedback"],
                                        grammar_feedback=grading_result["grammar_feedback"],
                                        pronunciation_hint=grading_result["pronunciation_hint"],
                                        transcript=transcript,
                                        language_code=language_code,
                                        category=category or "caregiving_vocabulary",
                                    )
                                    record_tool.run()
                                
                                st.success("✅ Answer graded and saved successfully!")
                                
                                # Display grading results
                                st.markdown("**📊 AI Grading Results:**")
                                grade = grading_result.get("grade", 0)
                                grade_color = "🟢" if grade >= 8 else "🟡" if grade >= 6 else "🔴"
                                st.metric("Overall Grade", f"{grade_color} {grade}/10")
                                
                                st.markdown("**✅ Accuracy Feedback:**")
                                st.write(grading_result.get("accuracy_feedback", "N/A"))
                                
                                st.markdown("**📝 Grammar Feedback:**")
                                st.write(grading_result.get("grammar_feedback", "N/A") )
                                
                                st.markdown("**🎯 Pronunciation Hint:**")
                                st.info(grading_result.get("pronunciation_hint", "N/A") )
                                
                            except Exception as e:
                                db.rollback()
                                st.error(f"❌ Database error: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc())
                            finally:
                                db.close()
                            
                            # Refresh to show updated results
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Grading error: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
        except ImportError:
            st.warning("⚠️ streamlit-mic-recorder not installed. Please install it to record answers.")
            st.code("pip install streamlit-mic-recorder")
        
        st.markdown("---")


def show_admin_dashboard():
    """Display Admin Monitoring Center dashboard."""
    # Check admin mode (double check)
    if not st.session_state.get("admin_mode", False):
        st.error("🔒 Admin Mode must be enabled to access this page.")
        return
    
    # System Health & Security Strip
    st.markdown(
        """
        <div class="system-health-strip">
            <h2>🛡️ System Health & Security</h2>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.header("Admin Monitoring Center")
    
    # Platform Mode Toggle (Training Mode vs Official Test-Cell Mode)
    st.markdown("---")
    st.subheader("🎛️ Platform Mode Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        platform_mode = st.radio(
            "Select Platform Mode",
            ["Training Mode", "Official Test-Cell Mode"],
            key="platform_mode",
            help="Training Mode: Standard learning environment. Official Test-Cell Mode: Strict assessment environment with enhanced security."
        )
    
    with col2:
        if platform_mode == "Training Mode":
            st.info("📚 **Training Mode Active**\n\n- Standard grading thresholds\n- Learning-focused feedback\n- Practice sessions enabled")
        else:
            st.warning("🔒 **Official Test-Cell Mode Active**\n\n- Strict grading standards (XPLOREKODO_STRICT)\n- Enhanced security measures\n- Official assessment environment")
    
    # Store mode in session state
    st.session_state.platform_mode = platform_mode
    
    # Display current grading standard
    st.markdown(f"**Current Grading Standard:** `{config.GRADING_STANDARD}`")
    if config.GRADING_STANDARD == "XPLOREKODO_STRICT":
        st.caption("⚠️ Strict grading enabled: 15% harder threshold than JLPT standard")
    else:
        st.caption("ℹ️ Standard JLPT grading thresholds")
    
    st.markdown("---")
    
    # Get critical logs for notification badge
    db = get_db_session()
    try:
        from utils.activity_logger import ActivityLogger
        from database.db_manager import ActivityLog
        
        critical_logs = ActivityLogger.get_recent_critical_logs(hours=1)
        
        # Notification Badge
        if critical_logs:
            st.error(f"🚨 **{len(critical_logs)} Critical Event(s) in Last Hour**")
            st.markdown("---")
        
        # System Notifications Section
        st.subheader("📢 System Notifications")
        
        if critical_logs:
            for log in critical_logs[:10]:
                severity_color = "🔴" if log.severity == "Error" else "🟡"
                st.markdown(
                    f"""
                    {severity_color} **{log.severity}** - {log.event_type}
                    - **Time:** {log.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
                    - **User:** {log.user_id or 'System'}
                    - **Message:** {log.message or 'No message'}
                    """,
                    unsafe_allow_html=True)
                if log.event_metadata:
                    with st.expander("View Details"):
                        st.json(log.event_metadata)
                st.markdown("---")
        else:
            st.success("✅ No critical events in the last hour. System is running smoothly.")
        
        st.markdown("---")
        
        # Cheating Risk Visualizer Section
        st.subheader("🚨 Cheating Risk Monitor")
        
        # Get cheating risk events
        db_risk = get_db_session()
        try:
            from database.db_manager import ActivityLog
            cheating_risk_logs = db_risk.query(ActivityLog).filter(
                ActivityLog.event_type == "Cheating_Risk",
                ActivityLog.severity == "Warning"
            ).order_by(ActivityLog.timestamp.desc()).limit(5).all()
            
            if cheating_risk_logs:
                st.markdown(
                    '<div class="cheating-risk-section">',
                    unsafe_allow_html=True
                )
                
                # Scrollable list container
                st.markdown('<div class="scrollable-list">', unsafe_allow_html=True)
                
                for log in cheating_risk_logs:
                    metadata = log.event_metadata or {}
                    risk_score = metadata.get("cheating_risk_score", 0)
                    
                    # Determine risk level
                    if risk_score >= 80:
                        risk_class = "high"
                        risk_label = "HIGH"
                    elif risk_score >= 70:
                        risk_class = "medium"
                        risk_label = "MEDIUM"
                    else:
                        risk_class = "low"
                        risk_label = "LOW"
                    
                    indicators = metadata.get("indicators", [])
                    
                    st.markdown(
                        f"""
                        <div class="risk-event-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                <strong style="color: #D32F2F;">🚨 Cheating Risk Detected</strong>
                                <span class="risk-score {risk_class}">{risk_label}: {risk_score}/100</span>
                            </div>
                            <div style="color: #757575; font-size: 0.875rem; margin-bottom: 0.5rem;">
                                <strong>Time:</strong> {log.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}<br>
                                <strong>User:</strong> {log.user_id or 'System'}<br>
                                <strong>Question:</strong> {metadata.get('question_type', 'N/A')} (Q{metadata.get('question_number', 'N/A')})
                            </div>
                            <div style="color: #212121; margin-top: 0.5rem;">
                                <strong>Indicators:</strong>
                                <ul style="margin: 0.25rem 0; padding-left: 1.5rem;">
                                    {''.join([f'<li>{ind}</li>' for ind in indicators[:3]])}
                                </ul>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                st.markdown('</div>', unsafe_allow_html=True)  # Close scrollable-list
                st.markdown('</div>', unsafe_allow_html=True)  # Close cheating-risk-section
            else:
                st.info("✅ No high-risk cheating events detected in recent assessments.")
        except Exception as e:
            st.warning(f"Could not load cheating risk logs: {str(e)}")
            st.info("✅ No high-risk cheating events detected in recent assessments.")
        finally:
            if 'db_risk' in locals():
                db_risk.close()
        
        st.markdown("---")
        
        # Curriculum Distribution Chart
        st.subheader("📊 Curriculum Distribution")
        
        db_curriculum = get_db_session()
        try:
            from database.db_manager import KnowledgeBase
            
            # Get word counts by category
            categories = db.query(KnowledgeBase.category).distinct().all()
            category_counts = {}
            
            for (category,) in categories:
                if category:
                    count = db.query(KnowledgeBase).filter(
                        KnowledgeBase.category == category
                    ).count()
                    category_counts[category] = count
            
            if category_counts:
                # Group into tracks
                caregiving_count = category_counts.get("caregiving_vocabulary", 0)
                academic_count = category_counts.get("jlpt_n5_vocabulary", 0) + category_counts.get("jlpt_n4_vocabulary", 0)
                tech_count = sum(count for cat, count in category_counts.items() if "tech" in cat.lower() or "ai" in cat.lower())
                
                # Create bar chart data
                chart_data = pd.DataFrame({
                    "Track": ["Caregiving", "Academic (N5/N4)", "Tech"],
                    "Word Count": [caregiving_count, academic_count, tech_count]
                })
                
                st.markdown('<div class="curriculum-chart-container">', unsafe_allow_html=True)
                st.bar_chart(chart_data.set_index("Track"), width='stretch')
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Show breakdown
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Caregiving Words", caregiving_count)
                with col2:
                    st.metric("Academic Words", academic_count)
                with col3:
                    st.metric("Tech Words", tech_count)
            else:
                st.info("No curriculum data available. Seed the knowledge base to see distribution.")
        except Exception as e:
            st.warning(f"Could not load curriculum distribution: {str(e)}")
        finally:
            if 'db_curriculum' in locals():
                db_curriculum.close()
        
        st.markdown("---")
        
        # Audit Log Section
        st.subheader("📋 Audit Log")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_user_id = st.text_input("Filter by User ID", "", key="audit_user_filter")
        with col2:
            filter_event_type = st.selectbox(
                "Filter by Event Type",
                ["All", "Grading", "Briefing", "Error", "API_Call"],
                key="audit_event_filter"
            )
        with col3:
            filter_severity = st.selectbox(
                "Filter by Severity",
                ["All", "Info", "Warning", "Error"],
                key="audit_severity_filter"
            )
        
        # Get audit logs
        user_id_filter = filter_user_id if filter_user_id else None
        event_type_filter = filter_event_type if filter_event_type != "All" else None
        
        audit_logs = ActivityLogger.get_audit_logs(
            user_id=user_id_filter,
            event_type=event_type_filter,
            limit=100
        )
        
        # Apply severity filter
        if filter_severity != "All":
            audit_logs = [log for log in audit_logs if log.severity == filter_severity]
        
        if audit_logs:
            # Create DataFrame for display
            log_data = []
            for log in audit_logs:
                log_data.append({
                    "Timestamp": log.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                    "User ID": log.user_id or "System",
                    "Event Type": log.event_type,
                    "Severity": log.severity,
                    "Message": log.message or "N/A",
                })
            
            df_logs = pd.DataFrame(log_data)
            st.dataframe(df_logs, width='stretch', hide_index=True)
            
            # Detailed view for selected log
            if len(audit_logs) > 0:
                st.markdown("---")
                st.subheader("🔍 Log Details")
                
                selected_index = st.selectbox(
                    "Select Log Entry",
                    range(len(audit_logs)),
                    format_func=lambda x: f"{audit_logs[x].timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {audit_logs[x].event_type} ({audit_logs[x].severity})"
                )
                
                selected_log = audit_logs[selected_index]
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Timestamp:** {selected_log.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    st.write(f"**User ID:** {selected_log.user_id or 'System'}")
                with col2:
                    st.write(f"**Event Type:** {selected_log.event_type}")
                    st.write(f"**Severity:** {selected_log.severity}")
                
                st.write(f"**Message:** {selected_log.message or 'No message'}")
                
                if selected_log.event_metadata:
                    st.write("**Metadata:**")
                    st.json(selected_log.event_metadata)
                
                # Special handling for Grading events
                if selected_log.event_type == "Grading" and selected_log.event_metadata:
                    st.markdown("---")
                    st.subheader("📊 Grading Details")
                    
                    metadata = selected_log.event_metadata
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Word", metadata.get("word_title", "N/A"))
                    with col2:
                        score = metadata.get("score", 0)
                        score_color = "🟢" if score >= 8 else "🟡" if score >= 6 else "🔴"
                        st.metric("Score", f"{score_color} {score}/10")
                    with col3:
                        st.metric("User", selected_log.user_id or "N/A")
                    
                    if metadata.get("transcript"):
                        st.write("**Student's Answer (Transcript):**")
                        st.info(f'"{metadata["transcript"]}"')
                    
                    if metadata.get("feedback"):
                        feedback = metadata["feedback"]
                        if feedback.get("accuracy"):
                            st.write("**Accuracy Feedback:**")
                            st.write(feedback["accuracy"])
                        if feedback.get("grammar"):
                            st.write("**Grammar Feedback:**")
                            st.write(feedback["grammar"])
                        if feedback.get("pronunciation"):
                            st.write("**Pronunciation Hint:**")
                            st.info(feedback["pronunciation"])
        else:
            st.info("No audit logs found matching the filters.")
        
    except ImportError:
        st.error("Activity logger not available. Please ensure utils/activity_logger.py exists.")
    except Exception as e:
        st.error(f"Error loading admin dashboard: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


def show_phase_unlock_progress(candidate_id: str):
    """
    Display phase unlock progress bar showing how close the student is to the next phase.
    """
    if not PHASE_TOOL_AVAILABLE:
        st.info("Phase progression system not available.")
        return
    
    db = get_db_session()
    try:
        # Get current phase
        phase_tool = GetCurrentPhase(candidate_id=candidate_id)
        phase_result = phase_tool.run()
        
        import json
        phase_info = json.loads(phase_result)
        
        current_phase = phase_info.get("current_phase", 1)
        phase_unlocked = phase_info.get("phase_unlocked", [True, False, False])
        next_phase_progress = phase_info.get("next_phase_progress", {})
        metrics = phase_info.get("metrics", {})
        
        # Display current phase
        phase_names = {
            1: "Phase 1: N5 Basics",
            2: "Phase 2: Caregiving Essentials",
            3: "Phase 3: Scenario Mastery"
        }
        
        st.markdown(f"**Current Phase:** {phase_names.get(current_phase, f'Phase {current_phase}')}")
        
        # Show phase unlock status
        col1, col2, col3 = st.columns(3)
        with col1:
            status = "✅ Unlocked" if phase_unlocked[0] else "🔒 Locked"
            st.metric("Phase 1", status)
        with col2:
            status = "✅ Unlocked" if len(phase_unlocked) > 1 and phase_unlocked[1] else "🔒 Locked"
            st.metric("Phase 2", status)
        with col3:
            status = "✅ Unlocked" if len(phase_unlocked) > 2 and phase_unlocked[2] else "🔒 Locked"
            st.metric("Phase 3", status)
        
        # Show progress to next phase
        if current_phase < 3 and next_phase_progress:
            next_phase = next_phase_progress.get("phase")
            overall_progress = next_phase_progress.get("overall_progress", 0)
            requirements = next_phase_progress.get("requirements", {})
            
            if next_phase:
                st.markdown(f"**Progress to Phase {next_phase}:**")
                
                # Progress bar
                st.progress(
                    overall_progress / 100.0,
                    text=f"{overall_progress:.1f}% Complete"
                )
                
                # Show requirements
                st.markdown("**Requirements:**")
                for req_name, req_value in requirements.items():
                    st.write(f"  • {req_name.replace('_', ' ').title()}: {req_value}")
        
        elif current_phase == 3:
            st.success("🎉 Maximum phase reached! You've unlocked all curriculum phases.")
        
        # Show current metrics
        st.markdown("**Current Metrics:**")
        if metrics.get("n5_count", 0) > 0:
            st.write(f"  • N5 Average: {metrics.get('n5_avg', 0):.1f}/10 ({metrics.get('n5_count', 0)} words)")
        if metrics.get("caregiving_count", 0) > 0:
            st.write(f"  • Caregiving Average: {metrics.get('caregiving_avg', 0):.1f}/10 ({metrics.get('caregiving_count', 0)} words)")
        
    except Exception as e:
        st.error(f"Error loading phase progress: {str(e)}")
    finally:
        db.close()


def show_learning_curve(candidate_id: str):
    """
    Display learning curve chart showing average scores over time.
    Uses student_performance table to calculate daily/weekly averages.
    """
    db = get_db_session()
    try:
        # Get all performance records for this candidate, ordered by date
        performances = db.query(StudentPerformance).filter(
            StudentPerformance.candidate_id == candidate_id
        ).order_by(StudentPerformance.created_at).all()
        
        if not performances:
            st.info("No performance data yet. Start practicing to see your learning curve!")
            return
        
        # Group by date and calculate average score per day
        from collections import defaultdict
        from datetime import datetime
        
        daily_scores = defaultdict(list)
        for perf in performances:
            date_key = perf.created_at.date() if perf.created_at else datetime.now().date()
            daily_scores[date_key].append(perf.score)
        
        # Calculate daily averages
        dates = sorted(daily_scores.keys())
        avg_scores = [sum(daily_scores[date]) / len(daily_scores[date]) for date in dates]
        
        # Create DataFrame for chart
        import pandas as pd
        df = pd.DataFrame({
            'Date': dates,
            'Average Score': avg_scores,
        })
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Attempts", len(performances))
        with col2:
            overall_avg = sum(avg_scores) / len(avg_scores) if avg_scores else 0
            st.metric("Overall Average", f"{overall_avg:.1f}/10")
        with col3:
            recent_avg = avg_scores[-7:] if len(avg_scores) >= 7 else avg_scores
            recent_avg_score = sum(recent_avg) / len(recent_avg) if recent_avg else 0
            st.metric("Last 7 Days", f"{recent_avg_score:.1f}/10")
        
        # Display line chart
        if len(dates) > 1:
            st.line_chart(df.set_index('Date')['Average Score'])
        else:
            st.bar_chart(df.set_index('Date')['Average Score'])
        
        # Show category breakdown
        st.markdown("**📊 Performance by Category:**")
        category_avg = {}
        category_counts = {}
        
        for perf in performances:
            cat = perf.category or "uncategorized"
            if cat not in category_avg:
                category_avg[cat] = 0
                category_counts[cat] = 0
            category_avg[cat] += perf.score
            category_counts[cat] += 1
        
        for cat in sorted(category_avg.keys()):
            avg = category_avg[cat] / category_counts[cat]
            st.write(f"  • **{cat}**: {avg:.1f}/10 ({category_counts[cat]} attempts)")
        
    except Exception as e:
        st.error(f"Error loading learning curve: {str(e)}")
    finally:
        db.close()


def show_goal_tracker(candidate_id: str):
    """
    Display Goal Tracker showing current JLPT level and progress to J-Standard+ certification.
    """
    if not PHASE_TOOL_AVAILABLE:
        return
    
    try:
        phase_tool = GetCurrentPhase(candidate_id=candidate_id)
        phase_result = phase_tool.run()
        
        import json
        phase_info = json.loads(phase_result)
        
        current_phase = phase_info.get("current_phase", 1)
        metrics = phase_info.get("metrics", {})
        
        # Determine current JLPT level based on phase and performance
        n5_avg = metrics.get("n5_avg", 0)
        n5_count = metrics.get("n5_count", 0)
        caregiving_avg = metrics.get("caregiving_avg", 0)
        
        # Map phase to JLPT level
        if current_phase == 1:
            current_level = "N5"
            target_level = "N4"
        elif current_phase == 2:
            current_level = "N4"
            target_level = "N3"
        else:
            current_level = "N3"
            target_level = "J-Standard+"
        
        # Calculate progress to J-Standard+ (requires N3 mastery + caregiving proficiency)
        # J-Standard+ = N3 average >= 8.0 AND caregiving average >= 7.5
        j_standard_progress = 0
        if n5_avg >= 6.0 and n5_count >= 20:
            j_standard_progress += 33  # Phase 1 complete
        if caregiving_avg >= 7.5:
            j_standard_progress += 33  # Phase 2 complete
        if current_phase == 3:
            j_standard_progress = 100  # Phase 3 = J-Standard+
        
        st.markdown(
            f"""
            <div class="goal-tracker">
                <div class="goal-tracker-header">
                    <h3 class="goal-tracker-title">🎯 Goal Tracker: J-Standard+ Certification</h3>
                    <span class="current-level-badge">Current: {current_level}</span>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar-label">
                        <span>Progress to J-Standard+</span>
                        <span>{j_standard_progress}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-bar-fill" style="width: {j_standard_progress}%">
                            {j_standard_progress}%
                        </div>
                    </div>
                </div>
                <div class="certification-milestones">
                    <div class="milestone {'active' if n5_avg >= 6.0 and n5_count >= 20 else 'inactive'}">
                        <div class="milestone-icon">📚</div>
                        <div class="milestone-label">N5 Mastery<br>(20+ words, 6.0+ avg)</div>
                    </div>
                    <div class="milestone {'active' if caregiving_avg >= 7.5 else 'inactive'}">
                        <div class="milestone-icon">🏥</div>
                        <div class="milestone-label">Caregiving<br>(7.5+ avg)</div>
                    </div>
                    <div class="milestone {'active' if current_phase == 3 else 'inactive'}">
                        <div class="milestone-icon">⭐</div>
                        <div class="milestone-label">J-Standard+<br>Certified</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Show current metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("N5 Average", f"{n5_avg:.1f}/10", f"{n5_count} words")
        with col2:
            st.metric("Caregiving Average", f"{caregiving_avg:.1f}/10" if caregiving_avg > 0 else "N/A")
        with col3:
            st.metric("Current Phase", f"Phase {current_phase}")
            
    except Exception as e:
        st.warning(f"Could not load goal tracker: {str(e)}")


def show_support_hub():
    """Display Life-in-Japan Support Hub with interactive category cards."""
    st.header("🇯🇵 Life-in-Japan Support Hub")
    st.markdown("Get help with legal, financial, visa, housing, and emergency information.")
    
    db = get_db_session()
    try:
        from database.db_manager import LifeInJapanKB
        
        # Get all categories
        categories = db.query(LifeInJapanKB.category).distinct().all()
        category_list = [cat[0] for cat in categories if cat[0]]
        
        if not category_list:
            st.info("No support categories available. Run the seed script to populate the knowledge base.")
            return
        
        # Category icons and descriptions
        category_info = {
            "legal": {"icon": "⚖️", "title": "Legal Support", "description": "SSW rights, overtime laws, and legal advice"},
            "financial": {"icon": "💰", "title": "Financial Services", "description": "Banking, accounts, and financial guidance"},
            "visa": {"icon": "📋", "title": "Visa & Immigration", "description": "Visa transitions, renewals, and status changes"},
            "housing": {"icon": "🏠", "title": "Housing Information", "description": "Rent, deposits, and housing tips"},
            "emergency": {"icon": "🚨", "title": "Emergency Services", "description": "Medical emergencies, 119, and crisis protocols"}
        }
        
        # Display category cards in a grid
        st.markdown("### Select a Support Category")
        
        # Create 2 columns for card layout
        col1, col2 = st.columns(2)
        
        for i, category in enumerate(category_list):
            info = category_info.get(category, {"icon": "📄", "title": category.title(), "description": "Support information"})
            
            # Alternate between columns
            with col1 if i % 2 == 0 else col2:
                # Create clickable card
                if st.button(
                    f"{info['icon']} {info['title']}",
                    key=f"support_card_{category}",
                    width='stretch'
                ):
                    st.session_state[f"selected_category_{category}"] = True
                
                st.caption(info['description'])
                st.markdown("---")
        
        # Show content when category is selected
        selected_category = None
        for category in category_list:
            if st.session_state.get(f"selected_category_{category}", False):
                selected_category = category
                break
        
        if selected_category:
            st.markdown("---")
            st.subheader(f"{category_info.get(selected_category, {}).get('icon', '📄')} {category_info.get(selected_category, {}).get('title', selected_category.title())}")
            
            # Get entries for this category
            entries = db.query(LifeInJapanKB).filter(
                LifeInJapanKB.category == selected_category
            ).order_by(LifeInJapanKB.updated_at.desc()).all()
            
            if entries:
                for entry in entries:
                    with st.expander(f"**{entry.title}**"):
                        st.markdown(entry.content)
                        if entry.source:
                            st.caption(f"Source: {entry.source}")
            else:
                st.info(f"No information available for {selected_category} category.")
            
            # Allow querying
            st.markdown("---")
            st.subheader("🔍 Search Support Knowledge Base")
            query = st.text_input("Enter your question or keywords", key="support_query")
            
            if query:
                try:
                    from agency.support_agent.tools import GetLifeInJapanAdvice
                    tool = GetLifeInJapanAdvice(
                        query=query,
                        category=selected_category,
                        language="en"
                    )
                    result = tool.run()
                    st.markdown(result)
                except Exception as e:
                    st.error(f"Error querying knowledge base: {str(e)}")
        
    except Exception as e:
        st.error(f"Error loading support hub: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
    finally:
        db.close()


def show_compliance_view():
    """Display compliance view with document scanning and status indicators."""
    st.header("⚖️ Compliance & Document Verification")
    
    db = get_db_session()
    try:
        candidates = db.query(Candidate).all()
        candidate_ids = [c.candidate_id for c in candidates]
    finally:
        db.close()
    
    if not candidate_ids:
        st.warning("No candidates found.")
        return
    
    selected_candidate_id = st.selectbox("Select Candidate", candidate_ids)
    
    if not selected_candidate_id:
        return
    
    db = get_db_session()
    try:
        candidate = db.query(Candidate).filter(Candidate.candidate_id == selected_candidate_id).first()
        if not candidate:
            st.error(f"Candidate {selected_candidate_id} not found.")
            return
        
        # Get documents from document_vault
        documents = db.query(DocumentVault).filter(
            DocumentVault.candidate_id == selected_candidate_id
        ).all()
        
        # Check for required documents
        passport_doc = next((d for d in documents if d.doc_type == "passport"), None)
        jlpt_doc = next((d for d in documents if d.doc_type == "jlpt_certificate" or "jlpt" in d.doc_type.lower()), None)
        
        # Compliance status
        st.subheader(f"📋 Compliance Status: {candidate.full_name}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Required Documents:**")
            
            # Passport check
            if passport_doc:
                st.success("✅ **Passport:** Valid (Found in Document Vault)")
                if passport_doc.file_path:
                    st.caption(f"Path: {passport_doc.file_path}")
            else:
                st.error("❌ **Passport:** Missing or Not Uploaded")
            
            # JLPT Certificate check
            if jlpt_doc:
                st.success("✅ **JLPT Certificate:** Valid (Found in Document Vault)")
                if jlpt_doc.file_path:
                    st.caption(f"Path: {jlpt_doc.file_path}")
            else:
                st.warning("⚠️ **JLPT Certificate:** Not Found in Document Vault")
        
        with col2:
            st.write("**Compliance Check:**")
            
            # Run compliance check using LegalAgent
            if st.button("🔍 Run Compliance Check", type="primary"):
                try:
                    from mvp_v1.Legal.compliance_checker import ComplianceChecker
                    result = ComplianceChecker.auto_update_compliance(selected_candidate_id)
                    st.info(result)
                    
                    # Refresh candidate data
                    db.refresh(candidate)
                except Exception as e:
                    st.error(f"Error running compliance check: {str(e)}")
            
            # Show current status
            if candidate.travel_ready:
                st.success(f"✅ **Travel Ready:** Yes")
            else:
                st.warning(f"⚠️ **Travel Ready:** No")
            
            st.write(f"**Status:** {candidate.status}")
        
        # Document list
        st.subheader("📁 All Documents")
        if documents:
            doc_df = pd.DataFrame([
                {
                    "Type": doc.doc_type.title(),
                    "File Path": doc.file_path,
                    "Uploaded": doc.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if doc.uploaded_at else "N/A",
                }
                for doc in documents
            ])
            st.dataframe(doc_df, width='stretch', hide_index=True)
        else:
            st.info("No documents found in Document Vault for this candidate.")
        
    except Exception as e:
        st.error(f"Error loading compliance data: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
