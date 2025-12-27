"""
Algebra 1 Coach - Claude Agent SDK Educational Tutor

A middle-school-friendly Algebra 1 tutoring agent that helps students build
strong problem-solving habits through a 6-stage coaching flow.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
from pathlib import Path

# Claude Agent SDK imports
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ResultMessage
)

# PDF parsing
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: PyMuPDF not installed. PDF support disabled.")
    print("Install with: pip install pymupdf")


class TutoringStage(Enum):
    """Stages of the tutoring flow (0-5)."""
    STAGE_0_SETUP = 0           # New problem setup
    STAGE_1_FIRST_ATTEMPT = 1   # First attempt coaching (attempts 1-2)
    STAGE_2_VALIDATION = 2      # Validate student's claimed answer
    STAGE_3_DIAGNOSE = 3        # Diagnose & repair (attempts 3-4)
    STAGE_4_FINAL_HINT = 4      # Final hint before reveal (attempt 5)
    STAGE_5_REVEAL = 5          # Answer reveal


class ConfidenceLevel(Enum):
    """Student confidence signals."""
    LOW = "low"
    MEDIUM = "med"
    HIGH = "high"


@dataclass
class TutoringState:
    """State variables for the tutoring session."""
    problem: str = ""
    attempt_count: int = 0
    reveal_now: bool = False
    student_age_band: str = "middle school"
    confidence_signal: Optional[ConfidenceLevel] = None
    current_stage: TutoringStage = TutoringStage.STAGE_0_SETUP
    problem_id: Optional[str] = None
    student_claimed_answer: bool = False  # True when student claims an answer
    answer_validated: bool = False        # True after validation complete
    problem_solved: bool = False          # True when correctly solved
    student_work_history: List[str] = field(default_factory=list)


def extract_problems_from_pdf(pdf_path: str) -> List[dict]:
    """
    Extract problems from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of dicts with 'id', 'text', and 'page' keys
    """
    if not PDF_SUPPORT:
        raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")

    problems = []
    doc = fitz.open(pdf_path)

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()

        # Simple problem extraction - split by common patterns
        # This can be customized based on the PDF format
        lines = text.strip().split('\n')
        current_problem = []
        problem_count = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect problem start (customize for your PDF format)
            # Common patterns: "1.", "1)", "Question 1", "Problem 1"
            import re
            problem_start = re.match(r'^(\d+)[.)\s]|^(Question|Problem)\s*\d+', line, re.IGNORECASE)

            if problem_start and current_problem:
                # Save previous problem
                problem_count += 1
                problems.append({
                    'id': f"p{page_num}_{problem_count}",
                    'text': '\n'.join(current_problem),
                    'page': page_num
                })
                current_problem = [line]
            else:
                current_problem.append(line)

        # Don't forget the last problem on the page
        if current_problem:
            problem_count += 1
            problems.append({
                'id': f"p{page_num}_{problem_count}",
                'text': '\n'.join(current_problem),
                'page': page_num
            })

    doc.close()
    return problems


def get_full_pdf_text(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    if not PDF_SUPPORT:
        raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")

    doc = fitz.open(pdf_path)
    full_text = ""

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        full_text += f"\n--- Page {page_num} ---\n{text}"

    doc.close()
    return full_text.strip()


class Algebra1Coach:
    """
    Middle-school-friendly Algebra 1 tutoring agent.

    Uses 6-stage flow:
    - Stage 0: New Problem Setup
    - Stage 1: First Attempt Coaching
    - Stage 2: Validation Path
    - Stage 3: Diagnose & Repair
    - Stage 4: Final Hint Before Reveal
    - Stage 5: Answer Reveal
    """

    SYSTEM_PROMPT_TEMPLATE = """You're like a favorite middle school math teacher—the kind who makes kids actually enjoy coming to class. You're here to help students figure things out themselves, not just give them answers.

## How You Talk
- Sound like a real person! Use contractions (you're, let's, don't, that's)
- Keep it SHORT: 1-4 sentences max. Middle schoolers tune out walls of text
- Be genuinely encouraging without being fake or over-the-top
- Use phrases like "Nice!", "Ooh, good thinking!", "Hmm, let's think about that...", "You're on the right track!"
- It's okay to be a little playful: "Uh oh, watch out for that trap!" or "Almost! So close!"
- Never sound like a textbook or a robot

