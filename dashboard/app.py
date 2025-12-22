"""
XploreKodo Global Command Center - Streamlit Dashboard

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

import base64
import pandas as pd
import streamlit as st
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

import config
from database.db_manager import Candidate, CurriculumProgress, Payment, DocumentVault, SessionLocal, StudentPerformance

# Try to import GetCurrentPhase for phase visualization
try:
    from agency.student_progress_agent.tools import GetCurrentPhase
    PHASE_TOOL_AVAILABLE = True
except ImportError:
    PHASE_TOOL_AVAILABLE = False
    GetCurrentPhase = None

# Page configuration
st.set_page_config(
    page_title="XploreKodo Global Command Center",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load Custom CSS
css_path = Path(__file__).parent.parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
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
def show_concierge_widget():
    """Display the XploreKodo Concierge Widget - floating sidebar assistant."""
    try:
        # Make widget more visible with a clear header
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🤖 XploreKodo Concierge")
        st.sidebar.markdown("*Your multilingual assistant*")
        
        # Initialize session state for concierge
        if "concierge_language" not in st.session_state:
            st.session_state.concierge_language = "en"
        if "concierge_avatar_visible" not in st.session_state:
            st.session_state.concierge_avatar_visible = True
        if "concierge_messages" not in st.session_state:
            st.session_state.concierge_messages = []
        if "pending_user_input" not in st.session_state:
            st.session_state.pending_user_input = None
        
        # Language Selector
        language_options = {
        'en': '🇺🇸 English',
        'ja': '🇯🇵 日本語',
            'ne': '🇳🇵 नेपाली'
        }
        
        selected_lang = st.sidebar.selectbox(
            "🌐 Language",
            options=list(language_options.keys()),
            format_func=lambda x: language_options[x],
            key="concierge_lang_select",
            index=list(language_options.keys()).index(st.session_state.concierge_language) if st.session_state.concierge_language in language_options else 0
        )
        st.session_state.concierge_language = selected_lang
        
        # Avatar Toggle
        st.session_state.concierge_avatar_visible = st.sidebar.checkbox(
            "👨‍🏫 Show Avatar",
            value=st.session_state.concierge_avatar_visible,
            key="concierge_avatar_toggle"
        )
        
        st.sidebar.markdown("---")
        
        # Show welcome message if no conversation yet
        if not st.session_state.concierge_messages:
            welcome_messages = {
                "en": "👋 **Welcome!** I'm your XploreKodo assistant. I can help with:\n\n• Platform features & navigation\n• Life-in-Japan advice\n• Language learning questions\n• General platform guidance\n\n**Try asking:** \"What can you help me with?\" or \"How does the virtual classroom work?\"",
                "ja": "👋 **ようこそ！** XploreKodoアシスタントです。お手伝いできること：\n\n• プラットフォーム機能とナビゲーション\n• 日本での生活に関するアドバイス\n• 言語学習の質問\n• 一般的なプラットフォームガイダンス\n\n**試してみてください：** 「何をお手伝いできますか？」または「バーチャルクラスルームはどのように機能しますか？」",
                "ne": "👋 **स्वागत छ!** म तपाईंको XploreKodo सहायक हुँ। म मद्दत गर्न सक्छु:\n\n• प्लेटफर्म सुविधाहरू र नेभिगेसन\n• जापानमा जीवन सल्लाह\n• भाषा सिकाइ प्रश्नहरू\n• सामान्य प्लेटफर्म मार्गदर्शन\n\n**प्रयास गर्नुहोस्:** \"तपाईं मलाई के मद्दत गर्न सक्नुहुन्छ?\" वा \"भर्चुअल कक्षा कसरी काम गर्छ?\""
            }
            st.sidebar.info(welcome_messages.get(st.session_state.concierge_language, welcome_messages["en"]))
        
        # Display conversation history
        if st.session_state.concierge_messages:
            st.sidebar.markdown("**💬 Conversation History:**")
            for msg in st.session_state.concierge_messages[-5:]:  # Show last 5 messages
                if msg["role"] == "user":
                    with st.sidebar.expander(f"**You:** {msg['content'][:60]}...", expanded=False):
                        st.markdown(msg['content'])
                else:
                    with st.sidebar.expander(f"**🤖 Concierge:** {msg['content'][:60]}...", expanded=True):
                        st.markdown(msg['content'])
        
        st.sidebar.markdown("---")
        
        # Hybrid Input: Chat + Mic Recorder
        input_method = st.sidebar.radio(
            "Input Method",
            ["💬 Text", "🎤 Voice"],
            key="concierge_input_method",
            horizontal=True
        )
        
        user_input = None
        
        if input_method == "💬 Text":
            # Text input - use text_input with a send button (chat_input doesn't work in sidebar)
            text_input = st.sidebar.text_input(
                "Ask the Concierge...",
                key="concierge_text_input",
                placeholder="Type your message here..."
            )
            send_button = st.sidebar.button("📤 Send", key="concierge_send_text")
            if send_button and text_input:
                user_input = text_input
        else:
            # Voice input using streamlit-mic-recorder
            st.sidebar.markdown("**🎤 Voice Recording:**")
            
            # Initialize recording state
            if "recorded_audio" not in st.session_state:
                st.session_state.recorded_audio = None
            
            try:
                from streamlit_mic_recorder import mic_recorder
                
                # Place mic_recorder in sidebar - this should render the button in the sidebar
                with st.sidebar.container():
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
                st.sidebar.warning("⚠️ streamlit-mic-recorder not installed")
                st.sidebar.code("pip install streamlit-mic-recorder")
                audio_data = None
            except Exception as e:
                st.sidebar.warning(f"⚠️ Mic recorder error: {str(e)}")
                audio_data = None
            
            # Use recorded audio
            final_audio = st.session_state.recorded_audio if st.session_state.recorded_audio else audio_data
            
            if final_audio:
                st.sidebar.markdown("---")
                st.sidebar.success("✅ Recording complete! Listen to your recording:")
                
                # Playback audio - make it prominent
                # Handle both dict format (from mic_recorder) and direct bytes
                audio_bytes_for_playback = final_audio.get("bytes") if isinstance(final_audio, dict) else final_audio
                if audio_bytes_for_playback:
                    # Ensure it's bytes, not base64 string
                    if isinstance(audio_bytes_for_playback, str):
                        audio_bytes_for_playback = base64.b64decode(audio_bytes_for_playback)
                    st.sidebar.audio(audio_bytes_for_playback, format="audio/wav", autoplay=False)
                    st.sidebar.caption("🔊 Click the play button above to hear your recording")
                else:
                    st.sidebar.warning("⚠️ Audio playback not available, but you can still send it for transcription.")
                
                # Show options
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    if st.button("🔄 Record Again", key="record_again_btn"):
                        st.session_state.recorded_audio = None
                        st.rerun()
                
                with col2:
                    send_voice_btn = st.button("📤 Send Voice", key="concierge_send_voice", type="primary")
                
                # Process voice input when Send is clicked
                if send_voice_btn:
                    with st.sidebar:
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
                            st.success(f"✅ Transcribed: \"{transcribed}\"")
                            # Store transcribed text for processing
                            st.session_state.pending_user_input = transcribed
                            # Clear recorded audio after processing
                            st.session_state.recorded_audio = None
                            st.rerun()  # Rerun to process the transcribed text
                        elif transcribed and transcribed.startswith("Error"):
                            st.error(transcribed)
                            st.info("💡 Tip: Make sure you're speaking clearly and your microphone is working. You can also type your message below.")
            else:
                st.sidebar.caption("💡 Click the microphone button above to start recording.")
            
            # Fallback text input if no audio recorded
            if not final_audio:
                st.sidebar.markdown("---")
                fallback_input = st.sidebar.text_input("Or type your message:", key="concierge_fallback_input")
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
            st.sidebar.info("🤖 Thinking...")
            try:
                response = get_concierge_response(user_input.strip(), st.session_state.concierge_language)
                
                # Add assistant message
                st.session_state.concierge_messages.append({
                    "role": "assistant",
                    "content": response
                })
                
                # Display response prominently (will be shown in conversation history after rerun)
                st.sidebar.success("✅ Response generated!")
                st.sidebar.markdown("---")
                st.sidebar.markdown("**🤖 Concierge Response:**")
                st.sidebar.markdown(response)
                st.sidebar.markdown("---")
                
                # Generate TTS audio if avatar is visible
                if st.session_state.concierge_avatar_visible:
                    st.sidebar.info("🔊 Generating audio...")
                    audio_output = generate_trilingual_tts(response, st.session_state.concierge_language)
                    if audio_output:
                        st.sidebar.audio(audio_output, format="audio/mp3")
                        st.sidebar.success("✅ Audio ready!")
                    else:
                        st.sidebar.warning("⚠️ Audio generation unavailable")
                
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.sidebar.error(error_msg)
                st.session_state.concierge_messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
                import traceback
                if config.DEBUG:
                    st.sidebar.code(traceback.format_exc())
            
            st.rerun()
    except Exception as e:
        # Show error in sidebar if widget fails - but keep widget visible
        st.sidebar.error(f"⚠️ Widget Error: {str(e)}")
        import traceback
        if config.DEBUG:
            with st.sidebar.expander("Show Error Details"):
                st.code(traceback.format_exc())
        # Show a fallback simple input
        st.sidebar.info("Please refresh the page. If the error persists, check the console.")


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
            from pathlib import Path
            
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
                "en": "Hello! 👋 I'm the XploreKodo Concierge. How can I help you today?",
                "ja": "こんにちは！👋 XploreKodoコンシェルジュです。今日はどのようにお手伝いできますか？",
                "ne": "नमस्ते! 👋 म XploreKodo Concierge हुँ। आज म तपाईंलाई कसरी मद्दत गर्न सक्छु?"
            }
            return greetings.get(language, greetings["en"])
        
        # Handle "how are you" and similar questions
        if any(phrase in user_lower for phrase in ["how are you", "how's it going", "how do you do", "what's up"]):
            responses = {
                "en": "I'm doing great, thank you! 😊 I'm here to help you with XploreKodo platform questions, life-in-Japan advice, and navigation. What would you like to know?",
                "ja": "元気です、ありがとうございます！😊 XploreKodoプラットフォームの質問、日本での生活に関するアドバイス、ナビゲーションをお手伝いします。何か知りたいことはありますか？",
                "ne": "म ठिक छु, धन्यवाद! 😊 म XploreKodo प्लेटफर्म प्रश्नहरू, जापानमा जीवन सल्लाह, र नेभिगेसनमा मद्दत गर्न यहाँ छु। तपाईं के जान्न चाहनुहुन्छ?",
            }
            return responses.get(language, responses["en"])
        
        # Platform feature questions
        if any(keyword in user_lower for keyword in ["support", "language", "nepalese", "nepali", "japanese", "multilingual", "what languages", "which languages"]):
            if "nepal" in user_lower or "nepali" in user_lower or "ne" in user_lower:
                return """✅ **Yes! XploreKodo supports Nepali (नेपाली).**

