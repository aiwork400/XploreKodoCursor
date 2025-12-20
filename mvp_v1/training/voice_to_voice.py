"""
Phase 2: Voice-to-Voice Translation Logic (OpenAI Reality)

This module contains voice-to-voice translation capabilities that are
only activated when PHASE_2_ENABLED = True.

Uses OpenAI Whisper for transcription, GPT-4o for translation, and OpenAI TTS for synthesis.
"""

from __future__ import annotations

import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import config

# Phase 2 guard: This entire module is dormant unless flag is enabled
if not config.PHASE_2_ENABLED:
    # Placeholder class that raises error if accidentally instantiated
    class VoiceToVoiceTranslator:
        """
        Phase 2 Voice-to-Voice Translator (DORMANT).

        This feature is only available when PHASE_2_ENABLED = True.
        """

        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "VoiceToVoiceTranslator is a Phase 2 feature. "
                "Set PHASE_2_ENABLED = True in config.py to activate."
            )

else:
    # Phase 2 implementation with OpenAI Reality
    from agency_swarm.tools import BaseTool
    from openai import OpenAI
    from pydantic import Field

    # Initialize OpenAI client
    openai_client = OpenAI(api_key=config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None

    class VoiceToVoiceTranslator(BaseTool):
        """
        Voice-to-Voice real-time translation tool (Phase 2 - OpenAI Reality).

        Uses:
        - OpenAI Whisper for Nepali audio transcription
        - GPT-4o for translation to Polite Japanese (Desu/Masu form)
        - OpenAI TTS (Voice: 'Alloy' or 'Shimmer') for Japanese audio synthesis
        """

        audio_input_path: Optional[str] = Field(
            default=None, description="Path to input audio file (Nepali input). Alternative to audio_base64."
        )
        audio_base64: Optional[str] = Field(
            default=None, description="Base64-encoded audio string (Nepali input). Alternative to audio_input_path."
        )
        source_language: Literal["Nepali", "Japanese", "English"] = Field(
            default="Nepali", description="Source language (typically Nepali)"
        )
        target_language: Literal["Nepali", "Japanese", "English"] = Field(
            default="Japanese", description="Target language (typically Japanese Sensei)"
        )
        tts_voice: Literal["alloy", "shimmer"] = Field(
            default="alloy", description="OpenAI TTS voice: 'alloy' or 'shimmer'"
        )

        def run(self) -> str:
            """
            Perform voice-to-voice translation: Nepali -> Japanese Sensei.

            Process:
            1. Transcribe Nepali audio using OpenAI Whisper
            2. Translate to Polite Japanese (Desu/Masu form) using GPT-4o
            3. Synthesize Japanese audio using OpenAI TTS
            4. Save audio to media/responses/ and return file path
            """
            if not openai_client:
                return "Error: OpenAI API key not configured. Set OPENAI_API_KEY in .env file."

            try:
                # Step 1: Handle audio input (file path or base64)
                audio_file = None
                if self.audio_base64:
                    # Decode base64 audio
                    audio_data = base64.b64decode(self.audio_base64)
                    # Save to temporary file (cross-platform)
                    import tempfile
                    temp_dir = Path(tempfile.gettempdir())
                    temp_audio_path = temp_dir / f"temp_audio_{datetime.now().timestamp()}.wav"
                    temp_audio_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(temp_audio_path, "wb") as f:
                        f.write(audio_data)
                    audio_file = open(temp_audio_path, "rb")
                elif self.audio_input_path:
                    audio_file = open(self.audio_input_path, "rb")
                else:
                    return "Error: Either audio_input_path or audio_base64 must be provided."

                # Step 2: Transcribe Nepali audio using Whisper
                transcription_response = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ne" if self.source_language == "Nepali" else None,  # Nepali language code
                )
                nepali_text = transcription_response.text
                audio_file.close()

                # Clean up temporary file if created
                if self.audio_base64 and temp_audio_path.exists():
                    temp_audio_path.unlink()

                # Step 3: Translate to Polite Japanese (Desu/Masu form) using GPT-4o
                translation_prompt = f"""Translate the following Nepali text to Polite Japanese (Desu/Masu form).
The response should be appropriate for a Japanese Sensei (teacher) speaking to a student.
Use respectful, formal Japanese language.

Nepali text: {nepali_text}

Provide only the Japanese translation in Polite form (Desu/Masu), no explanations."""

                translation_response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a professional translator specializing in Nepali to Japanese translation. Always use Polite Japanese (Desu/Masu form) suitable for a teacher-student context.",
                        },
                        {"role": "user", "content": translation_prompt},
                    ],
                    temperature=0.3,
                )
                japanese_text = translation_response.choices[0].message.content.strip()

                # Step 4: Synthesize Japanese audio using OpenAI TTS
                tts_response = openai_client.audio.speech.create(
                    model="tts-1",
                    voice=self.tts_voice,
                    input=japanese_text,
                )

                # Step 5: Save audio to media/responses/
                media_dir = Path(__file__).parent.parent.parent / "media" / "responses"
                media_dir.mkdir(parents=True, exist_ok=True)

                audio_filename = f"japanese_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                audio_output_path = media_dir / audio_filename

                with open(audio_output_path, "wb") as f:
                    for chunk in tts_response.iter_bytes():
                        f.write(chunk)

                return f"""
Voice-to-Voice Translation (Phase 2 - OpenAI Reality):
✓ Transcribed Nepali audio: "{nepali_text}"
✓ Translated to Polite Japanese: "{japanese_text}"
✓ Generated Japanese Sensei audio (Voice: {self.tts_voice})

**Output:**
- Audio Output Path: {audio_output_path}
- Transcribed Text: {nepali_text}
- Translated Text: {japanese_text}
"""
            except Exception as e:
                return f"Error in voice-to-voice translation: {str(e)}"