## Current Problem
{problem}

## Session State
- Attempt count: {attempt_count}
- Current stage: Stage {stage_num} ({stage_name})
- Reveal answer now: {reveal_now}
- Student claimed answer: {claimed_answer}
- Problem solved: {problem_solved}
- Confidence level: {confidence}

---

## STAGE INSTRUCTIONS - Follow these based on current stage:

### STAGE 0 — Getting Started (attempt_count == 0)
**Goal:** Help them understand what they're solving.
**Do:** Ask ONE simple question to get them thinking.
Examples:
- "Okay! So what are we trying to find here?"
- "First things first—what type of problem is this? Equation? Graph? Word problem?"
- "What do you notice about this problem?"
**Don't:** Jump into formulas or start solving.

---

### STAGE 1 — First Tries (attempt_count 1-2)
**Goal:** Give a gentle nudge without doing the work for them.
**Do:** Pick ONE of these (just one!):
- Ask a guiding question: "What would be your first step?"
- Drop a small hint: "Take a closer look at what's on both sides of the equals sign..."
- Warn about a common mistake: "Heads up—don't forget to distribute to BOTH terms inside the parentheses!"
**Don't:** Solve it for them or give away the answer.

---

### STAGE 2 — They Think They've Got It (student claims an answer)
**Goal:** Make sure they actually understand, not just got lucky.
**Do:**
1. Ask how they got there: "Nice! Walk me through how you figured that out?"
2. Based on their explanation:
   - If they nailed it → "Exactly! That works because [brief reason]."
   - If their method is shaky → "Hmm, you might've gotten the right answer, but that method could trip you up on harder problems. Here's a more reliable way..."
**Don't:** Just say "correct" or "wrong" without checking their thinking.

---

### STAGE 3 — They're Struggling (attempt_count 3-4)
**Goal:** Figure out exactly where they're getting stuck.
**Do:** Ask ONE targeted question to find the issue:
- "When you distributed, did you multiply by both terms inside?"
- "Wait, did the sign flip when you divided by a negative?"
- "Which numbers are you using to find the slope?"
Then give ONE helpful hint based on what they say.
**Don't:** Give away the answer yet (unless reveal_now=true).

---

### STAGE 4 — Last Chance Before Reveal (attempt_count == 5)
**Goal:** One final push to help them get it themselves.
**Do:**
- If reveal_now=false: Give a clear, structured hint that sets up the final step
- If reveal_now=true: Skip to Stage 5
Example: "Okay, here's a big hint: after you simplify the left side, you should have 12x² - 6. Now what can you do with both sides?"

---

### STAGE 5 — Showing the Answer (reveal_now=true OR after 5 attempts)
**Goal:** Make sure they learn from it, not just copy the answer.
**Format:**
1. Quick encouragement: "Hey, this was a tricky one!" or "You were actually really close!"
2. **The answer:** State it clearly
3. **Why it works:** One simple sentence
4. **Two ways to solve it:**
   - Quick method 1
   - Quick method 2

---

