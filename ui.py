"""
Math Stan - Streamlit UI
A basic web interface for the tutoring application with gamification features.
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

# Import Firebase and shop modules
try:
    from firebase_config import (
        sign_up, sign_in, get_user_data, update_currency,
        increment_solved_questions, purchase_item, equip_item, unequip_item
    )
    from shop_data import ACCESSORIES, SLOTS, get_accessory, get_accessories_by_slot
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


@dataclass
class Question:
    """Represents a single question from the exam."""
    number: int
    text: str
    choices: List[str]
    correct_answer: int = 0  # 1-indexed (1, 2, 3, or 4) for MCQ, 0 for FRQ
    has_graph: bool = False
    page: int = 1
    question_type: str = "mcq"  # "mcq" or "frq"


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
                choices=lq.choices if lq.choices else [],
                correct_answer=lq.correct_answer,
                has_graph=lq.has_graph,
                page=lq.page if lq.page > 0 else 1,
                question_type=lq.question_type,
            ))

        return questions
    except Exception as e:
        print(f"Exception during parsing: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_sample_questions() -> List[Question]:
    """Return hardcoded sample questions from Regents Algebra 1 exam."""
    return [
        Question(
            number=1,
            text="The owner of a small computer repair business has one employee, who is paid an hourly rate of $22. The owner estimates his weekly profit using the function P(x) = 8600 - 22x. In this function, x represents",
            choices=[
                "(1) the number of computers repaired per week",
                "(2) the number of hours worked per week",
                "(3) the employee's total weekly pay",
                "(4) the total weekly profit"
            ],
            correct_answer=2,
            page=1
        ),
        Question(
            number=2,
            text="Solve the equation 2(x + 2) + 2 = 4x + 8 algebraically. Show your work.",
            choices=[],
            correct_answer=-1,
            page=1,
            question_type="frq"
        ),
        Question(
            number=3,
            text="If the difference (3x² - 2x + 5) - (x² + 3x - 2) is multiplied by ½x², what is the result, written in standard form?",
            choices=[
                "(1) 2x⁴ - 5x³ + 7x²",
                "(2) x⁴ - 5/2x³ + 7/2x²",
                "(3) x⁴ + 1/2x³ + 3/2x²",
                "(4) x⁴ - 5x³ + 7x²"
            ],
            correct_answer=2,
            page=1
        ),
        Question(
            number=4,
            text="Which expression is equivalent to (x + 4)² - (x + 4)?",
            choices=[
                "(1) x² + 7x + 12",
                "(2) x² + 9x + 20",
                "(3) x² + 7x + 20",
                "(4) x² + 9x + 12"
            ],
            correct_answer=1,
            page=1
        ),
        Question(
            number=5,
            text="The minimum value of the function f(x) = (x - 2)² + 4 is",
            choices=[
                "(1) -2",
                "(2) 2",
                "(3) -4",
                "(4) 4"
            ],
            correct_answer=4,
            page=1
        ),
    ]


def init_session_state():
    """Initialize Streamlit session state variables."""
    # Authentication state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "user_name" not in st.session_state:
        st.session_state.user_name = ""

    # Question state
    if "questions" not in st.session_state:
        st.session_state.questions = get_sample_questions()
    if "using_sample_questions" not in st.session_state:
        st.session_state.using_sample_questions = True
    if "current_question_idx" not in st.session_state:
        st.session_state.current_question_idx = 0
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "attempt_count" not in st.session_state:
        st.session_state.attempt_count = 0
    if "coach_initialized" not in st.session_state:
        st.session_state.coach_initialized = False
    if "correct_questions" not in st.session_state:
        st.session_state.correct_questions = set()
    if "answer_is_correct" not in st.session_state:
        st.session_state.answer_is_correct = False
    if "awaiting_explanation" not in st.session_state:
        st.session_state.awaiting_explanation = False

    # Track questions that have already awarded coins (to prevent double-awarding)
    if "rewarded_questions" not in st.session_state:
        st.session_state.rewarded_questions = set()

    # Current page/tab
    if "current_tab" not in st.session_state:
        st.session_state.current_tab = "Practice"


def get_selected_answer_number(selected_choice: str) -> int:
    """Extract the answer number (1-4) from the selected choice string."""
    if selected_choice and selected_choice.startswith("("):
        try:
            return int(selected_choice[1])
        except (ValueError, IndexError):
            pass
    return 0


def is_correct_response(response: str) -> bool:
    """Check if the coach's response indicates the answer is correct."""
    response_lower = response.lower()

    strong_correct_indicators = [
        "that's correct", "is correct", "you're correct",
        "that's the right answer", "the right answer",
        "you got it", "you nailed it", "exactly right",
        "you solved it", "problem solved", "well done",
        "great work", "perfect", "nice work", "good job"
    ]

    for phrase in strong_correct_indicators:
        if phrase in response_lower:
            return True

    incorrect_indicators = [
        "not quite", "not correct", "incorrect", "try again", "not right",
        "that's not", "wrong", "close but", "almost", "not exactly",
        "let's think", "think about", "check your", "look again",
        "careful", "watch out", "hmm", "are you sure"
    ]

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


