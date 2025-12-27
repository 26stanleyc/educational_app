"""
Algebra 1 Coach - Streamlit UI
A basic web interface for the tutoring application.
"""

import streamlit as st
import asyncio
import re
from typing import List, Dict, Optional
from dataclasses import dataclass

# Import from main module
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

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
    image_bytes: Optional[bytes] = None  # PNG image data for visual questions


def extract_page_image(doc, page_num: int, crop_rect: Optional[List[float]] = None, zoom: float = 2.0) -> Optional[bytes]:
    """
    Extract a portion of a PDF page as a PNG image.

    Args:
        doc: PyMuPDF document
        page_num: 1-indexed page number
        crop_rect: Optional [x0, y0, x1, y1] as percentages (0-1) of page dimensions
        zoom: Resolution multiplier
    """
    try:
        page = doc[page_num - 1]  # 0-indexed
        page_rect = page.rect

        # Calculate clip rectangle if crop coordinates provided
        clip = None
        if crop_rect:
            x0 = page_rect.width * crop_rect[0]
            y0 = page_rect.height * crop_rect[1]
            x1 = page_rect.width * crop_rect[2]
            y1 = page_rect.height * crop_rect[3]
            clip = fitz.Rect(x0, y0, x1, y1)

        # Create a matrix for higher resolution
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=clip)
        return pix.tobytes("png")
    except Exception as e:
        print(f"Error extracting page image: {e}")
        return None


def parse_questions_from_uploaded_pdf(pdf_bytes: bytes, filename: str = "") -> List[Question]:
    """Parse questions from an uploaded PDF file."""
    if not PDF_SUPPORT:
        return []

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Use hardcoded data for regents_test.pdf
    if "regents_test.pdf" in filename.lower():
        questions = parse_regents_questions(doc)
        doc.close()
        return questions

    # For other PDFs: show each page with its image
    questions = []
    for page_num in range(len(doc)):
        image_bytes = extract_page_image(doc, page_num + 1)
        questions.append(Question(
            number=page_num + 1,
            text=f"Work through the problems on this page with your coach.",
            choices=["Ask me about any problem you see on this page!"],
            has_graph=True,
            page=page_num + 1,
            image_bytes=image_bytes
        ))

    doc.close()
    return questions


