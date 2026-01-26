"""
Algebra 1 Coach - Streamlit UI
A basic web interface for the tutoring application.
"""

import streamlit as st
import asyncio
import re
from typing import List, Optional
from dataclasses import dataclass

# Import LlamaParse-based parser for text extraction
try:
    from pdf_parser import parse_pdf_to_questions, ParsedQuestion as LlamaQuestion, LLAMAPARSE_AVAILABLE
except ImportError:
    LLAMAPARSE_AVAILABLE = False

from main import Algebra1Coach, process_turn


@dataclass
class Question:
    """Represents a single question from the exam."""
    number: int
    text: str
    choices: List[str]
    correct_answer: int = 1  # 1-indexed (1, 2, 3, or 4)
    has_graph: bool = False
    page: int = 1


def parse_questions_from_uploaded_pdf(pdf_bytes: bytes, filename: str = "", use_llamaparse: bool = True) -> List[Question]:
    """Parse questions from an uploaded PDF file.

    Args:
        pdf_bytes: The PDF file bytes
        filename: Original filename
        use_llamaparse: Whether to use LlamaParse for automatic extraction
    """
    if not LLAMAPARSE_AVAILABLE:
        return []

    if not use_llamaparse:
        return []

    try:
        llama_questions, markdown = parse_pdf_to_questions(
            pdf_bytes=pdf_bytes,
            filename=filename,
            use_claude=True
        )

        if not llama_questions:
            return []

        questions = []
        for lq in llama_questions:
            questions.append(Question(
                number=lq.number,
                text=lq.text,
                choices=lq.choices if lq.choices else ["This appears to be a free-response question."],
                correct_answer=lq.correct_answer,
                has_graph=lq.has_graph,
                page=lq.page if lq.page > 0 else 1,
            ))

        return questions
    except Exception as e:
        print(f"Exception during parsing: {e}")
        import traceback
        traceback.print_exc()
        return []


def init_session_state():
    """Initialize Streamlit session state variables."""
    if "questions" not in st.session_state:
        st.session_state.questions = []
    if "current_question_idx" not in st.session_state:
        st.session_state.current_question_idx = 0
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "attempt_count" not in st.session_state:
        st.session_state.attempt_count = 0
    if "coach_initialized" not in st.session_state:
        st.session_state.coach_initialized = False
    if "correct_questions" not in st.session_state:
        st.session_state.correct_questions = set()  # Track indices of correctly answered questions
    if "answer_is_correct" not in st.session_state:
        st.session_state.answer_is_correct = False  # Track if current answer is correct
    if "awaiting_explanation" not in st.session_state:
        st.session_state.awaiting_explanation = False  # Track if waiting for explanation


def get_selected_answer_number(selected_choice: str) -> int:
    """Extract the answer number (1-4) from the selected choice string."""
    # Choice format is like "(1) some text" or "(2) some text"
    if selected_choice and selected_choice.startswith("("):
        try:
            return int(selected_choice[1])
        except (ValueError, IndexError):
            pass
    return 0


def is_correct_response(response: str) -> bool:
    """Check if the coach's response indicates the answer is correct."""
    response_lower = response.lower()

    # Strong phrases that DEFINITELY indicate correct answer - check these FIRST
    strong_correct_indicators = [
        "that's correct", "is correct", "you're correct",
        "that's the right answer", "the right answer",
        "you got it", "you nailed it", "exactly right",
        "you solved it", "problem solved", "well done",
        "great work", "perfect", "nice work", "good job"
    ]

    # If coach confirms correct, mark as correct (even if also asking for explanation)
    for phrase in strong_correct_indicators:
        if phrase in response_lower:
            return True

    # Phrases that indicate incorrect answer
    incorrect_indicators = [
        "not quite", "not correct", "incorrect", "try again", "not right",
        "that's not", "wrong", "close but", "almost", "not exactly",
        "let's think", "think about", "check your", "look again",
        "careful", "watch out", "hmm", "are you sure"
    ]

    # Check for incorrect indicators
    for phrase in incorrect_indicators:
        if phrase in response_lower:
            return False

    return False


