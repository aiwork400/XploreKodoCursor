"""
Sandbox: Socratic Conversation Logic Prototype for Food/Tech Module

This is a standalone script to test the 'Sensei' chat logic for HACCP training.
Run this script in the terminal to prototype the Socratic conversation flow.

Usage:
    python agency/sandbox_socratic_logic.py
"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google.genai not available. Install with: pip install google-generativeai")

# Import config for API key
try:
    import config
except ImportError:
    print("Warning: config.py not found. Make sure GEMINI_API_KEY is set in .env")
    config = None


def load_transcript() -> str:
    """Load the English transcript from the Food/Tech video."""
    transcript_path = project_root / "app" / "static" / "videos" / "food_tech" / "ft_3step_san_En.txt"
    
    if not transcript_path.exists():
        # Try alternative path
        transcript_path = project_root / "static" / "videos" / "food_tech" / "ft_3step_san_En.txt"
    
    if not transcript_path.exists():
        return "Transcript file not found. Using default context: This lesson covers the 3-step sanitization process (Seiso, Sakkin, Kansou) in Japanese commercial kitchens."
    
    try:
        with open(transcript_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading transcript: {e}")
        return "Error loading transcript. Using default context."


def create_sensei_prompt(transcript: str, conversation_history: list, timer_elapsed: int) -> str:
    """
    Create the Sensei prompt for Gemini 2.0 Flash.
    
    The Sensei acts as a Socratic teacher who:
    - Does NOT give direct answers
    - Asks guiding questions about HACCP and 3-step sanitization
    - Detects and responds in the user's language (English, Japanese, Nepali)
    - Shifts from 'Helpful Assistant' to 'Evaluator' after timer threshold
    """
    
    # Determine conversation phase based on timer
    if timer_elapsed < 180:
        phase = "helpful_assistant"
        phase_instruction = "You are in 'Helpful Assistant' mode. Guide the student with questions, but be supportive and encouraging."
    else:
        phase = "evaluator"
        phase_instruction = "You are now in 'Evaluator' mode. Assess the student's understanding more critically. Ask deeper questions to test their knowledge."
    
    # Build conversation history context
    history_text = ""
    if conversation_history:
        history_text = "\n\n**Previous Conversation:**\n"
        for msg in conversation_history[-5:]:  # Last 5 messages
            history_text += f"- {msg['role']}: {msg['content']}\n"
    
    prompt = f"""You are a Japanese Food Safety Sensei (Teacher) conducting a Socratic dialogue about HACCP (Hazard Analysis and Critical Control Points) and kitchen sanitization.

**Lesson Context (from video transcript):**
{transcript}

**Your Role:**
- You are a Socratic teacher. You DO NOT give direct answers.
- You ask guiding questions that help the student discover the answers themselves.
- You focus on HACCP principles and the 3-step sanitization process:
  * Seiso (清掃) - Cleaning: Removing visible dirt and debris
  * Sakkin (殺菌) - Disinfection: Killing harmful microorganisms
  * Kansou (乾燥) - Air-drying: Allowing surfaces to air-dry naturally (no towels)

**Language Detection:**
- Detect the language the student is using (English, Japanese, or Nepali).
- Respond in the SAME language the student uses.
- If the student mixes languages, respond in the primary language they're using.

**Current Phase: {phase.upper()}**
{phase_instruction}

**Key Topics to Explore:**
1. Temperature control: Cold storage (<10°C), Frozen storage (<-15°C)
2. 3-step sanitization: Why each step matters, what happens if you skip a step
3. Cross-contamination (Kousa-osen / 交差汚染)
4. Expiry management (Kigen-kanri / 期限管理)
5. Proper disinfection techniques (Shudoku / 消毒)

**Socratic Method Rules:**
- NEVER give the answer directly. Instead, ask: "What do you think would happen if...?"
- If the student is stuck, ask a simpler related question to guide them.
- If the student gives a partial answer, ask a follow-up to deepen understanding.
- Praise correct thinking, but challenge assumptions gently.
- If the student uses HACCP terminology (like Kousa-osen, Kigen-kanri, Shudoku), acknowledge it positively.

