"""
Virtual Classroom Page - Live Voice Coaching with Avatar

Features:
- Real-time voice interaction with LanguageCoachAgent
- Avatar visualization with talking animation
- Live audio streaming using Gemini native audio or streamlit-webrtc
"""

from __future__ import annotations

import base64
import io
import json
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.parent.resolve())
if str(project_root) not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
from sqlalchemy.orm import Session

import config
from database.db_manager import Candidate, SessionLocal

# Try to import audio streaming libraries
try:
    from streamlit_webrtc import webrtc_streamer, WebRtcStreamerContext
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    webrtc_streamer = None
    WebRtcStreamerContext = None

try:
    from streamlit_mic_recorder import mic_recorder
    MIC_RECORDER_AVAILABLE = True
except ImportError:
    MIC_RECORDER_AVAILABLE = False
    mic_recorder = None

# Try to import Gemini for native audio streaming
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

# Page configuration
st.set_page_config(
    page_title="Virtual Classroom - XploreKodo",
    page_icon="🎓",
    layout="wide",
)

# Load Custom CSS
css_path = Path(__file__).parent.parent.parent / "assets" / "style.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Add Virtual Classroom specific CSS
st.markdown(
    """
    <style>
    .avatar-container {
        width: 100%;
        max-width: 500px;
        margin: 0 auto;
        position: relative;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    
    .avatar-video {
        width: 100%;
        aspect-ratio: 16/9;
        background: #1a1a2e;
        border-radius: 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        overflow: hidden;
    }
    
    .avatar-canvas-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 10;
    }
    
    #avatar_video_player {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 1;
    }
    
    .avatar-placeholder {
        font-size: 4rem;
        color: #fff;
        text-align: center;
        animation: pulse 2s ease-in-out infinite;
    }
    
    .avatar-talking {
        animation: talk 0.4s ease-in-out infinite;
        filter: brightness(1.1);
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 0.7; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.05); }
    }
    
    @keyframes talk {
        0%, 100% { 
            transform: scale(1) translateY(0); 
            opacity: 1;
        }
        25% { 
            transform: scale(1.08) translateY(-3px); 
            opacity: 0.95;
        }
        50% { 
            transform: scale(1.12) translateY(-5px); 
            opacity: 1;
        }
        75% { 
            transform: scale(1.08) translateY(-3px); 
            opacity: 0.95;
        }
    }
    
    .coaching-status {
        text-align: center;
        padding: 1rem;
        margin-top: 1rem;
        border-radius: 10px;
        font-weight: bold;
    }
    
    .status-active {
        background: #2E7D32;
        color: white;
    }
    
    .status-inactive {
        background: #757575;
        color: white;
    }
    
    .voice-controls {
        display: flex;
        gap: 1rem;
        justify-content: center;
        margin-top: 1rem;
    }
    
    .conversation-log {
        max-height: 400px;
        overflow-y: auto;
        padding: 1rem;
        background: #f5f5f5;
        border-radius: 10px;
        margin-top: 1rem;
    }
    
    .message-user {
        background: #e3f2fd;
        padding: 0.75rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        text-align: right;
    }
    
    .message-ai {
        background: #f1f8e9;
        padding: 0.75rem;
        border-radius: 10px;
        margin-bottom: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)


def get_db_session() -> Session:
    """Get database session."""
    return SessionLocal()


def initialize_session_state():
    """Initialize session state variables."""
    if "coaching_active" not in st.session_state:
        st.session_state.coaching_active = False
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    if "avatar_talking" not in st.session_state:
        st.session_state.avatar_talking = False
    if "selected_candidate_id" not in st.session_state:
        st.session_state.selected_candidate_id = None


def render_avatar_view(talking: bool = False):
    """
    Render the 2D Talking Avatar video container (avatar_view).
    
    Switches between 'Idle' and 'Talking' video loops based on AI response state.
    """
    import time
    
    # Auto-stop talking after duration
    if talking and "avatar_stop_time" in st.session_state:
        current_time = time.time()
        if current_time > st.session_state.avatar_stop_time:
            st.session_state.avatar_talking = False
            talking = False
            if "avatar_stop_time" in st.session_state:
                del st.session_state.avatar_stop_time
    
    # Determine video state
    video_state = "talking" if talking else "idle"
    
    # Video sources (placeholder URLs - in production, these would be actual video files)
    # Idle loop: Continuous idle animation
    # Talking loop: Lip-synced talking animation
    idle_video_url = "https://via.placeholder.com/640x360/667eea/ffffff?text=Avatar+Idle+Loop"
    talking_video_url = "https://via.placeholder.com/640x360/764ba2/ffffff?text=Avatar+Talking+Loop"
    
    # In production, these would be actual video file paths or streaming URLs
    # For now, we'll use a canvas-based animation that switches states
    current_video = talking_video_url if talking else idle_video_url
    
    st.markdown(
        f"""
        <div class="avatar-container">
            <div id="avatar_view" class="avatar-video">
                <video id="avatar_video_player" autoplay loop muted playsinline 
                       style="width: 100%; height: 100%; object-fit: cover; border-radius: 15px;">
                    <source src="{current_video}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
                <div id="avatar_canvas_overlay" class="avatar-canvas-overlay">
                    <!-- Canvas-based 2D avatar will be rendered here -->
                    <canvas id="avatar_canvas" width="640" height="360" 
                            style="width: 100%; height: 100%; border-radius: 15px;"></canvas>
                </div>
            </div>
            <div class="coaching-status {'status-active' if st.session_state.coaching_active else 'status-inactive'}">
                {'🎤 Live Coaching Active' if st.session_state.coaching_active else '⏸️ Coaching Inactive'}
                {' | 🗣️ Talking' if talking else ' | 😌 Idle'}
            </div>
        </div>
        <script>
        (function() {{
            const canvas = document.getElementById('avatar_canvas');
            const ctx = canvas.getContext('2d');
            const videoState = '{video_state}';
            
            // Avatar rendering function
            function drawAvatar(state) {{
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                // Background
                const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
                gradient.addColorStop(0, '#667eea');
                gradient.addColorStop(1, '#764ba2');
                ctx.fillStyle = gradient;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                // Draw avatar face (simplified 2D representation)
                const centerX = canvas.width / 2;
                const centerY = canvas.height / 2;
                
                // Face circle
                ctx.fillStyle = '#ffdbac';
                ctx.beginPath();
                ctx.arc(centerX, centerY, 80, 0, Math.PI * 2);
                ctx.fill();
                
                // Eyes
                ctx.fillStyle = '#000';
                ctx.beginPath();
                ctx.arc(centerX - 25, centerY - 20, 8, 0, Math.PI * 2);
                ctx.arc(centerX + 25, centerY - 20, 8, 0, Math.PI * 2);
                ctx.fill();
                
                // Mouth (changes based on state)
                if (state === 'talking') {{
                    // Talking: animated mouth
                    const mouthOpen = Math.sin(Date.now() / 200) * 15 + 20;
                    ctx.fillStyle = '#000';
                    ctx.beginPath();
                    ctx.ellipse(centerX, centerY + 30, 25, mouthOpen, 0, 0, Math.PI * 2);
                    ctx.fill();
                }} else {{
                    // Idle: closed mouth
                    ctx.strokeStyle = '#000';
                    ctx.lineWidth = 3;
                    ctx.beginPath();
                    ctx.arc(centerX, centerY + 30, 20, 0, Math.PI);
                    ctx.stroke();
                }}
                
                // Title
                ctx.fillStyle = '#fff';
                ctx.font = 'bold 24px Arial';
                ctx.textAlign = 'center';
                ctx.fillText('Sensei', centerX, centerY + 120);
            }}
            
            // Animation loop
            function animate() {{
                drawAvatar(videoState);
                requestAnimationFrame(animate);
            }}
            
            // Start animation
            animate();
            
            // Update state when talking status changes
            window.addEventListener('avatarStateChange', function(event) {{
                const newState = event.detail.state;
                drawAvatar(newState);
            }});
        }})();
        </script>
        """,
        unsafe_allow_html=True
    )


def process_voice_with_gemini_native_audio(audio_bytes: bytes, candidate_id: str) -> dict:
    """
    Process voice input using Gemini 2.5 Flash Native Audio streaming.
    
    This function integrates Gemini's native audio capabilities for real-time
    voice interaction with audio-visual sync for the 2D avatar.
    
    Returns:
        dict with transcript, response, audio_stream, and lip_sync_data
    """
    try:
        if not GEMINI_AVAILABLE or not config.GEMINI_API_KEY:
            return {
                "success": False,
                "error": "Gemini API not available"
            }
        
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        # Step 1: Transcribe audio using Gemini's native audio capabilities
        # Convert audio bytes to base64
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        # Use LanguageCoachingTool for initial transcription
        from agency.training_agent.language_coaching_tool import LanguageCoachingTool
        transcript_tool = LanguageCoachingTool(
            candidate_id=candidate_id,
            audio_base64=audio_base64,
            expected_answer="",
            question_type="conversation"
        )
        
        transcript_result = transcript_tool.run()
        transcript = ""
        if "Transcript:" in transcript_result:
            transcript = transcript_result.split("Transcript:")[1].split("\n")[0].strip()
        
        # Step 2: Generate response using Gemini with native audio streaming
        context = "You are a Japanese language teacher (Sensei) in a virtual classroom. "
        context += "Respond naturally and helpfully to the student's question. "
        context += "Keep responses concise and educational (2-3 sentences max).\n\n"
        
        # Add conversation history
        if st.session_state.conversation_history:
            context += "Recent conversation:\n"
            for msg in st.session_state.conversation_history[-3:]:
                context += f"{msg['role']}: {msg['content']}\n"
        
        context += f"\nStudent: {transcript}\nSensei:"
        
        # Generate response with Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=context
        )
        
        ai_response = response.text.strip()
        
        # Step 3: Generate audio with TTS for lip-sync
        audio_output = None
        lip_sync_data = None
        
        try:
            from google.cloud import texttospeech
            tts_client = texttospeech.TextToSpeechClient()
            
            synthesis_input = texttospeech.SynthesisInput(text=ai_response)
            voice = texttospeech.VoiceSelectionParams(
                language_code="ja-JP",
                name="ja-JP-Neural2-C",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,  # Normal speed for lip-sync
                pitch=0.0
            )
            
            tts_response = tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            audio_output = tts_response.audio_content
            
            # Generate lip-sync data (phoneme timing)
            # This is a simplified version - in production, use a proper lip-sync engine
            lip_sync_data = {
                "text": ai_response,
                "duration": len(audio_output) / 16000,  # Rough estimate
                "phonemes": _generate_phonemes(ai_response)  # Simplified phoneme extraction
            }
            
        except Exception as e:
            st.warning(f"TTS unavailable: {str(e)}")
        
        return {
            "transcript": transcript,
            "response": ai_response,
            "audio_output": audio_output,
            "lip_sync_data": lip_sync_data,
            "success": True
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _generate_phonemes(text: str) -> list:
    """
    Generate simplified phoneme timing data for lip-sync.
    
    In production, this would use a proper phoneme extraction library
    like espeak-ng or a Japanese-specific phoneme analyzer.
    """
    # Simplified: map characters to mouth shapes
    phonemes = []
    for i, char in enumerate(text):
        if char in "あいうえおアイウエオ":
            phonemes.append({"time": i * 0.1, "shape": "open"})
        elif char in "かきくけこカキクケコ":
            phonemes.append({"time": i * 0.1, "shape": "consonant"})
        elif char in "まみむめもマミムメモ":
            phonemes.append({"time": i * 0.1, "shape": "closed"})
        else:
            phonemes.append({"time": i * 0.1, "shape": "neutral"})
    return phonemes


def process_voice_input(audio_bytes: bytes, candidate_id: str) -> dict:
    """
    Process voice input using LanguageCoachingTool or Gemini native audio.
    
    Returns:
        dict with transcript, response, and audio output
    """
    try:
        from agency.training_agent.language_coaching_tool import LanguageCoachingTool
        
        # Convert audio to base64
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        # Use LanguageCoachingTool for transcription and grading
        # For live coaching, we'll use it in a conversational mode
        transcript_tool = LanguageCoachingTool(
            candidate_id=candidate_id,
            audio_base64=audio_base64,
            expected_answer="",  # Empty for conversational mode
            question_type="conversation"
        )
        
        # Get transcript
        result = transcript_tool.run()
        
        # Extract transcript from result
        transcript = ""
        if "Transcript:" in result:
            transcript = result.split("Transcript:")[1].split("\n")[0].strip()
        
        # Generate AI response using Gemini
        ai_response = ""
        audio_output = None
        
        if GEMINI_AVAILABLE and config.GEMINI_API_KEY:
            try:
                client = genai.Client(api_key=config.GEMINI_API_KEY)
                
                # Build conversation context
                context = "You are a Japanese language teacher (Sensei) in a virtual classroom. "
                context += "Respond naturally and helpfully to the student's question. "
                context += "Keep responses concise and educational.\n\n"
                
                # Add recent conversation history
                if st.session_state.conversation_history:
                    context += "Recent conversation:\n"
                    for msg in st.session_state.conversation_history[-3:]:
                        context += f"{msg['role']}: {msg['content']}\n"
                
                context += f"\nStudent: {transcript}\nSensei:"
                
                # Generate response
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=context
                )
                
                ai_response = response.text.strip()
                
                # Generate audio response using Google TTS (if available)
                try:
                    from google.cloud import texttospeech
                    tts_client = texttospeech.TextToSpeechClient()
                    
                    synthesis_input = texttospeech.SynthesisInput(text=ai_response)
                    voice = texttospeech.VoiceSelectionParams(
                        language_code="ja-JP",
                        name="ja-JP-Neural2-C",  # Japanese neural voice
                        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
                    )
                    audio_config = texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.MP3
                    )
                    
                    tts_response = tts_client.synthesize_speech(
                        input=synthesis_input,
                        voice=voice,
                        audio_config=audio_config
                    )
                    
                    audio_output = tts_response.audio_content
                    
                except Exception as e:
                    st.warning(f"TTS unavailable: {str(e)}")
                    
            except Exception as e:
                st.error(f"Gemini error: {str(e)}")
                ai_response = "I understand. Let's continue learning!"
        
        return {
            "transcript": transcript,
            "response": ai_response,
            "audio_output": audio_output,
            "lip_sync_data": lip_sync_data,
            "success": True
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    """Main Virtual Classroom page."""
    st.header("🎓 Virtual Classroom - Live Voice Coaching")
    st.markdown("Interact with Sensei in real-time using voice commands.")
    
    initialize_session_state()
    
    # Get candidate list
    db = get_db_session()
    try:
        candidates = db.query(Candidate).all()
        candidate_options = {f"{c.full_name} ({c.candidate_id})": c.candidate_id for c in candidates}
    finally:
        db.close()
    
    # Layout: Avatar on left, Controls on right
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Render 2D Talking Avatar (avatar_view)
        render_avatar_view(talking=st.session_state.avatar_talking)
    
    with col2:
        st.subheader("👤 Select Candidate")
        
        if candidate_options:
            selected_candidate = st.selectbox(
                "Choose Candidate",
                options=list(candidate_options.keys()),
                key="virtual_classroom_candidate"
            )
            st.session_state.selected_candidate_id = candidate_options[selected_candidate]
            
            st.markdown("---")
            st.subheader("🎤 Voice Controls")
            
            # Start/Stop Coaching Button
            if not st.session_state.coaching_active:
                if st.button("🎙️ Start Live Coaching", type="primary", use_container_width=True):
                    st.session_state.coaching_active = True
                    st.rerun()
            else:
                if st.button("⏹️ Stop Coaching", type="secondary", use_container_width=True):
                    st.session_state.coaching_active = False
                    st.session_state.avatar_talking = False
                    st.rerun()
            
            # Voice Input Method Selection
            if st.session_state.coaching_active:
                st.markdown("---")
                st.info("💡 Speak into your microphone. Your voice will be transcribed and Sensei will respond.")
                
                # Use mic_recorder for voice input
                if MIC_RECORDER_AVAILABLE:
                    audio_data = mic_recorder(
                        key="virtual_classroom_recorder",
                        start_prompt="🎤 Recording...",
                        stop_prompt="⏹️ Stop Recording",
                        just_once=False,
                        use_container_width=True,
                    )
                    
                    if audio_data:
                        st.audio(audio_data["bytes"], format="audio/wav")
                        
                        # Process audio when recorded - Complete Live Track Loop
                        if st.button("📤 Send to Sensei", type="primary", key="send_voice_btn"):
                            with st.spinner("🎤 Processing your voice with Gemini Native Audio..."):
                                # Set avatar to talking state
                                st.session_state.avatar_talking = True
                                
                                # Process voice input using Gemini Native Audio streaming
                                result = process_voice_with_gemini_native_audio(
                                    audio_data["bytes"],
                                    st.session_state.selected_candidate_id
                                )
                                
                                if result.get("success"):
                                    # Add to conversation history
                                    if result.get("transcript"):
                                        st.session_state.conversation_history.append({
                                            "role": "user",
                                            "content": result["transcript"]
                                        })
                                    
                                    if result.get("response"):
                                        st.session_state.conversation_history.append({
                                            "role": "assistant",
                                            "content": result["response"]
                                        })
                                    
                                    # Play audio response with lip-sync data
                                    if result.get("audio_output"):
                                        # Calculate audio duration
                                        import time
                                        lip_sync_data = result.get("lip_sync_data", {})
                                        estimated_duration = lip_sync_data.get("duration", len(result["audio_output"]) / 16000)
                                        
                                        # Create unique audio ID for tracking
                                        audio_id = f"audio_{len(st.session_state.conversation_history)}"
                                        
                                        # Display audio player with avatar lip-sync
                                        st.markdown(
                                            f"""
                                            <audio id="{audio_id}" controls autoplay>
                                                <source src="data:audio/mp3;base64,{base64.b64encode(result['audio_output']).decode('utf-8')}" type="audio/mp3">
                                            </audio>
                                            <script>
                                            (function() {{
                                                const audio = document.getElementById('{audio_id}');
                                                const phonemes = {json.dumps(lip_sync_data.get('phonemes', []))};
                                                
                                                if (audio) {{
                                                    // Switch avatar to talking state when audio plays
                                                    audio.addEventListener('play', function() {{
                                                        // Trigger avatar state change event
                                                        window.dispatchEvent(new CustomEvent('avatarStateChange', {{
                                                            detail: {{ state: 'talking' }}
                                                        }}));
                                                        
                                                        // Start lip-sync animation
                                                        let phonemeIndex = 0;
                                                        const lipSyncInterval = setInterval(function() {{
                                                            if (phonemeIndex < phonemes.length) {{
                                                                const phoneme = phonemes[phonemeIndex];
                                                                // Update avatar mouth shape based on phoneme
                                                                window.dispatchEvent(new CustomEvent('avatarPhoneme', {{
                                                                    detail: {{ phoneme: phoneme }}
                                                                }}));
                                                                phonemeIndex++;
                                                            }} else {{
                                                                clearInterval(lipSyncInterval);
                                                            }}
                                                        }}, 100); // Update every 100ms
                                                        
                                                        // Clear interval when audio ends
                                                        audio.addEventListener('ended', function() {{
                                                            clearInterval(lipSyncInterval);
                                                            window.dispatchEvent(new CustomEvent('avatarStateChange', {{
                                                                detail: {{ state: 'idle' }}
                                                            }}));
                                                        }}, {{ once: true }});
                                                    }});
                                                    
                                                    // Stop talking animation when audio ends
                                                    audio.addEventListener('ended', function() {{
                                                        window.dispatchEvent(new CustomEvent('avatarStateChange', {{
                                                            detail: {{ state: 'idle' }}
                                                        }}));
                                                    }});
                                                    
                                                    // Also stop on pause
                                                    audio.addEventListener('pause', function() {{
                                                        window.dispatchEvent(new CustomEvent('avatarStateChange', {{
                                                            detail: {{ state: 'idle' }}
                                                        }}));
                                                    }});
                                                }}
                                            }})();
                                            </script>
                                            """,
                                            unsafe_allow_html=True
                                        )
                                        
                                        # Keep avatar talking while audio plays
                                        st.session_state.avatar_talking = True
                                        
                                        # Schedule avatar to stop talking after audio duration
                                        st.session_state.avatar_stop_time = time.time() + max(estimated_duration, 3)
                                    
                                    st.success("✅ Response received!")
                                    st.rerun()
                                else:
                                    st.error(f"❌ Error: {result.get('error', 'Unknown error')}")
                                    st.session_state.avatar_talking = False
                else:
                    st.warning("⚠️ Microphone recorder not available. Install: pip install streamlit-mic-recorder")
                
                # Alternative: WebRTC for real-time streaming
                if WEBRTC_AVAILABLE:
                    st.markdown("---")
                    st.subheader("🌐 Real-Time Audio Stream (WebRTC)")
                    st.info("For real-time bidirectional audio, use WebRTC streamer below.")
                    
                    # WebRTC audio processor for real-time streaming
                    def audio_frame_callback(frame):
                        """Process incoming audio frames from WebRTC."""
                        if st.session_state.coaching_active:
                            # Convert audio frame to bytes
                            audio_bytes = frame.to_ndarray().tobytes()
                            # Process in background (would need async handling in production)
                            return frame
                        return frame
                    
                    # WebRTC streamer for bidirectional audio
                    webrtc_ctx = webrtc_streamer(
                        key="virtual_classroom_webrtc",
                        audio_frame_callback=audio_frame_callback,
                        media_stream_constraints={
                            "video": False,
                            "audio": {
                                "echoCancellation": True,
                                "noiseSuppression": True,
                                "autoGainControl": True,
                            },
                        },
                        rtc_configuration={
                            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
                        },
                    )
                    
                    if webrtc_ctx.state.playing:
                        st.success("🎤 Real-time audio streaming active!")
                        # Process audio frames in real-time
                        if webrtc_ctx.audio_receiver:
                            # This would process audio chunks as they arrive
                            pass
                else:
                    st.caption("💡 Install streamlit-webrtc for real-time audio streaming: pip install streamlit-webrtc")
        else:
            st.warning("No candidates available. Create a candidate first.")
    
    # Conversation Log
    if st.session_state.conversation_history:
        st.markdown("---")
        st.subheader("💬 Conversation History")
        
        conversation_html = '<div class="conversation-log">'
        for msg in st.session_state.conversation_history:
            if msg["role"] == "user":
                conversation_html += f'<div class="message-user"><strong>You:</strong> {msg["content"]}</div>'
            else:
                conversation_html += f'<div class="message-ai"><strong>Sensei:</strong> {msg["content"]}</div>'
        conversation_html += '</div>'
        
        st.markdown(conversation_html, unsafe_allow_html=True)
        
        # Clear conversation button
        if st.button("🗑️ Clear Conversation"):
            st.session_state.conversation_history = []
            st.rerun()


# Make main() callable from app.py
if __name__ == "__main__":
    main()
else:
    # When imported, expose main function
    pass