def run_async(coro):
    """Helper to run async functions in Streamlit."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def get_coach_response(problem: str, message: str, attempt: int, correct_answer: str = "",
                       answer_is_correct: bool = False, awaiting_explanation: bool = False) -> dict:
    """Get response from the tutoring coach. Returns dict with response and state."""
    return run_async(process_turn(
        problem=problem,
        student_message=message,
        attempt_count=attempt,
        correct_answer=correct_answer,
        answer_is_correct=answer_is_correct,
        awaiting_explanation=awaiting_explanation
    ))


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Algebra 1 Coach",
        page_icon="📐",
        layout="wide"
    )

    init_session_state()

    # Header
    st.title("📐 Algebra 1 Coach")
    st.markdown("*Your algebra tutor!*")

    # Sidebar for navigation
    with st.sidebar:
        st.header("📚 Questions")

        # Upload PDF
        st.subheader("Upload Exam PDF")
        uploaded_file = st.file_uploader(
            "Upload a PDF exam",
            type=["pdf"],
            help="Upload any math exam PDF and we'll automatically extract the questions!"
        )

        if uploaded_file is not None:
            # Check file size (1.5 MB limit)
            file_size_mb = uploaded_file.size / (1024 * 1024)
            if file_size_mb > 1.5:
                st.error(f"File too large ({file_size_mb:.1f} MB). Please upload a PDF under 1.5 MB.")
            else:
                use_ai_parsing = st.checkbox(
                    "Use AI parsing (LlamaParse)",
                    value=True,
                    help="Uses LlamaParse + Claude to automatically detect questions. Requires API keys."
                )

                if st.button("Parse PDF", type="primary"):
                    with st.spinner("Parsing PDF... This may take a moment for AI parsing."):
                        pdf_bytes = uploaded_file.read()
                        st.session_state.questions = parse_questions_from_uploaded_pdf(
                            pdf_bytes,
                            filename=uploaded_file.name,
                            use_llamaparse=use_ai_parsing
                        )
                        st.session_state.current_question_idx = 0
                        st.session_state.chat_history = []
                        st.session_state.attempt_count = 0
                        st.session_state.correct_questions = set()
                        st.session_state.answer_is_correct = False
                        st.session_state.awaiting_explanation = False

                    if st.session_state.questions:
                        st.success(f"Extracted {len(st.session_state.questions)} questions!")
                    else:
                        st.error("Could not extract questions from this PDF.")
                    st.rerun()

        st.divider()

        if st.session_state.questions:
            st.success(f"Loaded {len(st.session_state.questions)} questions!")

        # Question selector with progress
        if st.session_state.questions:
            correct_count = len(st.session_state.correct_questions)
            total_count = len(st.session_state.questions)
            st.subheader(f"Questions ({correct_count}/{total_count} ✓)")

            for i, q in enumerate(st.session_state.questions):
                is_correct = i in st.session_state.correct_questions
                is_current = i == st.session_state.current_question_idx

                # Use columns: green indicator + button
                col1, col2 = st.columns([1, 6])

                with col1:
                    if is_correct:
                        st.markdown(f"""
                        <div style="background-color: #28a745; color: white;
                                    border-radius: 50%; width: 24px; height: 24px;
                                    display: flex; align-items: center; justify-content: center;
                                    font-size: 14px; margin-top: 6px;">✓</div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background-color: transparent; width: 24px; height: 24px;
                                    margin-top: 6px;"></div>
                        """, unsafe_allow_html=True)

                with col2:
                    btn_type = "primary" if is_current else "secondary"
                    if st.button(f"Question {q.number}", key=f"q_btn_{i}", use_container_width=True, type=btn_type):
                        st.session_state.current_question_idx = i
                        st.session_state.chat_history = []
                        st.session_state.attempt_count = 0
                        st.session_state.answer_is_correct = False
                        st.session_state.awaiting_explanation = False
                        st.rerun()

                # Add green background to the row for correct questions
                if is_correct:
                    st.markdown("""
                    <style>
                        div[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(div[style*="28a745"]) {
                            background-color: #d4edda;
                            border-radius: 8px;
                            padding: 4px;
                            margin: 2px 0;
                            border: 1px solid #28a745;
                        }
                    </style>
                    """, unsafe_allow_html=True)

    # Main content area
    if not st.session_state.questions:
        st.info("👈 Upload a PDF exam in the sidebar to get started!")

        # Show sample question
        st.subheader("Or try a sample question:")
        sample_problem = "Solve for x: 3x + 7 = 22"
        st.markdown(f"**{sample_problem}**")

        col1, col2 = st.columns([3, 1])
        with col1:
            sample_response = st.text_input("Your response:", key="sample_input",
                                           placeholder="Type your answer or thinking here...")
        with col2:
            if st.button("Ask Coach", key="sample_btn"):
                if sample_response:
                    with st.spinner("Coach is thinking..."):
                        result = get_coach_response(sample_problem, sample_response, 0)
                        response = result["response"]
                    st.markdown(f"**Coach:** {response}")
    else:
        # Display current question
        current_q = st.session_state.questions[st.session_state.current_question_idx]

        # Question display area
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader(f"Question {current_q.number}")

            # Question text on white background with black text
            st.markdown(f"""
            <div style="background-color: #ffffff; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #e0e0e0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <p style="font-size: 16px; line-height: 1.6; color: #000000;">{current_q.text.replace(chr(10), '<br>')}</p>
            </div>
            """, unsafe_allow_html=True)

            # Answer choices
            st.markdown("**Answer Choices:**")
            selected_choice = st.radio(
                "Select your answer:",
                current_q.choices,
                key=f"choices_{current_q.number}",
                label_visibility="collapsed"
            )

            st.divider()

            # Response input area
            st.markdown("**💬 Chat with your Coach:**")

            user_input = st.text_area(
                "Type your response, question, or reasoning:",
                key=f"user_input_{current_q.number}",
                placeholder="Tell me what you're thinking, ask a question, or explain your answer choice...",
                height=100
            )

            col_a, col_b, col_c = st.columns([1, 1, 2])
            with col_a:
                send_btn = st.button("Send to Coach", type="primary", use_container_width=True)
            with col_b:
                submit_answer = st.button("Submit Answer", use_container_width=True)
            with col_c:
                reveal_btn = st.button("Reveal Answer", use_container_width=True)

            # Handle button clicks
            # Get the correct answer text for the coach
            correct_answer_text = current_q.choices[current_q.correct_answer - 1] if current_q.correct_answer > 0 else ""

            if send_btn and user_input:
                with st.spinner("Coach is thinking..."):
                    # Build problem text
                    problem_text = f"{current_q.text}\n\nChoices:\n" + "\n".join(current_q.choices)
                    result = get_coach_response(
                        problem_text,
                        user_input,
                        st.session_state.attempt_count,
                        correct_answer=correct_answer_text,
                        answer_is_correct=st.session_state.answer_is_correct,
                        awaiting_explanation=st.session_state.awaiting_explanation
                    )
                    response = result["response"]
                    st.session_state.chat_history.append(("You", user_input))
                    st.session_state.chat_history.append(("Coach", response))
                    st.session_state.attempt_count += 1

                    # Check if coach confirmed correct answer
                    if is_correct_response(response):
                        # If answer just became correct, we're now awaiting explanation
                        if not st.session_state.answer_is_correct:
                            st.session_state.answer_is_correct = True
                            st.session_state.awaiting_explanation = True
                        # If already awaiting explanation and coach says it's correct/complete
                        elif st.session_state.awaiting_explanation:
                            # Check for completion indicators
                            completion_indicators = ["perfect", "excellent", "you nailed it", "great job",
                                                    "well done", "you really understand", "nice work"]
                            response_lower = response.lower()
                            if any(ind in response_lower for ind in completion_indicators):
                                st.session_state.correct_questions.add(st.session_state.current_question_idx)
                                st.session_state.awaiting_explanation = False
                st.rerun()

            if submit_answer:
                with st.spinner("Coach is checking your answer..."):
                    problem_text = f"{current_q.text}\n\nChoices:\n" + "\n".join(current_q.choices)
                    message = f"My answer is {selected_choice}"
                    result = get_coach_response(
                        problem_text,
                        message,
                        st.session_state.attempt_count,
                        correct_answer=correct_answer_text,
                        answer_is_correct=st.session_state.answer_is_correct,
                        awaiting_explanation=st.session_state.awaiting_explanation
                    )
                    response = result["response"]
                    st.session_state.chat_history.append(("You", message))
                    st.session_state.chat_history.append(("Coach", response))
                    st.session_state.attempt_count += 1

                    # Check if coach confirmed correct answer - now awaiting explanation
                    if is_correct_response(response):
                        st.session_state.answer_is_correct = True
                        st.session_state.awaiting_explanation = True
                st.rerun()

            if reveal_btn:
                with st.spinner("Getting the answer..."):
                    problem_text = f"{current_q.text}\n\nChoices:\n" + "\n".join(current_q.choices)
                    result = run_async(process_turn(
                        problem=problem_text,
                        student_message="Please show me the answer",
                        attempt_count=5,
                        reveal_now=True,
                        correct_answer=correct_answer_text
                    ))
                    response = result["response"]
                    st.session_state.chat_history.append(("You", "Please reveal the answer"))
                    st.session_state.chat_history.append(("Coach", response))
                st.rerun()

        with col2:
            st.subheader("💬 Chat History")

            # Display chat history
            chat_container = st.container(height=500)
            with chat_container:
                if not st.session_state.chat_history:
                    st.markdown("*Start by typing a response or question below!*")

                    # Auto-start with coach greeting
                    if st.button("Start with Coach", key="start_btn"):
                        with st.spinner("Coach is ready..."):
                            problem_text = f"{current_q.text}\n\nChoices:\n" + "\n".join(current_q.choices)
                            correct_ans = current_q.choices[current_q.correct_answer - 1] if current_q.correct_answer > 0 else ""
                            result = get_coach_response(problem_text, "I'm ready to start", 0, correct_answer=correct_ans)
                            response = result["response"]
                            st.session_state.chat_history.append(("Coach", response))
                        st.rerun()
                else:
                    for sender, message in st.session_state.chat_history:
                        if sender == "You":
                            st.markdown(f"""
                            <div style="background-color: #e3f2fd; padding: 10px; border-radius: 10px; margin: 5px 0; color: #1a1a1a;">
                                <strong>You:</strong> {message}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="background-color: #f5f5f5; padding: 10px; border-radius: 10px; margin: 5px 0; color: #1a1a1a;">
                                <strong>🎓 Coach:</strong> {message}
                            </div>
                            """, unsafe_allow_html=True)

            # Progress info
            st.divider()
            st.markdown(f"**Attempts:** {st.session_state.attempt_count}")

            # Navigation buttons
            st.divider()
            nav_col1, nav_col2 = st.columns(2)
            with nav_col1:
                if st.session_state.current_question_idx > 0:
                    if st.button("← Previous", use_container_width=True):
                        st.session_state.current_question_idx -= 1
                        st.session_state.chat_history = []
                        st.session_state.attempt_count = 0
                        st.session_state.answer_is_correct = False
                        st.session_state.awaiting_explanation = False
                        st.rerun()
            with nav_col2:
                if st.session_state.current_question_idx < len(st.session_state.questions) - 1:
                    if st.button("Next →", use_container_width=True):
                        st.session_state.current_question_idx += 1
                        st.session_state.chat_history = []
                        st.session_state.attempt_count = 0
                        st.session_state.answer_is_correct = False
                        st.session_state.awaiting_explanation = False
                        st.rerun()


if __name__ == "__main__":
    main()
