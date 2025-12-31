# Following DEVELOPMENT_GUIDELINES.md - Sandbox Protocol
import streamlit as st
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    st.title("🎤 Audio-to-Sensei Sandbox")
    st.write("Testing Trilingual STT (EN, JP, NE) for the All-in-One Shop.")

    # 1. Setup Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("Missing GEMINI_API_KEY in .env")
        return
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    # 2. Audio Capture UI
    st.info("Click the button below and speak in English, Japanese, or Nepali.")
    
    # mic_recorder returns a dictionary with 'bytes' when recording stops
    audio = mic_recorder(
        start_prompt="🎤 Start Recording",
        stop_prompt="🛑 Stop & Transcribe",
        key='sensei_mic'
    )

    if audio:
        st.audio(audio['bytes']) # Playback for verification
        
        with st.spinner("Sensei is listening and transcribing..."):
            try:
                # 3. Process with Gemini
                # We send the raw bytes as a part of the content list
                audio_data = {
                    "mime_type": "audio/wav",
                    "data": audio['bytes']
                }
                
                prompt = "Please transcribe this audio accurately. If it is in Japanese, provide the Kanji/Kana. If English or Nepali, transcribe accordingly. Output ONLY the transcript."
                
                response = model.generate_content([prompt, audio_data])
                
                # 4. Display Result
                st.success("### Transcript Result:")
                st.write(response.text)
                
                # Logic Test: Word Count (for our 3,000 word rule)
                word_count = len(response.text.split())
                st.info(f"Word Count: {word_count}")

            except Exception as e:
                st.error(f"STT Error: {str(e)}")

if __name__ == "__main__":
    main()
