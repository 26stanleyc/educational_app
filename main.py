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
    correct_answer: str = ""  # The correct answer for verification
    attempt_count: int = 0
    reveal_now: bool = False
    student_age_band: str = "middle school"
    confidence_signal: Optional[ConfidenceLevel] = None
    current_stage: TutoringStage = TutoringStage.STAGE_0_SETUP
    problem_id: Optional[str] = None
    student_claimed_answer: bool = False
    answer_validated: bool = False
    problem_solved: bool = False
    answer_is_correct: bool = False  # Track if student's answer was correct
    awaiting_explanation: bool = False  # Track if we're waiting for explanation
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

## Answer Key (for verification only - don't reveal unless reveal_now=true)
Correct answer: {correct_answer}

## Session State
- Attempt count: {attempt_count}
- Current stage: Stage {stage_num} ({stage_name})
- Reveal answer now: {reveal_now}
- Student claimed answer: {claimed_answer}
- Answer is correct: {answer_is_correct}
- Awaiting explanation: {awaiting_explanation}
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
**Goal:** Confirm if correct, then make sure they understand why.

**If awaiting_explanation=false (student just gave an answer):**
1. First, evaluate if their answer is mathematically correct
2. If their answer IS CORRECT:
   - Start with clear confirmation: "That's correct!" or "You got it!" or "Yes, that's right!"
   - Then ask for their reasoning: "Now walk me through how you figured that out?"
3. If their answer is WRONG:
   - Don't say "correct" or confirm it
   - Give a gentle hint: "Hmm, not quite. Let's think about this..." or "Close! But check your work on..."
   - Guide them toward the right answer

**If awaiting_explanation=true (student is explaining their correct answer):**
1. Evaluate if their explanation shows understanding of the math
2. If their explanation IS VALID (shows they understand the concept):
   - Congratulate them enthusiastically: "Perfect! You nailed it!" or "Excellent work! You really understand this!"
   - The problem is COMPLETE - do NOT ask for more explanation
   - You can briefly reinforce what they did right
3. If their explanation is WRONG or incomplete:
   - Gently correct the misconception: "Hmm, not quite the right reasoning..."
   - Ask them to think about it differently: "The answer is right, but can you explain WHY that works?"
   - Keep asking until they show understanding

**Don't:** Ask for explanation without first confirming if they're right or wrong.
**Don't:** Keep asking for more explanation after they've correctly explained their reasoning.

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

### STAGE 4 — Extended Help (attempt_count >= 5)
**Goal:** Keep helping with increasingly clear hints, but NEVER reveal the answer.
**Do:**
- Give clear, structured hints that guide them toward the solution
- Break down the problem into smaller steps
- Point out exactly where they might be going wrong
Example: "Okay, here's a big hint: after you simplify the left side, you should have 12x² - 6. Now what can you do with both sides?"
**Don't:** NEVER reveal the answer unless reveal_now=true. Keep coaching no matter how many attempts.

---

### STAGE 5 — Showing the Answer (ONLY when reveal_now=true)
**Goal:** Make sure they learn from it, not just copy the answer.
**IMPORTANT:** Only enter this stage if reveal_now=true. Never reveal based on attempt count alone.
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
            correct_answer=self.state.correct_answer or "Not provided",
            attempt_count=self.state.attempt_count,
            stage_num=self.state.current_stage.value,
            stage_name=self._get_stage_name(),
            reveal_now=self.state.reveal_now,
            claimed_answer=self.state.student_claimed_answer,
            answer_is_correct=self.state.answer_is_correct,
            awaiting_explanation=self.state.awaiting_explanation,
            problem_solved=self.state.problem_solved,
            confidence=confidence_str
        )

    def set_problem(self, problem: str, problem_id: Optional[str] = None, correct_answer: str = ""):
        """Set a new problem and reset state."""
        self.state.problem = problem
        self.state.correct_answer = correct_answer
        self.state.problem_id = problem_id
        self.state.attempt_count = 0
        self.state.reveal_now = False
        self.state.current_stage = TutoringStage.STAGE_0_SETUP
        self.state.student_claimed_answer = False
        self.state.answer_validated = False
        self.state.problem_solved = False
        self.state.answer_is_correct = False
        self.state.awaiting_explanation = False
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
        # Only reveal if explicitly requested - never based on attempt count
        if self.state.reveal_now:
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

        # 5+ attempts: keep coaching with extended help, never auto-reveal
        if self.state.attempt_count >= 5:
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
            model="claude-3-haiku-20240307",
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
    problem_id: Optional[str] = None,
    correct_answer: str = "",
    answer_is_correct: bool = False,
    awaiting_explanation: bool = False
) -> dict:
    """Process a single tutoring turn. Returns dict with response and state."""
    coach = Algebra1Coach()
    coach.set_problem(problem, problem_id, correct_answer=correct_answer)
    coach.state.attempt_count = attempt_count
    coach.state.reveal_now = reveal_now
    coach.state.answer_is_correct = answer_is_correct
    coach.state.awaiting_explanation = awaiting_explanation

    if confidence_signal:
        coach.state.confidence_signal = ConfidenceLevel(confidence_signal)

    response = coach.respond(student_message)

    return {
        "response": response,
        "answer_is_correct": coach.state.answer_is_correct,
        "awaiting_explanation": coach.state.awaiting_explanation,
        "problem_solved": coach.state.problem_solved
    }


if __name__ == "__main__":
    print("Algebra 1 Coach - Run with: streamlit run ui.py")
