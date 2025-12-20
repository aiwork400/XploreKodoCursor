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

import pandas as pd
import streamlit as st
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

import config
from database.db_manager import Candidate, CurriculumProgress, Payment, DocumentVault, SessionLocal

# Page configuration
st.set_page_config(
    page_title="XploreKodo Global Command Center",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
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


# Main App
def main():
    """Main Streamlit app."""
    st.markdown('<h1 class="main-header">🌏 XploreKodo Global Command Center</h1>', unsafe_allow_html=True)

    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select View",
        ["Candidate View", "Wisdom Hub", "Live Simulator", "Financial Ledger", "Compliance"],
    )

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


def show_candidate_view():
    """Display candidate view with searchable list."""
    st.header("👥 Candidate View")

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
                use_container_width=True,
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
        st.dataframe(provider_df, use_container_width=True, hide_index=True)

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
        st.dataframe(recent_df, use_container_width=True, hide_index=True)


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
                use_container_width=False,
            )
            
            if audio_data:
                # Process audio when recorded
                if st.button(f"📤 Submit & Grade Answer", key=f"submit_{question_id}"):
                    import base64
                    import requests
                    
                    # Convert audio_data to base64
                    audio_bytes = audio_data["bytes"]
                    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                    
                    # Get API base URL (use default or from session state)
                    api_base_url = st.session_state.get("api_base_url", "http://localhost:8000")
                    
                    # Get expected answer from question data if available
                    expected_answer = None
                    if entry.get("question"):
                        expected_answer = entry["question"].get("english", "")
                    
                    # Call language coaching API
                    payload = {
                        "candidate_id": candidate_id,
                        "audio_base64": audio_base64,
                        "language_code": language_code,
                        "question_id": question_id,
                        "expected_answer": expected_answer,
                    }
                    
                    with st.spinner("🎤 Transcribing and grading your answer..."):
                        try:
                            response = requests.post(
                                f"{api_base_url}/language-coaching",
                                json=payload,
                                timeout=60
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                if result.get("success"):
                                    st.success("✅ Answer graded successfully! Refresh to see results.")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {result.get('message', 'Unknown error')}")
                            else:
                                st.error(f"Error: {response.status_code} - {response.text}")
                        except Exception as e:
                            st.error(f"Connection error: {str(e)}")
        except ImportError:
            st.warning("⚠️ streamlit-mic-recorder not installed. Please install it to record answers.")
            st.code("pip install streamlit-mic-recorder")
        
        st.markdown("---")


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
            st.dataframe(doc_df, use_container_width=True, hide_index=True)
        else:
            st.info("No documents found in Document Vault for this candidate.")
        
    except Exception as e:
        st.error(f"Error loading compliance data: {str(e)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