def show_login_page():
    """Display the login/signup page."""
    st.title("📐 Math Stan")
    st.markdown("**Welcome!** Sign in or create an account to start learning.")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

        with tab1:
            st.subheader("Sign In")
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")

            if st.button("Sign In", type="primary", use_container_width=True):
                if login_email and login_password:
                    result = sign_in(login_email, login_password)
                    if result["success"]:
                        st.session_state.logged_in = True
                        st.session_state.user_id = result["user_id"]
                        user_data = get_user_data(result["user_id"])
                        if user_data:
                            st.session_state.user_name = user_data.get("name", "Student")
                        st.success(result["message"])
                        st.rerun()
                    else:
                        st.error(result["message"])
                else:
                    st.warning("Please enter your email and password.")

        with tab2:
            st.subheader("Create Account")
            signup_name = st.text_input("Your Name", key="signup_name")
            signup_email = st.text_input("Email", key="signup_email")
            signup_password = st.text_input("Password", type="password", key="signup_password",
                                            help="At least 6 characters")

            if st.button("Create Account", type="primary", use_container_width=True):
                if signup_name and signup_email and signup_password:
                    result = sign_up(signup_email, signup_password, signup_name)
                    if result["success"]:
                        st.session_state.logged_in = True
                        st.session_state.user_id = result["user_id"]
                        st.session_state.user_name = signup_name
                        st.success(result["message"])
                        st.rerun()
                    else:
                        st.error(result["message"])
                else:
                    st.warning("Please fill in all fields.")

        # Guest mode option
        st.divider()
        st.caption("Or continue without an account:")
        if st.button("Continue as Guest", use_container_width=True):
            st.session_state.logged_in = True
            st.session_state.user_id = None
            st.session_state.user_name = "Guest"
            st.rerun()


def show_header_with_coins():
    """Display header with coin count for logged-in users."""
    user_data = None
    if st.session_state.user_id:
        user_data = get_user_data(st.session_state.user_id)

    header_col1, header_col2, header_col3 = st.columns([3, 1, 1])

    with header_col1:
        st.title("📐 Math Stan")

    with header_col2:
        if user_data:
            coins = user_data.get("currency", 0)
            st.markdown(f"""
            <div style="background-color: #ffd700; padding: 10px 15px; border-radius: 20px;
                        text-align: center; margin-top: 15px; color: #000;">
                <strong>🪙 {coins}</strong>
            </div>
            """, unsafe_allow_html=True)
        elif st.session_state.user_id is None:
            st.caption("Guest Mode")

    with header_col3:
        st.image("mathowl.png", width=80)


