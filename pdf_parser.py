"""
PDF Parser using LlamaParse for automatic question extraction.
"""

import os
import re
import json
from typing import List, Optional, Tuple
from dataclasses import dataclass

# LlamaParse imports
try:
    from llama_parse import LlamaParse
    LLAMAPARSE_AVAILABLE = True
except ImportError:
    LLAMAPARSE_AVAILABLE = False

# Anthropic for question structuring
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Streamlit for secrets
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False


@dataclass
class ParsedQuestion:
    """Represents a parsed question from a PDF."""
    number: int
    text: str
    choices: List[str]
    correct_answer: int = 0  # 0 means unknown, 1-4 for multiple choice
    has_graph: bool = False
    page: int = 1
    raw_markdown: str = ""
    question_type: str = "mcq"  # "mcq" or "frq"


def get_llama_api_key() -> Optional[str]:
    """Get LlamaCloud API key from environment or Streamlit secrets."""
    # Try Streamlit secrets first
    if STREAMLIT_AVAILABLE:
        try:
            return st.secrets.get("LLAMA_CLOUD_API_KEY")
        except:
            pass
    # Fall back to environment variable
    return os.environ.get("LLAMA_CLOUD_API_KEY")


def get_anthropic_api_key() -> Optional[str]:
    """Get Anthropic API key from environment or Streamlit secrets."""
    if STREAMLIT_AVAILABLE:
        try:
            return st.secrets.get("ANTHROPIC_API_KEY")
        except:
            pass
    return os.environ.get("ANTHROPIC_API_KEY")


