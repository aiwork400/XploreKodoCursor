"""
Utility functions for the XploreKodo API layer.

Provides helper functions for audio transcription, translation, and other common operations.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import config


def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Sends audio bytes to OpenAI Whisper-1 for multilingual transcription.
    
    Supports automatic language detection for English, Japanese, and Nepali.
    The Whisper model automatically detects the language and transcribes accordingly.
    
    Args:
        audio_bytes: Audio data as bytes (WAV format from mic_recorder)
    
    Returns:
        Transcribed text string in the detected language
    
    Raises:
        Exception: If OpenAI API key is not configured or transcription fails
    """
    try:
        from openai import OpenAI
        
        # Get API key from config (loaded from .env file)
        api_key = config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found. Set it in .env file or config.py")
        
        # Initialize OpenAI client (automatically uses OPENAI_API_KEY from environment or config)
        client = OpenAI(api_key=api_key)
        
        # Create a file-like object from bytes
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "recording.wav"
        
        # Call Whisper API for transcription
        # Whisper-1 automatically detects language (English, Japanese, Nepali, etc.)
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
        
        return transcript.text
        
    except ImportError:
        raise ImportError(
            "OpenAI library not installed. Install it with: pip install openai"
        )
    except Exception as e:
        raise Exception(f"Error transcribing audio with Whisper: {str(e)}")