def show_practice_page():
    """Display the main practice/tutoring page."""
    # Sidebar for navigation
    with st.sidebar:
        st.header("📚 Questions")

        # Upload PDF or Image
        st.subheader("Upload Exam")
        uploaded_file = st.file_uploader(
            "Upload a PDF or image",
            type=["pdf", "png", "jpg", "jpeg"],
            help="Upload a PDF or photo of your exam and we'll automatically extract the questions!"
        )
        st.caption("Accepted formats: PDF, PNG, JPG, JPEG")

        if uploaded_file is not None:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            if file_size_mb > 10:
                st.error(f"File too large ({file_size_mb:.1f} MB). Please upload a file under 10 MB.")
            else:
                use_ai_parsing = st.checkbox(
                    "Use AI parsing (May take a few minutes)",
                    value=True,
                    help="Uses LlamaParse + Claude to automatically detect questions. Requires API keys."
                )

                if st.button("Parse Image", type="primary"):
                    with st.spinner("Parsing image... This may take a moment for AI parsing."):
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
                        st.session_state.using_sample_questions = False

                    if st.session_state.questions:
                        st.success(f"Extracted {len(st.session_state.questions)} questions!")
                    else:
                        st.error("Could not extract questions from this PDF.")
                    st.rerun()

        st.divider()

        # Question selector with progress
        if st.session_state.questions:
            correct_count = len(st.session_state.correct_questions)
            total_count = len(st.session_state.questions)

            if st.session_state.using_sample_questions:
                st.subheader(f"📝 Sample Questions ({correct_count}/{total_count} ✓)")
                st.caption("From Regents Algebra 1 Exam")
            else:
                st.subheader(f"📄 Your Questions ({correct_count}/{total_count} ✓)")

            for i, q in enumerate(st.session_state.questions):
                is_correct = i in st.session_state.correct_questions
                is_current = i == st.session_state.current_question_idx

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
        st.info("👈 Select a question from the sidebar to get started, or upload your own PDF exam!")
    else:
        current_q = st.session_state.questions[st.session_state.current_question_idx]

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader(f"Question {current_q.number}")

            st.markdown(f"""
            <div style="background-color: #ffffff; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #e0e0e0; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <p style="font-size: 16px; line-height: 1.6; color: #000000;">{current_q.text.replace(chr(10), '<br>')}</p>
            </div>
            """, unsafe_allow_html=True)

            selected_choice = None

            if current_q.question_type == "mcq" and current_q.choices:
                st.markdown("**Answer Choices:**")
                selected_choice = st.radio(
                    "Select your answer:",
                    current_q.choices,
                    key=f"choices_{current_q.number}",
                    label_visibility="collapsed"
                )
                st.divider()

            st.markdown("**💬 Chat with your Coach:**")

            user_input = st.text_area(
                "Type your response, question, or reasoning:",
                key=f"user_input_{current_q.number}",
                placeholder="Tell me what you're thinking, ask a question, or explain your reasoning...",
                height=100
            )

            col_a, col_b, col_c = st.columns([1, 1, 2])
            with col_a:
                send_btn = st.button("Send to Coach", type="primary", use_container_width=True)
            with col_b:
                submit_answer = st.button("Submit Answer", use_container_width=True)
            with col_c:
                reveal_disabled = st.session_state.attempt_count < 3
                reveal_label = "Reveal Answer" if not reveal_disabled else f"Reveal Answer ({3 - st.session_state.attempt_count} more attempts)"
                reveal_btn = st.button(reveal_label, use_container_width=True, disabled=reveal_disabled)

            is_mcq = current_q.question_type == "mcq" and current_q.choices
            correct_answer_text = current_q.choices[current_q.correct_answer - 1] if is_mcq and current_q.correct_answer > 0 else ""

            if is_mcq:
                problem_text = f"{current_q.text}\n\nChoices:\n" + "\n".join(current_q.choices)
            else:
                problem_text = f"[Free Response Question]\n{current_q.text}"

            if send_btn and user_input:
                with st.spinner("Coach is thinking..."):
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

                    if is_correct_response(response):
                        if not st.session_state.answer_is_correct:
                            st.session_state.answer_is_correct = True
                            st.session_state.awaiting_explanation = True
                            st.session_state.correct_questions.add(st.session_state.current_question_idx)

                            # Award coins if user is logged in and hasn't been rewarded for this question
                            question_key = f"{st.session_state.current_question_idx}_{current_q.number}"
                            if st.session_state.user_id and question_key not in st.session_state.rewarded_questions:
                                update_currency(st.session_state.user_id, 5)
                                increment_solved_questions(st.session_state.user_id)
                                st.session_state.rewarded_questions.add(question_key)
                                st.toast("🪙 +5 coins!")
                st.rerun()

            if submit_answer:
                if is_mcq:
                    answer_to_submit = selected_choice
                    message = f"My answer is {selected_choice}"
                else:
                    answer_to_submit = user_input
                    message = f"My answer is: {user_input}"

                if answer_to_submit:
                    with st.spinner("Coach is checking your answer..."):
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

                        if is_correct_response(response):
                            st.session_state.answer_is_correct = True
                            st.session_state.awaiting_explanation = True
                            st.session_state.correct_questions.add(st.session_state.current_question_idx)

                            # Award coins
                            question_key = f"{st.session_state.current_question_idx}_{current_q.number}"
                            if st.session_state.user_id and question_key not in st.session_state.rewarded_questions:
                                update_currency(st.session_state.user_id, 5)
                                increment_solved_questions(st.session_state.user_id)
                                st.session_state.rewarded_questions.add(question_key)
                                st.toast("🪙 +5 coins!")
                    st.rerun()
                else:
                    st.warning("Please enter an answer before submitting.")

            if reveal_btn:
                with st.spinner("Getting the answer..."):
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
                    st.session_state.correct_questions.add(st.session_state.current_question_idx)
                    # No coins awarded for revealed answers
                st.rerun()

        with col2:
            st.subheader("💬 Chat History")

            chat_container = st.container(height=500)
            with chat_container:
                if not st.session_state.chat_history:
                    st.markdown("*Start by typing a response or question below!*")

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

            st.divider()
            st.markdown(f"**Attempts:** {st.session_state.attempt_count}")

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