The platform is **trilingual** and supports:
- 🇺🇸 **English** (en)
- 🇯🇵 **Japanese** (日本語) (ja)
- 🇳🇵 **Nepali** (नेपाली) (ne)

You can switch languages using the language selector in the Concierge widget. All features including voice recording, text-to-speech, and AI responses work in all three languages."""
            
            if "japan" in user_lower or "japanese" in user_lower or "ja" in user_lower:
                return """✅ **Yes! XploreKodo supports Japanese (日本語).**

The platform is **trilingual** and supports:
- 🇺🇸 **English** (en)
- 🇯🇵 **Japanese** (日本語) (ja)
- 🇳🇵 **Nepali** (नेपाली) (ne)

You can switch languages using the language selector in the Concierge widget. All features including voice recording, text-to-speech, and AI responses work in all three languages."""
            
            return """✅ **XploreKodo is a Trilingual Platform!**

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
            return """🤖 **XploreKodo Concierge can help you with:**

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
- Say "take me to [page name]" to navigate
- Available pages: Candidate View, Virtual Classroom, Life-in-Japan Support, etc.

Try asking about specific topics like "visa renewal" or "banking in Japan" for detailed information!"""
        
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
                    prompt = f"""You are the XploreKodo Concierge, an AI assistant for the XploreKodo platform.

**Platform Overview:**
XploreKodo is a 360° AI-powered lifecycle platform for Nepali human capital preparing for work in Japan. It provides:
- Trilingual training (N5-N3 Japanese proficiency, Kaigo caregiving, AI/ML tech)
- Voice coaching with AI Sensei and 2D animated avatar
- Virtual classroom with live voice interaction
- Life-in-Japan support (visa, banking, housing, legal)
- Document vault and compliance tracking
- Multi-phase progression system

**User Question:** {user_input}

**Instructions:**
- Answer the question helpfully and accurately about XploreKodo platform features
- If the question is about life in Japan (visa, banking, housing, etc.), acknowledge that specific information wasn't found in the knowledge base
- Be conversational, friendly, and helpful
- If you don't know something, suggest where the user can find more information
- Keep responses concise (2-3 paragraphs max)

**Response (in {language}):**"""
                    
                    ai_response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    
                    response_text = ai_response.text.strip()
                    
                    # Add helpful context
                    return f"""{response_text}

---

💡 **Need more specific help?**
- Life-in-Japan questions: Try "visa renewal", "banking in Japan", "housing"
- Platform features: Ask about "virtual classroom", "voice coaching", "language learning"
- Navigation: Say "take me to [page name]" to navigate"""
                    
            except Exception as ai_error:
                # Fallback if AI fails
                return f"""{result}

💡 **I couldn't find specific information, but I can help with:**
- **Life-in-Japan:** Visa, banking, housing, healthcare, legal rights
- **Platform Features:** Language learning, virtual classroom, voice coaching, trilingual support
- **Navigation:** Say "take me to [page name]" to navigate

**Try asking:**
- "What is the virtual classroom?"
- "How does voice coaching work?"
- "Tell me about visa renewal"
- "What languages are supported?"

Or rephrase your question and I'll do my best to help! 😊"""
        
        return result
        
    except Exception as e:
        # Enhanced error handling with AI fallback
        try:
            from google import genai
            import config
            
            if config.GEMINI_API_KEY:
                client = genai.Client(api_key=config.GEMINI_API_KEY)
                
                prompt = f"""You are the XploreKodo Concierge. A user asked: "{user_input}"

An error occurred: {str(e)}

Provide a helpful, friendly response that:
1. Acknowledges the question
2. Provides general guidance about XploreKodo platform
3. Suggests alternative ways to get help
4. Keeps it concise and helpful

Response (in {language}):"""
                
                ai_response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
                
                return f"""{ai_response.text.strip()}

⚠️ *Note: There was a technical issue, but I've provided a helpful response above.*"""
        except:
            pass
        
        return f"""I apologize, but I encountered an error: {str(e)}

💡 **I can help you with:**
- Questions about XploreKodo platform features
- Life-in-Japan advice (visa, banking, housing, etc.)
- Navigation to different pages
- General platform guidance

**Try asking:**
- "What can you help me with?"
- "How does the virtual classroom work?"
- "Tell me about language learning"

Or rephrase your question and I'll do my best to help! 😊"""