## Remember
- You're talking to a middle schooler, not a college student
- Short and sweet beats long and thorough
- Sound human! Like you're actually in the room with them
- One thing at a time—don't overwhelm them"""

    def __init__(self):
        self.client: Optional[ClaudeSDKClient] = None
        self.state = TutoringState()
        self.options: Optional[ClaudeAgentOptions] = None

    def _get_stage_name(self) -> str:
        """Get human-readable stage name."""
        names = {
            TutoringStage.STAGE_0_SETUP: "New Problem Setup",
            TutoringStage.STAGE_1_FIRST_ATTEMPT: "First Attempt Coaching",
            TutoringStage.STAGE_2_VALIDATION: "Validation Path",
            TutoringStage.STAGE_3_DIAGNOSE: "Diagnose & Repair",
            TutoringStage.STAGE_4_FINAL_HINT: "Final Hint",
            TutoringStage.STAGE_5_REVEAL: "Answer Reveal"
        }
        return names.get(self.state.current_stage, "Unknown")

    def _build_system_prompt(self) -> str:
        """Build the system prompt with current state."""
        confidence_str = self.state.confidence_signal.value if self.state.confidence_signal else "not specified"

        return self.SYSTEM_PROMPT_TEMPLATE.format(
            problem=self.state.problem or "No problem loaded yet",
            attempt_count=self.state.attempt_count,
            stage_num=self.state.current_stage.value,
            stage_name=self._get_stage_name(),
            reveal_now=self.state.reveal_now,
            claimed_answer=self.state.student_claimed_answer,
            problem_solved=self.state.problem_solved,
            confidence=confidence_str
        )

    async def initialize(self):
        """Initialize the Claude Agent SDK client."""
        self.options = ClaudeAgentOptions(
            system_prompt=self._build_system_prompt(),
            allowed_tools=[],
            permission_mode="default"
        )

        self.client = ClaudeSDKClient(options=self.options)
        await self.client.connect()

    async def _update_system_prompt(self):
        """Update the system prompt with new state."""
        if self.client:
            await self.client.disconnect()

        self.options = ClaudeAgentOptions(
            system_prompt=self._build_system_prompt(),
            allowed_tools=[],
            permission_mode="default"
        )

        self.client = ClaudeSDKClient(options=self.options)
        await self.client.connect()

    def set_problem(self, problem: str, problem_id: Optional[str] = None):
        """Set a new problem and reset state."""
        self.state.problem = problem
        self.state.problem_id = problem_id
        self.state.attempt_count = 0
        self.state.reveal_now = False
        self.state.current_stage = TutoringStage.STAGE_0_SETUP
        self.state.student_claimed_answer = False
        self.state.answer_validated = False
        self.state.problem_solved = False
        self.state.student_work_history = []

    def set_student_profile(
        self,
        age_band: str = "middle school",
        confidence: Optional[ConfidenceLevel] = None
    ):
        """Set student profile information."""
        self.state.student_age_band = age_band
        self.state.confidence_signal = confidence

    def force_reveal(self):
        """Force the coach to reveal the answer."""
        self.state.reveal_now = True
        self.state.current_stage = TutoringStage.STAGE_5_REVEAL

    def mark_correct(self):
        """Mark the current problem as correctly solved."""
        self.state.problem_solved = True

    def _detect_answer_claim(self, message: str) -> bool:
        """Check if student is claiming an answer."""
        msg_lower = message.lower()

        answer_indicators = [
            "is the answer", "my answer", "i got", "the answer is",
            "i think it's", "it equals", "x =", "x=", "= ",
            "equals", "answer:", "final answer", "solution is",
            "it's ", "is it", "would it be", "i believe"
        ]

        return any(indicator in msg_lower for indicator in answer_indicators)

    def _determine_stage(self, student_message: str):
        """Determine the appropriate stage based on state and message."""
        # Stage 5: Reveal (highest priority)
        if self.state.reveal_now or self.state.attempt_count >= 5:
            self.state.current_stage = TutoringStage.STAGE_5_REVEAL
            return

        # Already solved - stay in Stage 5 for reflection
        if self.state.problem_solved:
            self.state.current_stage = TutoringStage.STAGE_5_REVEAL
            return

        # Stage 0: New problem setup
        if self.state.attempt_count == 0:
            self.state.current_stage = TutoringStage.STAGE_0_SETUP
            return

        # Stage 2: Validation (student claims answer)
        if self._detect_answer_claim(student_message) and not self.state.answer_validated:
            self.state.student_claimed_answer = True
            self.state.current_stage = TutoringStage.STAGE_2_VALIDATION
            return

        # Stage 1: First attempts (1-2)
        if self.state.attempt_count in [1, 2]:
            self.state.current_stage = TutoringStage.STAGE_1_FIRST_ATTEMPT
            return

        # Stage 3: Diagnose & Repair (3-4)
        if self.state.attempt_count in [3, 4]:
            self.state.current_stage = TutoringStage.STAGE_3_DIAGNOSE
            return

        # Stage 4: Final hint (attempt 5, but not yet reveal)
        if self.state.attempt_count == 5:
            self.state.current_stage = TutoringStage.STAGE_4_FINAL_HINT
            return

    async def respond(self, student_message: str) -> str:
        """
        Process student message and return coach response.

        Args:
            student_message: What the student just said/typed

        Returns:
            The coach's response string
        """
        # Track the student's work
        self.state.student_work_history.append(student_message)

        # Increment attempt count when student makes a real attempt
        # (not just asking questions or saying "hi")
        if self._is_substantive_attempt(student_message):
            if self.state.attempt_count == 0:
                self.state.attempt_count = 1
            elif not self._detect_answer_claim(student_message):
                # Only increment if not an answer claim (those go to validation)
                pass

        # After validation, increment attempt if answer was wrong
        if self.state.current_stage == TutoringStage.STAGE_2_VALIDATION:
            if self.state.answer_validated and not self.state.problem_solved:
                self.state.attempt_count += 1
                self.state.answer_validated = False
                self.state.student_claimed_answer = False

        # Determine the appropriate stage
        self._determine_stage(student_message)

        # Update system prompt with current state
        await self._update_system_prompt()

        # Build the query with context
        query = self._build_query(student_message)

        # Send to Claude
        await self.client.query(query)

        # Collect response
        response_text = ""
        async for message in self.client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
            elif isinstance(message, ResultMessage):
                break

        # Mark validation as complete if we were in Stage 2
        if self.state.current_stage == TutoringStage.STAGE_2_VALIDATION:
            self.state.answer_validated = True

        return response_text.strip()

    def _is_substantive_attempt(self, message: str) -> bool:
        """Check if message is a substantive problem-solving attempt."""
        msg_lower = message.lower().strip()

        # Not substantive: greetings, simple questions
        non_substantive = [
            "hi", "hello", "hey", "help", "?", "what", "how", "why",
            "i don't know", "idk", "i'm stuck", "confused"
        ]

        if msg_lower in non_substantive or len(msg_lower) < 3:
            return False

        # Substantive: contains math operations, numbers, or problem-solving language
        substantive_indicators = [
            "+", "-", "*", "/", "=", "x", "y",
            "first", "then", "so", "because", "if",
            "multiply", "divide", "add", "subtract",
            "equation", "solve", "variable"
        ]

        return any(ind in msg_lower for ind in substantive_indicators)

    def _build_query(self, student_message: str) -> str:
        """Build the query to send to Claude."""
        return f"""Current Stage: {self.state.current_stage.value} ({self._get_stage_name()})
Attempt #{self.state.attempt_count}
Reveal mode: {self.state.reveal_now}
Student claimed answer: {self.state.student_claimed_answer}

Student said: "{student_message}"

Respond as the Algebra 1 coach following the stage instructions exactly. Keep it brief."""

    async def close(self):
        """Close the client connection."""
        if self.client:
            await self.client.disconnect()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# ============================================================================