def show_shop_page():
    """Display the shop page where users can buy accessories."""
    st.subheader("🛒 Accessory Shop")

    if st.session_state.user_id is None:
        st.warning("Please sign in to use the shop! Guest mode doesn't save progress.")
        return

    user_data = get_user_data(st.session_state.user_id)
    if not user_data:
        st.error("Could not load user data.")
        return

    coins = user_data.get("currency", 0)
    inventory = user_data.get("inventory", [])

    st.markdown(f"### 🪙 Your Coins: **{coins}**")
    st.markdown("Buy accessories to customize your owl!")

    st.divider()

    # Display accessories by slot
    for slot in SLOTS:
        st.markdown(f"#### {slot.title()} Items")
        slot_items = get_accessories_by_slot(slot)

        cols = st.columns(3)
        for idx, (item_id, item) in enumerate(slot_items.items()):
            with cols[idx % 3]:
                owned = item_id in inventory

                st.markdown(f"""
                <div style="background-color: {'#d4edda' if owned else '#f8f9fa'}; padding: 15px;
                            border-radius: 10px; text-align: center; margin-bottom: 10px;
                            border: 2px solid {'#28a745' if owned else '#dee2e6'};">
                    <div style="font-size: 40px;">{item['emoji']}</div>
                    <div style="font-weight: bold; color: #000;">{item['name']}</div>
                    <div style="color: #666; font-size: 12px;">{item['description']}</div>
                    <div style="color: #ffc107; font-weight: bold;">🪙 {item['price']}</div>
                </div>
                """, unsafe_allow_html=True)

                if owned:
                    st.button("✓ Owned", key=f"buy_{item_id}", disabled=True, use_container_width=True)
                else:
                    if st.button(f"Buy", key=f"buy_{item_id}", use_container_width=True):
                        result = purchase_item(st.session_state.user_id, item_id, item['price'])
                        if result["success"]:
                            st.success(result["message"])
                            st.rerun()
                        else:
                            st.error(result["message"])

        st.divider()