def parse_pdf_with_llamaparse(pdf_path: str = None, pdf_bytes: bytes = None, filename: str = "document.pdf") -> str:
    """
    Parse a PDF file using LlamaParse and return markdown content.

    Args:
        pdf_path: Path to PDF file (optional)
        pdf_bytes: Raw PDF bytes (optional)
        filename: Filename for the PDF

    Returns:
        Markdown string of the parsed PDF content
    """
    if not LLAMAPARSE_AVAILABLE:
        raise ImportError("llama-parse is not installed. Run: pip install llama-parse")

    api_key = get_llama_api_key()
    if not api_key:
        raise ValueError("LLAMA_CLOUD_API_KEY not found. Set it in environment or Streamlit secrets.")

    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",
        verbose=True,
        language="en",
        # Use premium mode for better table/graph extraction
        premium_mode=True,
    )

    if pdf_bytes:
        # Save bytes to temp file for parsing - use actual file extension
        import tempfile
        file_ext = filename.split('.')[-1].lower() if '.' in filename else 'pdf'
        with tempfile.NamedTemporaryFile(suffix=f".{file_ext}", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        try:
            documents = parser.load_data(tmp_path)
        finally:
            os.unlink(tmp_path)
    elif pdf_path:
        documents = parser.load_data(pdf_path)
    else:
        raise ValueError("Either pdf_path or pdf_bytes must be provided")

    # Combine all document content
    full_markdown = "\n\n".join([doc.text for doc in documents])
    return full_markdown


def extract_questions_with_regex(markdown: str) -> List[ParsedQuestion]:
    """
    Extract questions from markdown using regex patterns.
    Works well for standardized test formats.
    """
    questions = []

    # Pattern for numbered questions (1., 2., etc. or 1), 2), etc.)
    # This pattern captures: question number, question text, and answer choices
    question_pattern = r'(?:^|\n)(\d+)[.\)]\s*(.*?)(?=\n\d+[.\)]|\n*$)'

    # Pattern for answer choices (1), (2), (3), (4) or A), B), C), D)
    choice_pattern = r'\((\d)\)\s*([^\(]+?)(?=\(\d\)|$)'

    # Split by question numbers
    parts = re.split(r'\n(?=\d+[.\)])', markdown)

    for part in parts:
        if not part.strip():
            continue

        # Try to extract question number
        num_match = re.match(r'^(\d+)[.\)]\s*', part)
        if not num_match:
            continue

        q_num = int(num_match.group(1))
        remaining = part[num_match.end():]

        # Find answer choices
        choices = re.findall(choice_pattern, remaining)

        if choices:
            # Extract question text (everything before first choice)
            first_choice_pos = remaining.find(f"({choices[0][0]})")
            question_text = remaining[:first_choice_pos].strip() if first_choice_pos > 0 else remaining.strip()
            choice_list = [f"({num}) {text.strip()}" for num, text in choices]
        else:
            question_text = remaining.strip()
            choice_list = []

        # Check if question mentions graph/figure/diagram
        has_graph = bool(re.search(r'graph|figure|diagram|chart|image|below|shown', question_text.lower()))

        questions.append(ParsedQuestion(
            number=q_num,
            text=question_text,
            choices=choice_list,
            has_graph=has_graph,
            raw_markdown=part
        ))

    return questions


def extract_questions_with_claude(markdown: str) -> List[ParsedQuestion]:
    """
    Use Claude to intelligently extract and structure questions from markdown.
    More robust than regex for varied formats.
    """
    if not ANTHROPIC_AVAILABLE:
        raise ImportError("anthropic is not installed")

    api_key = get_anthropic_api_key()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found")

    client = Anthropic(api_key=api_key)

    prompt = f"""Extract ALL questions (both multiple choice AND free response) from this exam content.

Return a JSON array where each object has:
- "number": question number (integer)
- "text": the full question text
- "type": "mcq" for multiple choice (has 4 choices), "frq" for free response (no choices)
- "choices": array of 4 answer choices like ["(1) option1", "(2) option2", "(3) option3", "(4) option4"] for MCQ, empty array [] for FRQ
- "has_graph": true if the question references or shows a graph, figure, diagram, table, or image
- "correct_answer": 0
- "page": the page number where this question appears in the QUESTION section (not counting cover pages). First question page = 1

RULES:
- Extract BOTH multiple choice questions (with 4 choices) AND free response questions (without choices)
- For MCQ: Answer choices use (1), (2), (3), (4) format
- For FRQ: Set "choices" to empty array [] and "type" to "frq"
- Extract ALL questions completely
- NO comments, NO explanations - ONLY the JSON array
- The JSON must be complete and valid
- IMPORTANT: Use plain text for math, NOT LaTeX. Write "f(x) = (x - 2)^2 + 4" not "$f(x) = (x - 2)^2 + 4$"
- Remove all $ signs and LaTeX formatting from the text
- Set has_graph=true for ANY question that mentions "graph", "below", "shown", "figure", "table", "diagram", or displays visual data
- CRITICAL for graph questions: DO NOT include numerical values that give away the answer. No slopes, no y-intercepts, no specific coordinates, no vertex locations. Only describe the general shape (e.g., "a line with negative slope", "a V-shaped graph", "shaded region below the line"). The student should determine the numbers themselves.

Content:
{markdown}

Output the complete JSON array:"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response.content[0].text.strip()

    # Try to parse JSON
    try:
        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            response_text = re.sub(r'^```json?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)

        # Find the JSON array boundaries
        start_idx = response_text.find('[')
        end_idx = response_text.rfind(']')
        if start_idx != -1 and end_idx != -1:
            response_text = response_text[start_idx:end_idx + 1]

        # Remove any JavaScript-style comments
        response_text = re.sub(r'//[^\n]*\n', '\n', response_text)
        response_text = re.sub(r'//[^\n]*$', '', response_text)

        questions_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"Failed to parse Claude response as JSON: {e}")
        print(f"Response length: {len(response_text)}")
        print(f"Response start: {response_text[:500]}")
        print(f"Response end: {response_text[-500:]}")
        return []

    questions = []
    for q in questions_data:
        questions.append(ParsedQuestion(
            number=q.get("number", 0),
            text=q.get("text", ""),
            choices=q.get("choices", []),
            correct_answer=q.get("correct_answer", 0),
            has_graph=q.get("has_graph", False),
            page=q.get("page", 1),
            question_type=q.get("type", "mcq"),
        ))

    return questions


def parse_pdf_to_questions(
    pdf_path: str = None,
    pdf_bytes: bytes = None,
    filename: str = "document.pdf",
    use_claude: bool = True
) -> Tuple[List[ParsedQuestion], str]:
    """
    Main function to parse a PDF and extract questions.

    Args:
        pdf_path: Path to PDF file
        pdf_bytes: Raw PDF bytes
        filename: Filename for reference
        use_claude: Whether to use Claude for question extraction (more accurate but slower)

    Returns:
        Tuple of (list of questions, raw markdown)
    """
    # Step 1: Parse PDF to markdown using LlamaParse
    markdown = parse_pdf_with_llamaparse(pdf_path=pdf_path, pdf_bytes=pdf_bytes, filename=filename)

    # Step 2: Extract questions
    if use_claude:
        try:
            questions = extract_questions_with_claude(markdown)
        except Exception as e:
            print(f"Claude extraction failed, falling back to regex: {e}")
            questions = extract_questions_with_regex(markdown)
    else:
        questions = extract_questions_with_regex(markdown)

    return questions, markdown


# Convenience function for direct usage
def parse_exam_pdf(pdf_path: str) -> List[ParsedQuestion]:
    """
    Simple function to parse an exam PDF and return questions.

    Usage:
        questions = parse_exam_pdf("my_exam.pdf")
        for q in questions:
            print(f"Q{q.number}: {q.text}")
            for choice in q.choices:
                print(f"  {choice}")
    """
    questions, _ = parse_pdf_to_questions(pdf_path=pdf_path)
    return questions


if __name__ == "__main__":
    # Test the parser
    import sys

    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        print(f"Parsing: {pdf_file}")

        try:
            questions, markdown = parse_pdf_to_questions(pdf_path=pdf_file)

            print(f"\n{'='*50}")
            print(f"Found {len(questions)} questions")
            print(f"{'='*50}\n")

            for q in questions:
                print(f"Question {q.number}:")
                print(f"  Text: {q.text[:100]}..." if len(q.text) > 100 else f"  Text: {q.text}")
                print(f"  Choices: {len(q.choices)}")
                print(f"  Has graph: {q.has_graph}")
                print()

        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python pdf_parser.py <pdf_file>")
        print("\nMake sure to set LLAMA_CLOUD_API_KEY environment variable")