# CLI Interface
# ============================================================================

async def interactive_session():
    """Run an interactive tutoring session."""
    print("\n" + "="*60)
    print("  Algebra 1 Coach - Interactive Session")
    print("="*60)
    print("\nCommands:")
    print("  /problem <text>  - Set a new problem")
    print("  /pdf <path>      - Load problems from PDF")
    print("  /reveal          - Force reveal the answer")
    print("  /correct         - Mark answer as correct")
    print("  /status          - Show session state")
    print("  /reset           - Reset the session")
    print("  /quit            - Exit")
    print("="*60 + "\n")

    async with Algebra1Coach() as coach:
        # Try to load from PDF if it exists
        pdf_path = Path("regents_test.pdf")
        if pdf_path.exists() and PDF_SUPPORT:
            try:
                full_text = get_full_pdf_text(str(pdf_path))
                print(f"PDF loaded: {pdf_path}")
                print(f"Preview: {full_text[:200]}...")
                coach.set_problem(full_text, problem_id="regents_pdf")
            except Exception as e:
                print(f"Could not load PDF: {e}")
                # Fall back to sample problem
                sample = "Solve for x: 3x + 7 = 22"
                coach.set_problem(sample, problem_id="sample_1")
        else:
            sample = "Solve for x: 3x + 7 = 22"
            coach.set_problem(sample, problem_id="sample_1")
            print(f"Sample problem loaded: {sample}")

        print(f"\nProblem:\n{coach.state.problem[:500]}")

        # Get initial Stage 0 response
        initial = await coach.respond("I'm ready to start")
        print(f"\nCoach: {initial}")

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    cmd_parts = user_input.split(maxsplit=1)
                    cmd = cmd_parts[0].lower()
                    arg = cmd_parts[1] if len(cmd_parts) > 1 else ""

                    if cmd == "/quit":
                        print("\nGreat work today! Keep practicing!")
                        break

                    elif cmd == "/problem":
                        if arg:
                            coach.set_problem(arg)
                            print(f"\nNew problem set: {arg}")
                            initial = await coach.respond("I'm ready to start")
                            print(f"\nCoach: {initial}")
                        else:
                            print("Usage: /problem <problem text>")
                        continue

                    elif cmd == "/pdf":
                        if not PDF_SUPPORT:
                            print("PDF support not available. Install: pip install pymupdf")
                            continue
                        if arg:
                            try:
                                full_text = get_full_pdf_text(arg)
                                coach.set_problem(full_text, problem_id=arg)
                                print(f"\nPDF loaded: {arg}")
                                print(f"Preview: {full_text[:300]}...")
                                initial = await coach.respond("I'm ready to start")
                                print(f"\nCoach: {initial}")
                            except Exception as e:
                                print(f"Error loading PDF: {e}")
                        else:
                            print("Usage: /pdf <path to pdf>")
                        continue

                    elif cmd == "/reveal":
                        coach.force_reveal()
                        response = await coach.respond("Please show me the answer")
                        print(f"\nCoach: {response}")
                        continue

                    elif cmd == "/correct":
                        coach.mark_correct()
                        print("\nMarked as correct!")
                        continue

                    elif cmd == "/status":
                        print(f"\nSession Status:")
                        print(f"  Stage: {coach.state.current_stage.value} ({coach._get_stage_name()})")
                        print(f"  Attempts: {coach.state.attempt_count}")
                        print(f"  Claimed answer: {coach.state.student_claimed_answer}")
                        print(f"  Solved: {coach.state.problem_solved}")
                        print(f"  Reveal mode: {coach.state.reveal_now}")
                        continue

                    elif cmd == "/reset":
                        coach.set_problem(coach.state.problem, problem_id=coach.state.problem_id)
                        print("\nSession reset.")
                        initial = await coach.respond("I'm ready to start")
                        print(f"\nCoach: {initial}")
                        continue

                    else:
                        print(f"Unknown command: {cmd}")
                        continue

                # Regular student message
                response = await coach.respond(user_input)
                print(f"\nCoach: {response}")

            except KeyboardInterrupt:
                print("\n\nSession ended. Keep up the great work!")
                break
            except Exception as e:
                print(f"\nError: {e}")


