"""
Seed Curriculum Script - Populate knowledge_base with JLPT N5 words and caregiving terms.

Uses:
- New google-genai SDK for Nepali translations
- JLPT Vocab API for N5 words
- Manual caregiving terms list
- PostgreSQL knowledge_base table
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        pass

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import requests
from sqlalchemy.orm import Session

import config
from database.db_manager import KnowledgeBase, SessionLocal

# Try to import google-genai
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("ERROR: google-genai not installed. Run: pip install google-genai")
    sys.exit(1)


# Caregiving terms (Japanese/English pairs)
CAREGIVING_TERMS = [
    ("病院", "Hospital"),
    ("服薬", "Medication"),
    ("バイタル", "Vital Signs"),
    ("血圧", "Blood Pressure"),
    ("体温", "Body Temperature"),
    ("脈拍", "Pulse"),
    ("看護師", "Nurse"),
    ("医師", "Doctor"),
    ("患者", "Patient"),
    ("診察", "Medical Examination"),
    ("処方箋", "Prescription"),
    ("薬", "Medicine"),
    ("症状", "Symptoms"),
    ("痛み", "Pain"),
    ("介護", "Caregiving"),
    ("介護士", "Caregiver"),
    ("高齢者", "Elderly Person"),
    ("食事", "Meal"),
    ("入浴", "Bathing"),
    ("リハビリ", "Rehabilitation"),
]


def fetch_jlpt_n5_words() -> list[dict]:
    """
    Fetch 100 JLPT N5 words from the API.
    
    Returns:
        List of word dictionaries with 'word', 'reading', 'meaning', etc.
    """
    print("📚 Fetching 100 JLPT N5 words from API...")
    
    try:
        url = "https://jlpt-vocab-api.vercel.app/api/words?level=5"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        words = response.json()
        
        # Ensure we have exactly 100 words (or as many as available)
        if isinstance(words, list):
            words = words[:100]
        elif isinstance(words, dict) and "words" in words:
            words = words["words"][:100]
        else:
            print(f"⚠️  Unexpected API response format: {type(words)}")
            words = []
        
        print(f"✅ Fetched {len(words)} JLPT N5 words")
        return words
        
    except Exception as e:
        print(f"❌ Error fetching JLPT N5 words: {e}")
        return []


def translate_to_nepali_with_gemini(japanese_text: str, english_text: str = "") -> str:
    """
    Translate Japanese text to Nepali using Gemini 1.5 Flash.
    
    Args:
        japanese_text: Japanese word/text
        english_text: English translation (optional, for context)
    
    Returns:
        Nepali translation
    """
    if not GEMINI_AVAILABLE:
        return f"[Nepali: {japanese_text}]"
    
    try:
        # Get API key from config
        api_key = config.GEMINI_API_KEY or ""
        
        if not api_key:
            print("⚠️  GEMINI_API_KEY not found in .env file")
            return f"[Nepali: {japanese_text}]"
        
        # Initialize client
        client = genai.Client(api_key=api_key)
        
        # Build translation prompt
        context = f"English: {english_text}" if english_text else ""
        prompt = f"""Translate the following Japanese word to Nepali.

Japanese: {japanese_text}
{context}