def generate_trilingual_tts(text: str, language: str) -> bytes | None:
    """Generate TTS audio in the specified language."""
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
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=lang_code,
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
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
    st.markdown('<h1 class="main-header">🌏 XploreKodo Global Command Center</h1>', unsafe_allow_html=True)

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
    
    page_options = ["Candidate View", "Wisdom Hub", "Live Simulator", "Financial Ledger", "Compliance", "Life-in-Japan Support", "Virtual Classroom"]
    if admin_mode:
        page_options.append("Admin Dashboard")
    
    page = st.sidebar.radio(
        "Select View",
        page_options,
    )
    
    # Show Concierge Widget (after page selection to avoid conflicts)
    # Always show widget - it's a core feature
    try:
        show_concierge_widget()
    except Exception as e:
        # If widget fails completely, show a fallback message
        st.sidebar.markdown("---")
        st.sidebar.error(f"⚠️ Concierge Widget Error: {str(e)}")
        import traceback
        if config.DEBUG:
            with st.sidebar.expander("Debug Info"):
                st.code(traceback.format_exc())

    if page == "Candidate View":
        show_candidate_view()
    elif page == "Wisdom Hub":
        show_wisdom_hub()
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
    elif page == "Admin Dashboard":
        if admin_mode:
            show_admin_dashboard()
        else:
            st.error("🔒 Admin Mode must be enabled to access this page.")


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
                if st.button("🔄 Generate Briefing", key="generate_briefing_btn", width='stretch'):
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