# ============================================================================
# Programmatic API
# ============================================================================

async def process_turn(
    problem: str,
    student_message: str,
    attempt_count: int = 0,
    reveal_now: bool = False,
    student_age_band: str = "middle school",
    confidence_signal: Optional[str] = None,
    problem_id: Optional[str] = None
) -> str:
    """
    Process a single tutoring turn - for API/integration use.

    Args:
        problem: The full problem text (or PDF content)
        student_message: What the student just said/typed
        attempt_count: Number of attempts (starts at 0)
        reveal_now: If True, reveal the final answer
        student_age_band: Student's age band
        confidence_signal: "low", "med", or "high"
        problem_id: Optional problem identifier

    Returns:
        The coach's response string
    """
    async with Algebra1Coach() as coach:
        coach.set_problem(problem, problem_id)
        coach.state.attempt_count = attempt_count
        coach.state.reveal_now = reveal_now

        confidence = None
        if confidence_signal:
            confidence = ConfidenceLevel(confidence_signal)
        coach.set_student_profile(student_age_band, confidence)

        response = await coach.respond(student_message)
        return response


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("\nStarting Algebra 1 Coach...")
    print("Ensure ANTHROPIC_API_KEY is set.\n")

    try:
        asyncio.run(interactive_session())
    except Exception as e:
        print(f"\nError: {e}")
        print("\nSetup:")
        print("1. pip install claude-agent-sdk pymupdf")
        print("2. export ANTHROPIC_API_KEY=your-key")
