"""
Algebra 1 Coach - Educational Tutor

A middle-school-friendly Algebra 1 tutoring agent that helps students build
strong problem-solving habits through a 6-stage coaching flow.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

# Try to import Streamlit for secrets (when running in Streamlit Cloud)
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# Anthropic SDK
from anthropic import Anthropic

# PDF parsing
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


def get_api_key():
    """Get API key from Streamlit secrets or environment variable."""
    # Try Streamlit secrets first (for Streamlit Cloud deployment)
    if STREAMLIT_AVAILABLE:
        try:
            return st.secrets["ANTHROPIC_API_KEY"]
        except:
            pass
    # Fall back to environment variable
    return os.environ.get("ANTHROPIC_API_KEY")


class TutoringStage(Enum):
    """Stages of the tutoring flow (0-5)."""
    STAGE_0_SETUP = 0
    STAGE_1_FIRST_ATTEMPT = 1
    STAGE_2_VALIDATION = 2
    STAGE_3_DIAGNOSE = 3
    STAGE_4_FINAL_HINT = 4
    STAGE_5_REVEAL = 5


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
    student_claimed_answer: bool = False
    answer_validated: bool = False
    problem_solved: bool = False
    student_work_history: List[str] = field(default_factory=list)


class Algebra1Coach:
    """Middle-school-friendly Algebra 1 tutoring agent."""

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
        api_key = get_api_key()
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found. Set it in Streamlit secrets or environment.")
        self.client = Anthropic(api_key=api_key)
        self.state = TutoringState()

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

    def force_reveal(self):
        """Force the coach to reveal the answer."""
        self.state.reveal_now = True
        self.state.current_stage = TutoringStage.STAGE_5_REVEAL

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
        if self.state.reveal_now or self.state.attempt_count >= 5:
            self.state.current_stage = TutoringStage.STAGE_5_REVEAL
            return

        if self.state.problem_solved:
            self.state.current_stage = TutoringStage.STAGE_5_REVEAL
            return

        if self.state.attempt_count == 0:
            self.state.current_stage = TutoringStage.STAGE_0_SETUP
            return

        if self._detect_answer_claim(student_message) and not self.state.answer_validated:
            self.state.student_claimed_answer = True
            self.state.current_stage = TutoringStage.STAGE_2_VALIDATION
            return

        if self.state.attempt_count in [1, 2]:
            self.state.current_stage = TutoringStage.STAGE_1_FIRST_ATTEMPT
            return

        if self.state.attempt_count in [3, 4]:
            self.state.current_stage = TutoringStage.STAGE_3_DIAGNOSE
            return

        if self.state.attempt_count == 5:
            self.state.current_stage = TutoringStage.STAGE_4_FINAL_HINT
            return

    def respond(self, student_message: str) -> str:
        """Process student message and return coach response."""
        self.state.student_work_history.append(student_message)

        if self._is_substantive_attempt(student_message):
            if self.state.attempt_count == 0:
                self.state.attempt_count = 1

        if self.state.current_stage == TutoringStage.STAGE_2_VALIDATION:
            if self.state.answer_validated and not self.state.problem_solved:
                self.state.attempt_count += 1
                self.state.answer_validated = False
                self.state.student_claimed_answer = False

        self._determine_stage(student_message)

        query = f"""Current Stage: {self.state.current_stage.value} ({self._get_stage_name()})
Attempt #{self.state.attempt_count}
Reveal mode: {self.state.reveal_now}
Student claimed answer: {self.state.student_claimed_answer}

Student said: "{student_message}"

Respond as the Algebra 1 coach following the stage instructions exactly. Keep it brief."""

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=self._build_system_prompt(),
            messages=[{"role": "user", "content": query}]
        )

        response_text = response.content[0].text

        if self.state.current_stage == TutoringStage.STAGE_2_VALIDATION:
            self.state.answer_validated = True

        return response_text.strip()

    def _is_substantive_attempt(self, message: str) -> bool:
        """Check if message is a substantive problem-solving attempt."""
        msg_lower = message.lower().strip()
        non_substantive = [
            "hi", "hello", "hey", "help", "?", "what", "how", "why",
            "i don't know", "idk", "i'm stuck", "confused"
        ]

        if msg_lower in non_substantive or len(msg_lower) < 3:
            return False

        substantive_indicators = [
            "+", "-", "*", "/", "=", "x", "y",
            "first", "then", "so", "because", "if",
            "multiply", "divide", "add", "subtract",
            "equation", "solve", "variable"
        ]

        return any(ind in msg_lower for ind in substantive_indicators)


async def process_turn(
    problem: str,
    student_message: str,
    attempt_count: int = 0,
    reveal_now: bool = False,
    student_age_band: str = "middle school",
    confidence_signal: Optional[str] = None,
    problem_id: Optional[str] = None
) -> str:
    """Process a single tutoring turn."""
    coach = Algebra1Coach()
    coach.set_problem(problem, problem_id)
    coach.state.attempt_count = attempt_count
    coach.state.reveal_now = reveal_now

    if confidence_signal:
        coach.state.confidence_signal = ConfidenceLevel(confidence_signal)

    response = coach.respond(student_message)
    return response


if __name__ == "__main__":
    print("Algebra 1 Coach - Run with: streamlit run ui.py")
