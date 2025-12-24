"""
XploreKodo Configuration

Loads configuration from environment variables using python-dotenv.
All sensitive values should be stored in .env file (not tracked in git).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=False)

# Application Flags
PHASE_2_ENABLED = os.getenv("PHASE_2_ENABLED", "False").lower() == "true"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Corridors and Visa Modes
CORRIDORS = os.getenv("CORRIDORS", "Japan,Europe,GCC").split(",")
VISA_MODES = os.getenv("VISA_MODES", "Student,SSW_Caregiver,Skilled_Worker").split(",")

# Trilingual Support
TRILINGUAL_SUPPORT = os.getenv("TRILINGUAL_SUPPORT", "Nepali,Japanese,English").split(",")

# Supported Languages (ISO 639-1 codes)
SUPPORTED_LANGUAGES = ['en', 'ja', 'ne']  # English, Japanese, Nepali

# Language to TTS Voice Mapping
LANGUAGE_TTS_VOICES = {
    'en': 'en-US-Neural2-C',  # English (US)
    'ja': 'ja-JP-Neural2-C',  # Japanese
    'ne': 'ne-NP-Wavenet-A',  # Nepali
}

# Track-based TTS Voice Personality Mapping
# Maps track to voice personality settings (tone, pitch, speaking_rate)
TRACK_TTS_PERSONALITY = {
    'Care-giving': {
        'tone': 'gentle',
        'pitch': -2.0,  # Slightly lower pitch for gentle, caring tone
        'speaking_rate': 0.95,  # Slightly slower for clarity and warmth
        'ssml_gender': 'FEMALE',  # Often preferred for caregiving contexts
    },
    'Academic': {
        'tone': 'formal',
        'pitch': 0.0,  # Neutral pitch for formal tone
        'speaking_rate': 1.0,  # Standard rate
        'ssml_gender': 'NEUTRAL',  # Neutral for academic contexts
    },
    'Food/Tech': {
        'tone': 'professional',
        'pitch': 1.0,  # Slightly higher for energy and engagement
        'speaking_rate': 1.05,  # Slightly faster for tech contexts
        'ssml_gender': 'NEUTRAL',  # Neutral for professional contexts
    },
}

# Track options for Triple-Track Coaching
COACHING_TRACKS = ['Care-giving', 'Academic', 'Food/Tech']

# Language Display Names
LANGUAGE_NAMES = {
    'en': 'English',
    'ja': '日本語 (Japanese)',
    'ne': 'नेपाली (Nepali)',
}

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/xplorekodo",
)

# Payment Gateway API Keys
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY", "")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET", "")

# Email/SMS Notification Services
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# Translation API
TRANSLATION_API_KEY = os.getenv("TRANSLATION_API_KEY", "")
TRANSLATION_API_URL = os.getenv("TRANSLATION_API_URL", "")

# OpenAI API (for Phase 2: Voice-to-Voice, Whisper, TTS)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Google Cloud Translation API (for Multi-Language Socratic Questioning)
GOOGLE_CLOUD_TRANSLATE_PROJECT_ID = os.getenv("GOOGLE_CLOUD_TRANSLATE_PROJECT_ID", "")
GOOGLE_CLOUD_TRANSLATE_CREDENTIALS_PATH = os.getenv("GOOGLE_CLOUD_TRANSLATE_CREDENTIALS_PATH", "")

# Google Gemini API (for AI Grading in Language Coaching)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Google Cloud Application Credentials (for Speech-to-Text, TTS, etc.)
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")

# Grading Standard
# Options: 'JLPT_STANDARD' (standard JLPT grading) or 'XPLOREKODO_STRICT' (15% harder threshold)
GRADING_STANDARD = os.getenv("GRADING_STANDARD", "XPLOREKODO_STRICT")

# Grading Threshold Multiplier (for XPLOREKODO_STRICT: 1.15 = 15% harder)
GRADING_THRESHOLD_MULTIPLIER = 1.15 if GRADING_STANDARD == "XPLOREKODO_STRICT" else 1.0