**Example Questions You Might Ask:**
- "The temperature log shows the walk-in freezer at -10°C. What does HACCP require for frozen storage?"
- "You're cleaning a prep table. Can you explain the difference between Seiso and Sakkin? Why is air-drying (Kansou) better than using a towel?"
- "What could happen if you skip the Kansou step and wipe the surface with a towel instead?"

{history_text}

**Student's Latest Input:**
User input: {conversation_history[-1]['content'] if conversation_history else 'Starting conversation'}

**Your Response (as Sensei, in the student's language, using Socratic questioning):**
"""
    
    return prompt


def initialize_gemini_client():
    """Initialize Gemini 2.0 Flash client."""
    if not GEMINI_AVAILABLE:
        print("Error: google.genai not available")
        return None
    
    # Get API key
    api_key = None
    if config and hasattr(config, 'GEMINI_API_KEY'):
        api_key = config.GEMINI_API_KEY
    else:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not found. Set it in .env file or environment variable.")
        return None
    
    try:
        client = genai.Client(api_key=api_key)
        return client
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")
        return None


def get_sensei_response(client, prompt: str) -> str:
    """Get response from Gemini Sensei."""
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        return f"Error getting response from Gemini: {e}"


def main():
    """Main conversation loop for testing Socratic logic."""
    print("=" * 70)
    print("Food/Tech Socratic Logic Sandbox - Sensei Chat Prototype")
    print("=" * 70)
    print()
    
    # Load transcript
    print("Loading transcript...")
    transcript = load_transcript()
    print(f"Transcript loaded ({len(transcript)} characters)")
    print()
    
    # Initialize Gemini client
    print("Initializing Gemini client...")
    client = initialize_gemini_client()
    if not client:
        print("Failed to initialize Gemini client. Exiting.")
        return
    print("Gemini client initialized successfully.")
    print()
    
    # Mock timer (simulates elapsed time in conversation)
    timer_elapsed = 0
    timer_increment = 30  # Increment by 30 seconds per exchange
    
    # Conversation history
    conversation_history = []
    
    # Initial Sensei greeting/question
    initial_question = "Welcome. I see the walk-in freezer is at -10°C today. Is this acceptable in a Japanese commercial kitchen? What is your next step?"
    print("=" * 70)
    print("SENSEI:")
    print(initial_question)
    print("=" * 70)
    print()
    
    conversation_history.append({
        "role": "sensei",
        "content": initial_question
    })
    
    # Conversation loop
    while True:
        # Get user input
        try:
            user_input = input("YOU: ").strip()
            
            if not user_input:
                continue
            
            # Exit commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\nEnding conversation. Goodbye!")
                break
            
            # Safety: Use repr() to prevent syntax errors
            safe_input = f"User input: {user_input!r}"
            
            # Add user message to history
            conversation_history.append({
                "role": "student",
                "content": user_input
            })
            
            # Increment timer
            timer_elapsed += timer_increment
            print(f"\n[Timer: {timer_elapsed}s | Phase: {'Evaluator' if timer_elapsed >= 180 else 'Helpful Assistant'}]")
            print()
            
            # Create Sensei prompt
            prompt = create_sensei_prompt(transcript, conversation_history, timer_elapsed)
            
            # Get Sensei response
            print("Sensei is thinking...")
            sensei_response = get_sensei_response(client, prompt)
            
            # Display response
            print("=" * 70)
            print("SENSEI:")
            print(sensei_response)
            print("=" * 70)
            print()
            
            # Add Sensei response to history
            conversation_history.append({
                "role": "sensei",
                "content": sensei_response
            })
            
        except KeyboardInterrupt:
            print("\n\nConversation interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again or type 'exit' to quit.")


if __name__ == "__main__":
    main()

