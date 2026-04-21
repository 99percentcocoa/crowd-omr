import re
from typing import Tuple


HEADER_PATTERN = re.compile(r"^\s*उत्तरे\s*:\s*$")
ANSWER_PATTERN = re.compile(r"^\s*(\d+)\s*:\s*(\S+)\s*$")
VALID_OPTIONS = {"A", "B", "C", "D"}


def validate_and_parse_template_reply(
    text_body: str,
    question_count: int,
) -> Tuple[bool, dict[str, str], str]:
    """
    Validate a user reply against the fixed answer template and parse answers.

    Rules:
    - Header must be present as: "उत्तरे:" (whitespace variations allowed).
    - Questions must appear in order from 1..question_count.
    - Each answer line format must remain: "N: X" where X is only A/B/C/D.
    - Extra non-whitespace lines are rejected.
    """
    answers = {str(i): "" for i in range(1, question_count + 1)}

    meaningful_lines = [line for line in text_body.splitlines() if line.strip()]

    if not meaningful_lines:
        return False, answers, "Empty response"

    if not HEADER_PATTERN.match(meaningful_lines[0]):
        return False, answers, "Missing or invalid template header"

    answer_lines = meaningful_lines[1:]

    if len(answer_lines) != question_count:
        return False, answers, "Incorrect number of answer lines"

    expected_q = 1
    for line in answer_lines:
        match = ANSWER_PATTERN.match(line)
        if not match:
            return False, answers, "Invalid answer line format"

        q_num, option = match.groups()
        if int(q_num) != expected_q:
            return False, answers, "Question numbers are missing or out of order"

        normalized_option = option.strip().upper()
        if normalized_option not in VALID_OPTIONS:
            return False, answers, f"Invalid option for question {q_num}: use only A/B/C/D"

        answers[q_num] = normalized_option
        expected_q += 1

    return True, answers, ""