def parse_regents_questions(doc) -> List[Question]:
    """Parse the specific Regents exam with hardcoded accurate data."""
    questions_data = [
        {
            "number": 1,
            "text": """A part of Jennifer's work to solve the equation 2(6x² − 3) = 11x² − x is shown below.

Given: 2(6x² − 3) = 11x² − x
Step 1: 12x² − 6 = 11x² − x

Which property justifies her first step?""",
            "choices": [
                "(1) identity property of multiplication",
                "(2) multiplication property of equality",
                "(3) commutative property of multiplication",
                "(4) distributive property of multiplication over subtraction"
            ],
            "correct_answer": 4,
            "page": 2
        },
        {
            "number": 2,
            "text": "Which value of x results in equal outputs for j(x) = 3x − 2 and b(x) = |x + 2|?",
            "choices": [
                "(1) −2",
                "(2) 2",
                "(3) 2/3",
                "(4) 4"
            ],
            "correct_answer": 2,
            "page": 2
        },
        {
            "number": 3,
            "text": "The expression 49x² − 36 is equivalent to",
            "choices": [
                "(1) (7x − 6)²",
                "(2) (24.5x − 18)²",
                "(3) (7x − 6)(7x + 6)",
                "(4) (24.5x − 18)(24.5x + 18)"
            ],
            "correct_answer": 3,
            "page": 2
        },
        {
            "number": 4,
            "text": "If f(x) = ½x² − (¼x + 3), what is the value of f(8)?",
            "choices": [
                "(1) 11",
                "(2) 17",
                "(3) 27",
                "(4) 33"
            ],
            "correct_answer": 3,
            "page": 3
        },
        {
            "number": 5,
            "text": """The graph below models the height of a remote-control helicopter over 20 seconds during flight.

Over which interval does the helicopter have the slowest average rate of change?""",
            "choices": [
                "(1) 0 to 5 seconds",
                "(2) 5 to 10 seconds",
                "(3) 10 to 15 seconds",
                "(4) 15 to 20 seconds"
            ],
            "correct_answer": 3,
            "page": 3,
            "has_graph": True,
            "graph_rect": [0.1, 0.15, 0.9, 0.55]
        },
        {
            "number": 6,
            "text": """In the functions f(x) = kx² and g(x) = |kx|, k is a positive integer.
If k is replaced by ½, which statement about these new functions is true?""",
            "choices": [
                "(1) The graphs of both f(x) and g(x) become wider.",
                "(2) The graph of f(x) becomes narrower and the graph of g(x) shifts left.",
                "(3) The graphs of both f(x) and g(x) shift vertically.",
                "(4) The graph of f(x) shifts left and the graph of g(x) becomes wider."
            ],
            "correct_answer": 1,
            "page": 3
        },
        {
            "number": 7,
            "text": """Wenona sketched the polynomial P(x) as shown on the axes below.

Which equation could represent P(x)?""",
            "choices": [
                "(1) P(x) = (x + 1)(x − 2)²",
                "(2) P(x) = (x − 1)(x + 2)²",
                "(3) P(x) = (x + 1)(x − 2)",
                "(4) P(x) = (x − 1)(x + 2)"
            ],
            "correct_answer": 1,
            "page": 4,
            "has_graph": True,
            "graph_rect": [0.1, 0.1, 0.9, 0.5]
        },
        {
            "number": 8,
            "text": "Which situation does not describe a causal relationship?",
            "choices": [
                "(1) The higher the volume on a radio, the louder the sound will be.",
                "(2) The faster a student types a research paper, the more pages the research paper will have.",
                "(3) The shorter the time a car remains running, the less gasoline it will use.",
                "(4) The slower the pace of a runner, the longer it will take the runner to finish the race."
            ],
            "correct_answer": 2,
            "page": 4
        },
        {
            "number": 9,
            "text": """A plumber has a set fee for a house call and charges by the hour for repairs. The total cost of her services can be modeled by c(t) = 125t + 95.

Which statements about this function are true?
I. A house call fee costs $95.
II. The plumber charges $125 per hour.
III. The number of hours the job takes is represented by t.""",
            "choices": [
                "(1) I and II, only",
                "(2) I and III, only",
                "(3) II and III, only",
                "(4) I, II, and III"
            ],
            "correct_answer": 4,
            "page": 5
        },
        {
            "number": 10,
            "text": """What is the domain of the relation shown below?
{(4,2), (1,1), (0,0), (1,−1), (4,−2)}""",
            "choices": [
                "(1) {0, 1, 4}",
                "(2) {−2, −1, 0, 1, 2}",
                "(3) {−2, −1, 0, 1, 2, 4}",
                "(4) {−2, −1, 0, 0, 1, 1, 1, 2, 4, 4}"
            ],
            "correct_answer": 1,
            "page": 5
        }
    ]

    questions = []
    for q_data in questions_data:
        # Extract cropped image for questions with graphs
        image_bytes = None
        if q_data.get("has_graph", False):
            page_num = q_data["page"]
            crop_rect = q_data.get("graph_rect")
            image_bytes = extract_page_image(doc, page_num, crop_rect=crop_rect)

        questions.append(Question(
            number=q_data["number"],
            text=q_data["text"],
            choices=q_data["choices"],
            correct_answer=q_data.get("correct_answer", 1),
            has_graph=q_data.get("has_graph", False),
            page=q_data["page"],
            image_bytes=image_bytes
        ))

    return questions


