# SYSTEM CONTEXT: XPLORA KODO PLATFORM (PROJECT "MYPROJECT")

## 1. Project Overview & Architecture
Xplora Kodo is a trilingual (English, Japanese, Nepali) Agentic AI (AAI) training platform designed for Commercial Centers.
- **Backend:** FastAPI, Swarm Agency (Agency Swarm), Gemini 2.0.
- **Frontend:** Streamlit Dashboard with a sidebar-contained Concierge UI.
- **Core Primitives:** "All-in-One Shop" standards (Stable, Professional, Scalable).

## 2. Current Architectural State
- **Concierge UI:** Contained in `dashboard/app.py` within `with st.sidebar:`.
- **Reporting:** `agency/training_agent/report_generator.py` uses Helvetica (English-only) to prevent Japanese font-mapping crashes.
- **Socratic Agent:** `video_socratic_assessment_tool.py` manages a tiered questioning logic.
- **Storage:** Standardized directories at `app/static/videos/[track_name]/`.

## 3. The "Immersion-Bridge" Workflow (Hard Requirement)
- **Videos:** Japanese-only audio/captions for immersion.
- **Transcripts:** Stored as `[video_name]_En.txt`. 
- **LLM Logic:** Backend must read the `.txt` file, generate a Nepali translation, and display both in the UI below the video before triggering Socratic questions.

## 4. Active Curriculum: Food/Tech (HACCP)
- **Status:** Kaigo (Care-giving) materials have been DISCARDED. 
- **Knowledge Base:** Japanese HACCP Standards (Cold <10°C, Frozen <-15°C).
- **Current Lesson:** FT-01 (Freezer Temperatures) & FT-04 (Sanitization: Seiso, Sakkin, Kansou).

## 5. Immediate Technical Task
"Implement the Immersion-Bridge Directory and Logic: 
1. Create directories: `app/static/videos/food_tech/`, `academic/`, and `tech_ai/`.
2. Rewrite `dashboard/app.py` to fetch `[video_name]_En.txt` and display a bilingual (English/Nepali) transcript block via LLM translation below the video player.
3. Ensure the 'Food/Tech' track is the default active state in the sidebar."

# XPLORA KODO: MASTER SYSTEM SPECIFICATION

## 🎯 PRODUCT VISION
A high-stakes, trilingual (EN, JP, NE) vocational training platform using Agentic AI (AAI) to bridge the gap between foreign talent and the Japanese "Highly Skilled Professional" visa category.

## 🛠️ ARCHITECTURAL PILLARS (ALL-IN-ONE SHOP)
1. **Immersion-Bridge Workflow:** Japanese-only video immersion supported by LLM-generated bilingual (EN/NE) transcripts.
2. **Crash-Proof Reporting:** English-only PDF generation using standard fonts (Helvetica) to ensure 100% uptime for stakeholders.
3. **Triple-Track Logic:** - Food/Tech (HACCP/Kitchen Ops)
   - Academic (JLPT N5-N3 Mastery)
   - AI & Startup (Technical Visa Prep)

## 🚀 PHASE 2 & BEYOND: THE COMPLEX STACK
1. **Socratic Grading & TDD:** Every agent response must be validated against a "Bonus Vocabulary" list (e.g., Kousa-osen). 
2. **AR-VR Integration:** Future implementation of A-Frame/Three.js components to allow "Virtual Kitchen Walkthroughs" triggered by the Sensei.
3. **Database & State:** Transition from Session State to PostgreSQL for persistent student "Performance Passports."
4. **Payment Gateway:** Integration of Stripe for per-track or per-certification billing.
5. **Interview Simulation:** AI-driven mock interviews with "Stress-Testing" logic for Japanese business etiquette.

## 📜 DEVELOPMENT PROTOCOLS (FOR CURSOR/CLI)
- **Primary Font:** Helvetica (Global PDF standard).
- **Directory Standard:** `app/static/videos/[track]/` + `[video_name]_En.txt`.
- **Logic Rule:** Never use hardcoded Japanese strings in the PDF engine; always fetch from the translation bridge.