"""
Seed Life in Japan Knowledge Base

Populates the life_in_japan_kb table with 5 core support categories:
1. Legal: SSW rights and overtime laws
2. Finance: Opening a Japan Post Bank account
3. Visa: Transitioning from Student to Work status
4. Housing: Understanding Shikikin and Reikin
5. Emergency: Medical emergency (119) communication protocols
"""

from __future__ import annotations

import sys
import io
from pathlib import Path
from datetime import datetime, timezone

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from database.db_manager import LifeInJapanKB, SessionLocal, init_db


# Core knowledge base entries
LIFE_IN_JAPAN_KB_ENTRIES = [
    {
        "topic": "ssw_rights_overtime",
        "category": "legal",
        "title": "SSW (Specified Skilled Worker) Rights and Overtime Laws",
        "content": """**SSW Rights and Overtime Laws in Japan**

**Basic Rights:**
- SSW visa holders have the same labor rights as Japanese workers
- Maximum working hours: 8 hours per day, 40 hours per week
- Overtime must be agreed upon in writing (36 Agreement - サブロク協定)

**Overtime Regulations:**
- Overtime pay: 125% of regular wage for first 60 hours/month, 150% for hours exceeding 60/month
- Annual overtime limit: 720 hours (with 36 Agreement)
- Rest periods: At least 1 hour break for 8+ hour shifts

**Important Notes:**
- Your employer must provide a written employment contract in Japanese and your native language
- Keep records of your work hours
- If overtime exceeds limits, contact the Labor Standards Inspection Office (労働基準監督署)

**Resources:**
- Labor Standards Inspection Office: 0570-003-110 (toll-free)
- Ministry of Health, Labor and Welfare website for SSW information""",
        "language": "en",
        "source": "Ministry of Health, Labor and Welfare (厚生労働省)"
    },
    {
        "topic": "japan_post_bank_account",
        "category": "financial",
        "title": "Opening a Japan Post Bank Account",
        "content": """**How to Open a Japan Post Bank Account (ゆうちょ銀行)**

**Required Documents:**
1. Valid residence card (在留カード) or passport
2. Proof of address (住民票 - Certificate of Residence)
3. Personal seal (印鑑) or signature
4. Valid ID (passport or driver's license)

**Steps:**
1. Visit any Japan Post Bank branch (ゆうちょ銀行)
2. Fill out the account application form (口座開設申込書)
3. Present your documents
4. Choose account type: Regular savings (普通預金) or Time deposit (定期預金)
5. Receive your bankbook (通帳) and cash card (キャッシュカード) within 1-2 weeks

**Important Information:**
- Initial deposit: Usually 1 yen minimum
- ATM fees: Free at Japan Post ATMs, fees apply at convenience stores
- Online banking: Available after account setup
- International transfers: Possible but may require additional documentation

**Tips:**
- Bring a Japanese-speaking friend if possible
- Some branches may require appointment (予約)
- Keep your bankbook and card safe - report loss immediately""",
        "language": "en",
        "source": "Japan Post Bank Official Guidelines"
    },
    {
        "topic": "student_to_work_visa",
        "category": "visa",
        "title": "Transitioning from Student Visa to Work Visa Status",
        "content": """**Changing from Student Visa (留学) to Work Visa**

**Eligibility Requirements:**
1. Complete your studies or graduate from a recognized institution
2. Have a job offer from a Japanese company
3. Meet the specific requirements for your work visa category (e.g., Engineer/Specialist in Humanities, SSW)

**Required Documents:**
1. Certificate of Eligibility (COE) application form
2. Employment contract or job offer letter
3. Company registration documents (from employer)
4. Academic certificates (diploma, transcripts)
5. Passport and current residence card
6. Application for Change of Status (在留資格変更許可申請)

**Process:**
1. Your employer applies for COE at Immigration Bureau (入国管理局)
2. Once COE is approved (2-4 weeks), you apply for status change
3. Submit application at your local Immigration Bureau
4. Processing time: 2-4 weeks
5. Receive new residence card with work visa status

**Important Notes:**
- You can work part-time (up to 28 hours/week) on student visa, but full-time work requires work visa
- Start the process 2-3 months before your student visa expires
- If your student visa expires before work visa is approved, you may need to extend student visa

**Where to Apply:**
- Regional Immigration Bureau (地方入国管理局)
- Book appointment online to avoid long waits""",
        "language": "en",
        "source": "Immigration Services Agency of Japan (出入国在留管理庁)"
    },
    {
        "topic": "shikikin_reikin",
        "category": "housing",
        "title": "Understanding Shikikin (敷金) and Reikin (礼金) in Japan",
        "content": """**Shikikin (Security Deposit) and Reikin (Key Money) Explained**

**Shikikin (敷金 - Security Deposit):**
- Refundable deposit paid to landlord
- Usually 1-2 months' rent
- Used to cover damages or unpaid rent
- Should be returned (minus deductions) when you move out
- If no damages, you get it back

**Reikin (礼金 - Key Money/Gratitude Money):**
- Non-refundable payment to landlord
- Usually 1-2 months' rent
- Traditional practice in Japan (showing gratitude)
- You will NOT get this back when moving out
- Some modern apartments don't require reikin

**Total Initial Costs:**
When renting in Japan, you typically pay:
- First month's rent
- Shikikin (1-2 months) - refundable
- Reikin (1-2 months) - non-refundable
- Agent fee (仲介手数料) - usually 1 month's rent
- Insurance (火災保険) - usually 10,000-20,000 yen

**Example:**
For a 50,000 yen/month apartment:
- Rent: 50,000 yen
- Shikikin: 100,000 yen (2 months)
- Reikin: 100,000 yen (2 months)
- Agent fee: 50,000 yen
- Insurance: 15,000 yen
- **Total: 315,000 yen upfront**

**Tips:**
- Look for apartments with "敷金0" (no shikikin) or "礼金0" (no reikin)
- Negotiate if possible (especially in less popular areas)
- Read your contract carefully - understand refund conditions
- Take photos when moving in to document condition""",
        "language": "en",
        "source": "Real Estate Transaction Act (宅地建物取引業法)"
    },
    {
        "topic": "medical_emergency_119",
        "category": "emergency",
        "title": "Medical Emergency (119) Communication Protocols in Japan",
        "content": """**Calling 119 for Medical Emergency in Japan**

**When to Call 119:**
- Serious injury or illness
- Unconsciousness
- Severe breathing difficulties
- Chest pain or suspected heart attack
- Severe allergic reaction
- Any life-threatening situation

**What to Say (Basic Phrases):**
- "救急車をお願いします" (Kyūkyūsha wo onegaishimasu) - "Please send an ambulance"
- "住所は..." (Jūsho wa...) - "The address is..."
- "怪我をしました" (Kega wo shimashita) - "I'm injured"
- "病気です" (Byōki desu) - "I'm sick"

**Important Information to Provide:**
1. **Location**: Exact address, nearest landmark, building name and room number
2. **Situation**: What happened, symptoms, number of people affected
3. **Your phone number**: So they can call back if needed
4. **Language**: If you don't speak Japanese, say "英語で話せますか?" (Eigo de hanasemasu ka?) - "Can you speak English?"

**What Happens Next:**
- Ambulance arrives (usually 5-10 minutes in cities)
- Paramedics assess the situation
- You're taken to the nearest appropriate hospital
- Hospital fees: Usually 30% of cost (with health insurance), 100% without insurance

**Emergency Numbers:**
- 119: Ambulance/Fire
- 110: Police
- 118: Coast Guard

**Tips:**
- Keep your address written in Japanese on your phone
- If possible, have a Japanese speaker help you call
- Ambulance service is free in Japan (no charge for the ambulance itself)
- Bring your health insurance card (健康保険証) to the hospital

**Preparing for Emergency:**
- Write your address in Japanese and keep it accessible
- Know your blood type and allergies
- Keep emergency contact information handy""",
        "language": "en",
        "source": "Fire and Disaster Management Agency (消防庁)"
    }
]