Provide ONLY the Nepali translation, nothing else. Do not include explanations or additional text."""
        
        # Generate translation
        # Note: Using gemini-2.5-flash (gemini-1.5-flash was deprecated)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        nepali_text = response.text.strip()
        
        # Clean up if there are quotes or extra text
        nepali_text = nepali_text.strip('"').strip("'").strip()
        
        return nepali_text
        
    except Exception as e:
        print(f"⚠️  Translation error for '{japanese_text}': {e}")
        return f"[Nepali: {japanese_text}]"


def format_vocabulary_content(word_data: dict, nepali_translation: str = "") -> str:
    """
    Format vocabulary data into content string for knowledge_base.
    
    Args:
        word_data: Dictionary with word information
        nepali_translation: Nepali translation
    
    Returns:
        Formatted content string
    """
    word = word_data.get("word", word_data.get("reading", ""))
    reading = word_data.get("reading", "")
    meaning = word_data.get("meaning", word_data.get("english", ""))
    
    content_parts = []
    
    if word:
        content_parts.append(f"Word: {word}")
    if reading and reading != word:
        content_parts.append(f"Reading: {reading}")
    if meaning:
        content_parts.append(f"English: {meaning}")
    if nepali_translation:
        content_parts.append(f"Nepali: {nepali_translation}")
    
    return "\n".join(content_parts)


def store_in_knowledge_base(
    entries: list[dict],
    source_file: str,
    category: str,
    db: Session
) -> int:
    """
    Store entries in knowledge_base table.
    
    Args:
        entries: List of entry dictionaries with 'concept_title', 'concept_content', 'language'
        source_file: Source file identifier
        category: Category for the entries
        db: Database session
    
    Returns:
        Number of new entries stored
    """
    stored_count = 0
    
    for entry in entries:
        concept_title = entry.get("concept_title", "")
        concept_content = entry.get("concept_content", "")
        language = entry.get("language", "ja")
        
        if not concept_title or not concept_content:
            continue
        
        # Check if already exists
        existing = db.query(KnowledgeBase).filter(
            KnowledgeBase.source_file == source_file,
            KnowledgeBase.concept_title == concept_title,
            KnowledgeBase.category == category
        ).first()
        
        if existing:
            # Update existing entry
            existing.concept_content = concept_content
            continue
        
        # Create new entry
        kb_entry = KnowledgeBase(
            source_file=source_file,
            concept_title=concept_title,
            concept_content=concept_content,
            page_number=None,
            language=language,
            category=category,
        )
        db.add(kb_entry)
        stored_count += 1
    
    return stored_count


def main():
    """Main function to seed curriculum data."""
    print("=" * 60)
    print("🌱 XploreKodo Curriculum Seeding Script")
    print("=" * 60)
    print()
    
    # Verify Gemini API key
    api_key = config.GEMINI_API_KEY or ""
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env file")
        print("   Please add GEMINI_API_KEY=your_key to your .env file")
        sys.exit(1)
    
    print("✅ Gemini API key found")
    print()
    
    db: Session = SessionLocal()
    total_stored = 0
    
    try:
        # Step 1: Fetch JLPT N5 words
        jlpt_words = fetch_jlpt_n5_words()
        
        if not jlpt_words:
            print("⚠️  No JLPT N5 words fetched. Continuing with caregiving terms only...")
        else:
            print(f"\n📝 Processing {len(jlpt_words)} JLPT N5 words...")
            print("   (This may take a few minutes for translations)")
            
            jlpt_entries = []
            for i, word_data in enumerate(jlpt_words, 1):
                # Extract word information
                word = word_data.get("word", word_data.get("reading", ""))
                reading = word_data.get("reading", "")
                meaning = word_data.get("meaning", word_data.get("english", ""))
                
                if not word:
                    continue
                
                # Translate to Nepali
                print(f"   [{i}/{len(jlpt_words)}] Translating: {word}...", end="\r")
                nepali = translate_to_nepali_with_gemini(word, meaning)
                
                # Format content
                content = format_vocabulary_content(word_data, nepali)
                
                jlpt_entries.append({
                    "concept_title": word,
                    "concept_content": content,
                    "language": "ja",
                })
            
            print(f"\n✅ Processed {len(jlpt_entries)} JLPT N5 words")
            
            # Store JLPT words
            stored = store_in_knowledge_base(
                jlpt_entries,
                source_file="jlpt_vocab_api_n5",
                category="jlpt_n5_vocabulary",
                db=db
            )
            total_stored += stored
            print(f"✅ Stored {stored} new JLPT N5 entries")
            print()
        
        # Step 2: Process caregiving terms
        print("🏥 Processing 20 caregiving terms...")
        print("   (Translating to Nepali...)")
        
        caregiving_entries = []
        for i, (japanese, english) in enumerate(CAREGIVING_TERMS, 1):
            print(f"   [{i}/{len(CAREGIVING_TERMS)}] Translating: {japanese} ({english})...", end="\r")
            
            # Translate to Nepali
            nepali = translate_to_nepali_with_gemini(japanese, english)
            
            # Format content
            content = f"Word: {japanese}\nEnglish: {english}\nNepali: {nepali}"
            
            caregiving_entries.append({
                "concept_title": japanese,
                "concept_content": content,
                "language": "ja",
            })
        
        print(f"\n✅ Processed {len(caregiving_entries)} caregiving terms")
        
        # Store caregiving terms
        stored = store_in_knowledge_base(
            caregiving_entries,
            source_file="manual_caregiving_terms",
            category="caregiving_vocabulary",
            db=db
        )
        total_stored += stored
        print(f"✅ Stored {stored} new caregiving entries")
        print()
        
        # Commit all changes
        db.commit()
        
        print("=" * 60)
        print(f"🎉 SUCCESS! Total entries stored: {total_stored}")
        print("=" * 60)
        
        # Show summary
        total_in_db = db.query(KnowledgeBase).count()
        print(f"\n📊 Total entries in knowledge_base: {total_in_db}")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