def show_live_simulator():
    """Live simulator for testing Socratic Sensei."""
    st.header("🎓 Live Simulator - Socratic Sensei")

    st.info(
        "Test the Socratic Sensei by interacting with the LanguageCoachAgent through the FastAPI endpoints. "
        "This simulates candidate interactions with the Phase 2 immersive training features."
    )

    # API endpoint configuration
    api_base_url = st.text_input("API Base URL", "http://localhost:8000", help="Base URL for the FastAPI server")

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
                    st.markdown("**📊 AI Grading:**")
                    grade = grading.get("grade", 0)
                    grade_color = "🟢" if grade >= 8 else "🟡" if grade >= 6 else "🔴"
                    st.metric("Overall Grade", f"{grade_color} {grade}/10")
                    
                    st.markdown("**✅ Accuracy:**")
                    st.write(grading.get("accuracy_feedback", "N/A"))
                    
                    st.markdown("**📝 Grammar:**")
                    st.write(grading.get("grammar_feedback", "N/A"))
                    
                    st.markdown("**🎯 Pronunciation Hint:**")
                    st.info(grading.get("pronunciation_hint", "N/A"))
                
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
                                st.write(grading_result.get("grammar_feedback", "N/A"))
                                
                                st.markdown("**🎯 Pronunciation Hint:**")
                                st.info(grading_result.get("pronunciation_hint", "N/A"))
                                
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
            for log in critical_logs[:10]:  # Show top 10
                severity_color = "🔴" if log.severity == "Error" else "🟡"
                st.markdown(f"""
                {severity_color} **{log.severity}** - {log.event_type}
                - **Time:** {log.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
                - **User:** {log.user_id or 'System'}
                - **Message:** {log.message or 'No message'}
                """)
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
        
        st.markdown(f"**Current Phase: {phase_names.get(current_phase, f'Phase {current_phase}')}**")
        
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