def show_owl_page():
    """Display the owl customization page."""
    st.subheader("🦉 My Owl")

    if st.session_state.user_id is None:
        st.warning("Please sign in to customize your owl! Guest mode doesn't save progress.")
        return

    user_data = get_user_data(st.session_state.user_id)
    if not user_data:
        st.error("Could not load user data.")
        return

    inventory = user_data.get("inventory", [])
    equipped = user_data.get("equipped", {})

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Your Owl")

        # Display owl with equipped items
        st.image("mathowl.png", width=250)

        # Show what's equipped
        st.markdown("**Currently Wearing:**")
        for slot in SLOTS:
            item_id = equipped.get(slot)
            if item_id:
                item = get_accessory(item_id)
                st.markdown(f"- **{slot.title()}:** {item.get('emoji', '')} {item.get('name', item_id)}")
            else:
                st.markdown(f"- **{slot.title()}:** *(empty)*")

    with col2:
        st.markdown("### Your Inventory")

        if not inventory:
            st.info("You don't have any accessories yet! Visit the shop to buy some.")
        else:
            for slot in SLOTS:
                slot_items = [item_id for item_id in inventory if get_accessory(item_id).get("slot") == slot]
                if slot_items:
                    st.markdown(f"**{slot.title()}:**")
                    for item_id in slot_items:
                        item = get_accessory(item_id)
                        is_equipped = equipped.get(slot) == item_id

                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.markdown(f"{item.get('emoji', '')} {item.get('name', item_id)}")
                        with col_b:
                            if is_equipped:
                                if st.button("Remove", key=f"unequip_{item_id}"):
                                    unequip_item(st.session_state.user_id, slot)
                                    st.rerun()
                            else:
                                if st.button("Equip", key=f"equip_{item_id}"):
                                    equip_item(st.session_state.user_id, item_id, slot)
                                    st.rerun()


def show_profile_page():
    """Display the user profile page."""
    st.subheader("👤 My Profile")

    if st.session_state.user_id is None:
        st.warning("You're in guest mode. Sign in to save your progress!")

        if st.button("Sign In / Create Account"):
            st.session_state.logged_in = False
            st.rerun()
        return

    user_data = get_user_data(st.session_state.user_id)
    if not user_data:
        st.error("Could not load user data.")
        return

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Account Info")
        st.markdown(f"**Name:** {user_data.get('name', 'Unknown')}")
        st.markdown(f"**Email:** {user_data.get('email', 'Unknown')}")

        st.divider()

        if st.button("Sign Out"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.user_name = ""
            st.session_state.rewarded_questions = set()
            st.rerun()

    with col2:
        st.markdown("### Stats")

        coins = user_data.get("currency", 0)
        solved = user_data.get("solved_questions", 0)
        inventory_count = len(user_data.get("inventory", []))

        st.metric("🪙 Coins", coins)
        st.metric("✅ Questions Solved", solved)
        st.metric("🎒 Items Owned", inventory_count)


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Math Stan",
        page_icon="📐",
        layout="wide"
    )

    init_session_state()

    # Check if Firebase is available
    if not FIREBASE_AVAILABLE:
        st.error("Firebase modules not loaded. Please check your installation.")
        return

    # Show login page if not logged in
    if not st.session_state.logged_in:
        show_login_page()
        return

    # Show header with coins
    show_header_with_coins()

    # Navigation tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Practice", "🛒 Shop", "🦉 My Owl", "👤 Profile"])

    with tab1:
        show_practice_page()

    with tab2:
        show_shop_page()

    with tab3:
        show_owl_page()

    with tab4:
        show_profile_page()


if __name__ == "__main__":
    main()
