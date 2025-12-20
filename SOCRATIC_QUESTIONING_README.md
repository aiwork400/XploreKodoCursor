# Socratic Questioning Implementation

## Overview

The TrainingAgent now implements **Socratic Questioning** for caregiving candidates, following the principle: **NEVER give answers - only ask questions that lead candidates to discover the correct Japanese caregiving practice**.

## Features

### 1. **Socratic Method**
- The agent asks questions, never provides direct answers
- Guides candidates through discovery-based learning
- Uses follow-up questions to help candidates reach complete understanding

### 2. **Multi-Language Support**
- Questions are delivered in **Japanese + Nepali pairs** using Google Cloud Translate
- Each question is presented in:
  - English (original)
  - Japanese (translated)
  - Nepali (translated)

### 3. **Persistence**
- All Socratic interactions are saved to PostgreSQL `curriculum_progress.dialogue_history` (JSONB column)
- Tracks complete learning journey:
  - Questions asked
  - Candidate responses
  - Timestamps
  - Learning objectives

### 4. **Topic: Japanese Bedside Etiquette (Omotenashi)**
- Starts with 'Omotenashi' - the Japanese concept of anticipatory hospitality
- 5 progressive Socratic questions that guide candidates to discover:
  - Greeting and acknowledgment
  - Reading non-verbal cues
  - Dignity and privacy
  - Respect for personal space
  - Closure and gratitude

## Usage

### Basic Usage

```python
from agency.training_agent.socratic_questioning_tool import SocraticQuestioningTool

# Start a new Socratic session
tool = SocraticQuestioningTool(
    candidate_id="siddharth_test",
    topic="omotenashi",
    start_new_session=True
)
result = tool.run()
print(result)
```

### Continuing a Dialogue

```python
# Continue with candidate's response
tool = SocraticQuestioningTool(
    candidate_id="siddharth_test",
    topic="omotenashi",
    candidate_response="I should greet them politely"
)
result = tool.run()
print(result)
```

## Database Schema

The `curriculum_progress` table now includes:

```sql
dialogue_history JSONB
```

Stores dialogue entries in this format:
```json
[
  {
    "question_id": "omotenashi_1",
    "topic": "omotenashi",
    "question": {
      "english": "When you enter a patient's room...",
      "japanese": "[Japanese translation]",
      "nepali": "[Nepali translation]"
    },
    "learning_objective": "Understanding the importance of greeting...",
    "hint_if_stuck": "Think about respect...",
    "question_timestamp": "2025-12-19T17:30:00Z",
    "candidate_answer": "I should greet them",
    "answer_timestamp": "2025-12-19T17:31:00Z"
  }
]
```

## Configuration

### Google Cloud Translate Setup

1. **Install dependencies:**
   ```bash
   pip install google-cloud-translate>=3.15.0
   ```

2. **Set environment variables in `.env`:**
   ```env
   GOOGLE_CLOUD_TRANSLATE_PROJECT_ID=your-project-id
   GOOGLE_CLOUD_TRANSLATE_CREDENTIALS_PATH=/path/to/credentials.json
   ```

3. **Fallback behavior:**
   - If Google Cloud Translate is not configured, the tool will use placeholder translations
   - The tool will still function, but translations will be marked as placeholders

## Example Socratic Dialogue

**Question 1:**
- **English:** "When you enter a patient's room in Japan, what do you think is the first thing you should do? Why do you think that matters?"
- **Japanese:** "[Translated]"
- **Nepali:** "[Translated]"

**Candidate Response (Partial):**
"I should greet them."

**Follow-Up Question (NOT the answer):**
"That's a good start! Now, think about HOW you would greet them. In Japan, what specific words or gestures show respect when entering someone's personal space?"

**Continue until candidate discovers:**
- The importance of greeting (aisatsu)
- Specific Japanese phrases (おはようございます, etc.)
- Body language and respect
- Why this matters in Japanese caregiving culture

## Integration with TrainingAgent

The `SocraticQuestioningTool` is now integrated into the TrainingAgent:

```python
from agency.training_agent.training_agent import TrainingAgent

agent = TrainingAgent()
# The agent now has access to SocraticQuestioningTool
```

## Migration

If you have an existing database, run:

```bash
psql -U postgres -d xplorekodo -f database/migration_add_dialogue_history.sql
```

Or use Python:

```python
from database.db_manager import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE curriculum_progress ADD COLUMN IF NOT EXISTS dialogue_history JSONB"))
    conn.commit()
```

## Next Steps

1. **Install Google Cloud Translate:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure credentials** in `.env` file

3. **Test the Socratic Questioning:**
   ```python
   from agency.training_agent.socratic_questioning_tool import SocraticQuestioningTool
   
   tool = SocraticQuestioningTool(
       candidate_id="siddharth_test",
       topic="omotenashi"
   )
   result = tool.run()
   print(result)
   ```

## Notes

- The agent **NEVER gives answers** - it only asks questions
- All interactions are persisted to the database
- Multi-language support enhances accessibility for Nepali-speaking candidates
- The Socratic method helps candidates internalize Japanese caregiving principles through discovery