def seed_life_in_japan_kb():
    """Seed the life_in_japan_kb table with core support categories."""
    print("=" * 60)
    print("🌱 Seeding Life in Japan Knowledge Base")
    print("=" * 60)
    
    # Initialize database
    init_db()
    
    db: Session = SessionLocal()
    try:
        seeded_count = 0
        updated_count = 0
        
        for entry_data in LIFE_IN_JAPAN_KB_ENTRIES:
            # Check if entry already exists
            existing = db.query(LifeInJapanKB).filter(
                LifeInJapanKB.topic == entry_data["topic"],
                LifeInJapanKB.language == entry_data["language"]
            ).first()
            
            if existing:
                # Update existing entry
                existing.title = entry_data["title"]
                existing.content = entry_data["content"]
                existing.category = entry_data["category"]
                existing.source = entry_data.get("source")
                existing.updated_at = datetime.now(timezone.utc)
                updated_count += 1
                print(f"✅ Updated: {entry_data['title']}")
            else:
                # Create new entry
                kb_entry = LifeInJapanKB(
                    topic=entry_data["topic"],
                    category=entry_data["category"],
                    title=entry_data["title"],
                    content=entry_data["content"],
                    language=entry_data["language"],
                    source=entry_data.get("source")
                )
                db.add(kb_entry)
                seeded_count += 1
                print(f"✅ Added: {entry_data['title']}")
        
        db.commit()
        
        print("\n" + "=" * 60)
        print(f"🎉 Seeding Complete!")
        print(f"   Added: {seeded_count} entries")
        print(f"   Updated: {updated_count} entries")
        print("=" * 60)
        
        # Show summary by category
        print("\n📊 Entries by Category:")
        categories = {}
        for entry in db.query(LifeInJapanKB).all():
            cat = entry.category or "uncategorized"
            categories[cat] = categories.get(cat, 0) + 1
        
        for cat, count in sorted(categories.items()):
            print(f"   • {cat}: {count} entries")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_life_in_japan_kb()

