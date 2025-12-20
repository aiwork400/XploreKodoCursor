"""
Seed knowledge_base table with JLPT N4/N5 vocabulary from Jisho API.

Fetches 50 terms related to 'Caregiving, Body Parts, and Daily Greetings'
and stores them in the knowledge_base table for Socratic simulation.
"""

from __future__ import annotations

import sys
import time
import io
from pathlib import Path
from typing import Optional

import requests
from sqlalchemy.orm import Session

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from database.db_manager import KnowledgeBase, SessionLocal

# Jisho API endpoint
JISHO_API_URL = "https://jisho.org/api/v1/search/words"

# Keywords to search for relevant vocabulary
SEARCH_KEYWORDS = [
    # Caregiving terms
    "care", "nurse", "patient", "elderly", "help", "assist", "support",
    "health", "medicine", "hospital", "doctor", "treatment",
    # Body parts
    "head", "hand", "foot", "eye", "ear", "mouth", "nose", "body",
    "arm", "leg", "face", "back", "chest", "stomach", "heart",
    # Daily greetings
    "hello", "good morning", "good evening", "good night", "thank you",
    "please", "excuse me", "sorry", "goodbye", "see you",
]

# Target categories for filtering
TARGET_CATEGORIES = [
    "caregiving",
    "body_parts",
    "daily_greetings",
    "vocabulary",
]

# Fallback curated vocabulary (common JLPT N4/N5 terms)
CURATED_VOCABULARY = [
    # Daily Greetings
    {"word": "おはよう", "reading": "おはよう", "meanings": ["good morning"], "category": "daily_greetings"},
    {"word": "こんにちは", "reading": "こんにちは", "meanings": ["hello", "good afternoon"], "category": "daily_greetings"},
    {"word": "こんばんは", "reading": "こんばんは", "meanings": ["good evening"], "category": "daily_greetings"},
    {"word": "おやすみ", "reading": "おやすみ", "meanings": ["good night"], "category": "daily_greetings"},
    {"word": "ありがとう", "reading": "ありがとう", "meanings": ["thank you"], "category": "daily_greetings"},
    {"word": "すみません", "reading": "すみません", "meanings": ["excuse me", "sorry"], "category": "daily_greetings"},
    {"word": "さようなら", "reading": "さようなら", "meanings": ["goodbye"], "category": "daily_greetings"},
    {"word": "お願いします", "reading": "おねがいします", "meanings": ["please"], "category": "daily_greetings"},
    {"word": "いただきます", "reading": "いただきます", "meanings": ["thank you for the meal (before eating)"], "category": "daily_greetings"},
    {"word": "ごちそうさまでした", "reading": "ごちそうさまでした", "meanings": ["thank you for the meal (after eating)"], "category": "daily_greetings"},
    
    # Body Parts
    {"word": "頭", "reading": "あたま", "meanings": ["head"], "category": "body_parts"},
    {"word": "手", "reading": "て", "meanings": ["hand"], "category": "body_parts"},
    {"word": "足", "reading": "あし", "meanings": ["foot", "leg"], "category": "body_parts"},
    {"word": "目", "reading": "め", "meanings": ["eye"], "category": "body_parts"},
    {"word": "耳", "reading": "みみ", "meanings": ["ear"], "category": "body_parts"},
    {"word": "口", "reading": "くち", "meanings": ["mouth"], "category": "body_parts"},
    {"word": "鼻", "reading": "はな", "meanings": ["nose"], "category": "body_parts"},
    {"word": "体", "reading": "からだ", "meanings": ["body"], "category": "body_parts"},
    {"word": "腕", "reading": "うで", "meanings": ["arm"], "category": "body_parts"},
    {"word": "顔", "reading": "かお", "meanings": ["face"], "category": "body_parts"},
    {"word": "背中", "reading": "せなか", "meanings": ["back"], "category": "body_parts"},
    {"word": "胸", "reading": "むね", "meanings": ["chest"], "category": "body_parts"},
    {"word": "お腹", "reading": "おなか", "meanings": ["stomach", "belly"], "category": "body_parts"},
    {"word": "心臓", "reading": "しんぞう", "meanings": ["heart"], "category": "body_parts"},
    {"word": "首", "reading": "くび", "meanings": ["neck"], "category": "body_parts"},
    
    # Caregiving
    {"word": "介護", "reading": "かいご", "meanings": ["nursing care", "caregiving"], "category": "caregiving"},
    {"word": "看護", "reading": "かんご", "meanings": ["nursing"], "category": "caregiving"},
    {"word": "患者", "reading": "かんじゃ", "meanings": ["patient"], "category": "caregiving"},
    {"word": "高齢者", "reading": "こうれいしゃ", "meanings": ["elderly person"], "category": "caregiving"},
    {"word": "助ける", "reading": "たすける", "meanings": ["to help", "to assist"], "category": "caregiving"},
    {"word": "健康", "reading": "けんこう", "meanings": ["health"], "category": "caregiving"},
    {"word": "薬", "reading": "くすり", "meanings": ["medicine"], "category": "caregiving"},
    {"word": "病院", "reading": "びょういん", "meanings": ["hospital"], "category": "caregiving"},
    {"word": "医者", "reading": "いしゃ", "meanings": ["doctor"], "category": "caregiving"},
    {"word": "治療", "reading": "ちりょう", "meanings": ["treatment", "medical care"], "category": "caregiving"},
    {"word": "痛い", "reading": "いたい", "meanings": ["painful", "it hurts"], "category": "caregiving"},
    {"word": "熱", "reading": "ねつ", "meanings": ["fever"], "category": "caregiving"},
    {"word": "食事", "reading": "しょくじ", "meanings": ["meal"], "category": "caregiving"},
    {"word": "入浴", "reading": "にゅうよく", "meanings": ["bathing"], "category": "caregiving"},
    {"word": "安全", "reading": "あんぜん", "meanings": ["safety"], "category": "caregiving"},
]