def parse_questions_from_pdf(pdf_path: str) -> List[Question]:
    """Parse individual questions from the Regents PDF."""
    if not PDF_SUPPORT:
        return []

    questions = []
    doc = fitz.open(pdf_path)

    # Manually define the questions from the PDF (parsed from content)
    # This is more reliable than automatic parsing for structured exams
    questions_data = [
        {
            "number": 1,
            "text": """A part of Jennifer's work to solve the equation 2(6x² − 3) = 11x² − x is shown below.

Given: 2(6x² − 3) = 11x² − x
Step 1: 12x² − 6 = 11x² − x

Which property justifies her first step?""",
            "choices": [
                "(1) identity property of multiplication",
                "(2) multiplication property of equality",
                "(3) commutative property of multiplication",
                "(4) distributive property of multiplication over subtraction"
            ],
            "correct_answer": 4,
            "page": 2
        },
        {
            "number": 2,
            "text": "Which value of x results in equal outputs for j(x) = 3x − 2 and b(x) = |x + 2|?",
            "choices": [
                "(1) −2",
                "(2) 2",
                "(3) 2/3",
                "(4) 4"
            ],
            "correct_answer": 2,
            "page": 2
        },
        {
            "number": 3,
            "text": "The expression 49x² − 36 is equivalent to",
            "choices": [
                "(1) (7x − 6)²",
                "(2) (24.5x − 18)²",
                "(3) (7x − 6)(7x + 6)",
                "(4) (24.5x − 18)(24.5x + 18)"
            ],
            "correct_answer": 3,
            "page": 2
        },
        {
            "number": 4,
            "text": "If f(x) = ½x² − (¼x + 3), what is the value of f(8)?",
            "choices": [
                "(1) 11",
                "(2) 17",
                "(3) 27",
                "(4) 33"
            ],
            "correct_answer": 3,
            "page": 3
        },
        {
            "number": 5,
            "text": """The graph below models the height of a remote-control helicopter over 20 seconds during flight.

Over which interval does the helicopter have the slowest average rate of change?""",
            "choices": [
                "(1) 0 to 5 seconds",
                "(2) 5 to 10 seconds",
                "(3) 10 to 15 seconds",
                "(4) 15 to 20 seconds"
            ],
            "correct_answer": 3,
            "page": 3,
            "has_graph": True,
            "graph_rect": [0.1, 0.15, 0.9, 0.55]
        },
        {
            "number": 6,
            "text": """In the functions f(x) = kx² and g(x) = |kx|, k is a positive integer.
If k is replaced by ½, which statement about these new functions is true?""",
            "choices": [
                "(1) The graphs of both f(x) and g(x) become wider.",
                "(2) The graph of f(x) becomes narrower and the graph of g(x) shifts left.",
                "(3) The graphs of both f(x) and g(x) shift vertically.",
                "(4) The graph of f(x) shifts left and the graph of g(x) becomes wider."
            ],
            "correct_answer": 1,
            "page": 3
        },
        {
            "number": 7,
            "text": """Wenona sketched the polynomial P(x) as shown on the axes below.

Which equation could represent P(x)?""",
            "choices": [
                "(1) P(x) = (x + 1)(x − 2)²",
                "(2) P(x) = (x − 1)(x + 2)²",
                "(3) P(x) = (x + 1)(x − 2)",
                "(4) P(x) = (x − 1)(x + 2)"
            ],
            "correct_answer": 1,
            "page": 4,
            "has_graph": True,
            "graph_rect": [0.1, 0.1, 0.9, 0.5]
        },
        {
            "number": 8,
            "text": "Which situation does not describe a causal relationship?",
            "choices": [
                "(1) The higher the volume on a radio, the louder the sound will be.",
                "(2) The faster a student types a research paper, the more pages the research paper will have.",
                "(3) The shorter the time a car remains running, the less gasoline it will use.",
                "(4) The slower the pace of a runner, the longer it will take the runner to finish the race."
            ],
            "correct_answer": 2,
            "page": 4
        },
        {
            "number": 9,
            "text": """A plumber has a set fee for a house call and charges by the hour for repairs. The total cost of her services can be modeled by c(t) = 125t + 95.

Which statements about this function are true?
I. A house call fee costs $95.
II. The plumber charges $125 per hour.
III. The number of hours the job takes is represented by t.""",
            "choices": [
                "(1) I and II, only",
                "(2) I and III, only",
                "(3) II and III, only",
                "(4) I, II, and III"
            ],
            "correct_answer": 4,
            "page": 5
        },
        {
            "number": 10,
            "text": """What is the domain of the relation shown below?
{(4,2), (1,1), (0,0), (1,−1), (4,−2)}""",
            "choices": [
                "(1) {0, 1, 4}",
                "(2) {−2, −1, 0, 1, 2}",
                "(3) {−2, −1, 0, 1, 2, 4}",
                "(4) {−2, −1, 0, 0, 1, 1, 1, 2, 4, 4}"
            ],
            "correct_answer": 1,
            "page": 5
        }
    ]

    for q_data in questions_data:
        # Extract cropped image for questions with graphs
        image_bytes = None
        if q_data.get("has_graph", False):
            page_num = q_data["page"]
            crop_rect = q_data.get("graph_rect")  # [x0, y0, x1, y1] as percentages
            # Each graph gets its own cropped image (don't cache since crops differ)
            image_bytes = extract_page_image(doc, page_num, crop_rect=crop_rect)

        questions.append(Question(
            number=q_data["number"],
            text=q_data["text"],
            choices=q_data["choices"],
            correct_answer=q_data.get("correct_answer", 1),
            has_graph=q_data.get("has_graph", False),
            page=q_data["page"],
            image_bytes=image_bytes
        ))

    doc.close()
    return questions


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

    # Phrases that indicate the coach is asking for more info (NOT confirming correct)
    asking_for_explanation = [
        "walk me through", "how did you", "can you explain", "show me your",
        "what steps", "how you got", "tell me more", "explain your",
        "let's see your work", "walk through", "step-by-step", "step by step",
        "can you walk", "let me see"
    ]

    # If asking for explanation, it's NOT a confirmation yet
    for phrase in asking_for_explanation:
        if phrase in response_lower:
            return False

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

    # Strong phrases that DEFINITELY indicate correct answer
    # These are more specific and less likely to be false positives
    strong_correct_indicators = [
        "that's correct", "is correct", "you're correct",
        "that's the right answer", "the right answer",
        "you got it", "you nailed it", "exactly right",
        "you solved it", "problem solved", "well done!",
        "great work!", "perfect!", "that's it!"
    ]

    for phrase in strong_correct_indicators:
        if phrase in response_lower:
            return True

    return False