def fetch_jisho_vocabulary(keyword: str, limit: int = 10) -> list[dict]:
    """
    Fetch vocabulary from Jisho API for a given keyword.
    
    Args:
        keyword: Search keyword (English)
        limit: Maximum number of results to return
        
    Returns:
        List of vocabulary entries with Japanese, reading, and meanings
    """
    try:
        params = {"keyword": keyword}
        response = requests.get(JISHO_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("data", [])[:limit]
        
        vocabulary = []
        for result in results:
            japanese = result.get("japanese", [])
            senses = result.get("senses", [])
            
            if not japanese or not senses:
                continue
            
            # Get primary Japanese word and reading
            primary_jp = japanese[0]
            word = primary_jp.get("word", "")
            reading = primary_jp.get("reading", "")
            
            # Get meanings
            meanings = []
            for sense in senses:
                english_defs = sense.get("english_definitions", [])
                meanings.extend(english_defs)
            
            if word or reading:
                vocabulary.append({
                    "word": word,
                    "reading": reading,
                    "meanings": meanings,
                    "parts_of_speech": senses[0].get("parts_of_speech", []) if senses else [],
                })
        
        return vocabulary
        
    except Exception as e:
        print(f"   [WARN] Error fetching vocabulary for '{keyword}': {e}")
        return []


def categorize_vocabulary(vocab: dict, keyword: str) -> Optional[str]:
    """
    Categorize vocabulary based on keyword and content.
    
    Returns:
        Category string or None
    """
    word = vocab.get("word", "").lower()
    reading = vocab.get("reading", "").lower()
    meanings_str = " ".join(vocab.get("meanings", [])).lower()
    keyword_lower = keyword.lower()
    
    # Body parts
    body_parts_keywords = ["head", "hand", "foot", "eye", "ear", "mouth", "nose", 
                          "body", "arm", "leg", "face", "back", "chest", "stomach", "heart"]
    if any(bp in keyword_lower for bp in body_parts_keywords):
        return "body_parts"
    
    # Daily greetings
    greeting_keywords = ["hello", "good morning", "good evening", "good night", 
                        "thank you", "please", "excuse me", "sorry", "goodbye"]
    if any(g in keyword_lower for g in greeting_keywords):
        return "daily_greetings"
    
    # Caregiving
    caregiving_keywords = ["care", "nurse", "patient", "elderly", "help", "assist", 
                          "support", "health", "medicine", "hospital", "doctor", "treatment"]
    if any(cg in keyword_lower for cg in caregiving_keywords):
        return "caregiving"
    
    return "vocabulary"


def format_vocabulary_content(vocab: dict) -> str:
    """
    Format vocabulary entry as a structured text content.
    
    Returns:
        Formatted string with word, reading, meanings, and parts of speech
    """
    word = vocab.get("word", "")
    reading = vocab.get("reading", "")
    meanings = vocab.get("meanings", [])
    parts_of_speech = vocab.get("parts_of_speech", [])
    
    content_parts = []
    
    if word:
        content_parts.append(f"Word: {word}")
    if reading:
        content_parts.append(f"Reading: {reading}")
    
    if meanings:
        meanings_str = "; ".join(meanings)
        content_parts.append(f"Meanings: {meanings_str}")
    
    if parts_of_speech:
        pos_str = ", ".join(parts_of_speech)
        content_parts.append(f"Parts of Speech: {pos_str}")
    
    return "\n".join(content_parts)


def collect_vocabulary() -> list[dict]:
    """
    Collect 50 vocabulary terms from Jisho API, with curated fallback.
    
    Returns:
        List of vocabulary dictionaries with category
    """
    all_vocabulary = []
    seen_words = set()  # Avoid duplicates
    
    print("[INFO] Fetching vocabulary from Jisho API...")
    print(f"[INFO] Searching {len(SEARCH_KEYWORDS)} keywords...\n")
    
    # Try to fetch from API first
    for i, keyword in enumerate(SEARCH_KEYWORDS, 1):
        print(f"   [{i}/{len(SEARCH_KEYWORDS)}] Searching: '{keyword}'...", end=" ", flush=True)
        
        vocab_list = fetch_jisho_vocabulary(keyword, limit=5)
        
        for vocab in vocab_list:
            word = vocab.get("word") or vocab.get("reading", "")
            if not word or word in seen_words:
                continue
            
            seen_words.add(word)
            category = categorize_vocabulary(vocab, keyword)
            
            all_vocabulary.append({
                **vocab,
                "category": category,
                "search_keyword": keyword,
            })
            
            if len(all_vocabulary) >= 50:
                print(f"[OK] Found {len(vocab_list)} terms (Total: {len(all_vocabulary)})")
                break
        
        if len(all_vocabulary) >= 50:
            break
        
        print(f"[OK] Found {len(vocab_list)} terms (Total: {len(all_vocabulary)})")
        
        # Rate limiting - be respectful to the API
        time.sleep(0.5)
    
    # If we don't have 50 terms, supplement with curated vocabulary
    if len(all_vocabulary) < 50:
        needed = 50 - len(all_vocabulary)
        print(f"\n[INFO] Only found {len(all_vocabulary)} terms from API.")
        print(f"[INFO] Supplementing with {needed} curated vocabulary terms...\n")
        
        for curated in CURATED_VOCABULARY:
            if len(all_vocabulary) >= 50:
                break
            
            word = curated.get("word") or curated.get("reading", "")
            if word and word not in seen_words:
                seen_words.add(word)
                all_vocabulary.append({
                    "word": curated.get("word", ""),
                    "reading": curated.get("reading", ""),
                    "meanings": curated.get("meanings", []),
                    "parts_of_speech": [],
                    "category": curated.get("category", "vocabulary"),
                    "search_keyword": "curated",
                })
    
    return all_vocabulary[:50]  # Ensure exactly 50


def store_vocabulary_in_database(vocabulary: list[dict], db: Session) -> int:
    """
    Store vocabulary in knowledge_base table.
    
    Args:
        vocabulary: List of vocabulary dictionaries
        db: Database session
        
    Returns:
        Number of new entries stored
    """
    stored_count = 0
    source_file = "jisho_api_jlpt_n4_n5"
    
    for vocab in vocabulary:
        word = vocab.get("word") or vocab.get("reading", "")
        if not word:
            continue
        
        # Check if already exists
        existing = db.query(KnowledgeBase).filter(
            KnowledgeBase.source_file == source_file,
            KnowledgeBase.concept_title == word,
            KnowledgeBase.category == vocab.get("category", "vocabulary")
        ).first()
        
        if existing:
            # Update existing entry
            existing.concept_content = format_vocabulary_content(vocab)
            continue
        
        # Create new entry
        kb_entry = KnowledgeBase(
            source_file=source_file,
            concept_title=word,
            concept_content=format_vocabulary_content(vocab),
            page_number=None,  # Not applicable for API data
            language="ja",
            category=vocab.get("category", "vocabulary"),
        )
        db.add(kb_entry)
        stored_count += 1
    
    return stored_count


def main():
    """Main function to fetch and store vocabulary."""
    print("=" * 80)
    print("JLPT N4/N5 Vocabulary Seeder")
    print("=" * 80)
    print("\nTarget: 50 terms related to 'Caregiving, Body Parts, and Daily Greetings'")
    print("Source: Jisho API (https://jisho.org/api/)\n")
    
    db: Session = SessionLocal()
    try:
        # Collect vocabulary
        vocabulary = collect_vocabulary()
        
        if not vocabulary:
            print("\n[ERROR] No vocabulary collected. Check API connection.")
            return
        
        print(f"\n[INFO] Collected {len(vocabulary)} vocabulary terms")
        
        # Show category breakdown
        categories = {}
        for vocab in vocabulary:
            cat = vocab.get("category", "vocabulary")
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\n[INFO] Category breakdown:")
        for cat, count in sorted(categories.items()):
            print(f"   - {cat}: {count} terms")
        
        # Store in database
        print("\n[INFO] Storing vocabulary in knowledge_base table...")
        stored = store_vocabulary_in_database(vocabulary, db)
        db.commit()
        
        print(f"[SUCCESS] Stored {stored} new vocabulary terms in database")
        
        # Show sample entries
        print("\n[INFO] Sample vocabulary entries:")
        sample = db.query(KnowledgeBase).filter(
            KnowledgeBase.source_file == "jisho_api_jlpt_n4_n5"
        ).limit(5).all()
        
        for kb in sample:
            # Handle encoding for Japanese characters
            try:
                title = kb.concept_title
                content_preview = kb.concept_content[:100]
            except UnicodeEncodeError:
                title = kb.concept_title.encode('ascii', 'replace').decode('ascii')
                content_preview = kb.concept_content[:100].encode('ascii', 'replace').decode('ascii')
            
            print(f"\n   Title: {title}")
            print(f"   Category: {kb.category}")
            print(f"   Content preview: {content_preview}...")
        
        print("\n" + "=" * 80)
        print("[SUCCESS] Vocabulary seeding complete!")
        print("=" * 80)
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