def run_async(coro):
    """Helper to run async functions in Streamlit."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def get_coach_response(problem: str, message: str, attempt: int) -> str:
    """Get response from the tutoring coach."""
    return run_async(process_turn(
        problem=problem,
        student_message=message,
        attempt_count=attempt
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
    st.markdown("*Your friendly middle-school algebra tutor*")

    # Sidebar for navigation
    with st.sidebar:
        st.header("📚 Questions")

        # Load Regents Exam button
        if st.button("Load Regents Exam", type="primary"):
            with st.spinner("Loading questions..."):
                st.session_state.questions = parse_questions_from_pdf("regents_test.pdf")
                st.session_state.current_question_idx = 0
                st.session_state.chat_history = []
                st.session_state.attempt_count = 0
                # Don't reset correct_questions if already exists
                if "correct_questions" not in st.session_state:
                    st.session_state.correct_questions = set()
            st.rerun()

        if st.session_state.questions:
            st.success(f"Loaded {len(st.session_state.questions)} questions!")

        st.divider()

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
        st.info("👈 Click **Load Regents Exam** in the sidebar to get started!")

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
                        response = get_coach_response(sample_problem, sample_response, 0)
                    st.markdown(f"**Coach:** {response}")
    else:
        # Display current question
        current_q = st.session_state.questions[st.session_state.current_question_idx]

        # Question display area
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader(f"Question {current_q.number}")

            # Question text
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <p style="font-size: 16px; line-height: 1.6; color: #1a1a1a;">{current_q.text.replace(chr(10), '<br>')}</p>
            </div>
            """, unsafe_allow_html=True)

            # Display graph/visual if available
            if current_q.has_graph and current_q.image_bytes:
                st.image(current_q.image_bytes, caption=f"Visual from page {current_q.page}", use_container_width=True)
            elif current_q.has_graph:
                st.info("📊 This question includes a graph. Refer to page " +
                       f"{current_q.page} of the exam for the visual.")

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
            if send_btn and user_input:
                with st.spinner("Coach is thinking..."):
                    # Build problem text
                    problem_text = f"{current_q.text}\n\nChoices:\n" + "\n".join(current_q.choices)
                    response = get_coach_response(
                        problem_text,
                        user_input,
                        st.session_state.attempt_count
                    )
                    st.session_state.chat_history.append(("You", user_input))
                    st.session_state.chat_history.append(("Coach", response))
                    st.session_state.attempt_count += 1
                    # Check if coach confirmed correct answer
                    if is_correct_response(response):
                        st.session_state.correct_questions.add(st.session_state.current_question_idx)
                st.rerun()

            if submit_answer:
                with st.spinner("Coach is checking your answer..."):
                    problem_text = f"{current_q.text}\n\nChoices:\n" + "\n".join(current_q.choices)
                    message = f"My answer is {selected_choice}"
                    response = get_coach_response(
                        problem_text,
                        message,
                        st.session_state.attempt_count
                    )
                    st.session_state.chat_history.append(("You", message))
                    st.session_state.chat_history.append(("Coach", response))
                    st.session_state.attempt_count += 1
                    # Check if coach confirmed correct answer
                    if is_correct_response(response):
                        st.session_state.correct_questions.add(st.session_state.current_question_idx)
                st.rerun()

            if reveal_btn:
                with st.spinner("Getting the answer..."):
                    problem_text = f"{current_q.text}\n\nChoices:\n" + "\n".join(current_q.choices)
                    response = get_coach_response(
                        problem_text,
                        "Please show me the answer",
                        attempt_count=5,  # Force reveal
                        reveal_now=True
                    ) if False else run_async(process_turn(
                        problem=problem_text,
                        student_message="Please show me the answer",
                        attempt_count=5,
                        reveal_now=True
                    ))
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
                            response = get_coach_response(problem_text, "I'm ready to start", 0)
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
                        st.rerun()
            with nav_col2:
                if st.session_state.current_question_idx < len(st.session_state.questions) - 1:
                    if st.button("Next →", use_container_width=True):
                        st.session_state.current_question_idx += 1
                        st.session_state.chat_history = []
                        st.session_state.attempt_count = 0
                        st.rerun()


if __name__ == "__main__":
    main()
