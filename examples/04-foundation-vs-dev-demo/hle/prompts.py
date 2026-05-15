"""Prompts for the HLE portion of the demo. Same as example 02."""

SOLVER_PROMPT_TEMPLATE = """\
I have a question I would like you to answer for me to the best of your ability.

The question is in the file 'question.md' in the current directory.{image_note}

Write the final answer to 'answer.txt' in the current directory. The file must \
have a clear, definitive final answer on the last line, formatted as: \
ANSWER: <your answer>

You should write tools, run code, and so forth where appropriate to figure out \
the answer, but DO NOT search the web or explore files outside of your current \
directory.

The answer must be precise and unambiguous.

Treat me as if I am asleep. I am not here to answer questions, only to read \
your output afterwards."""

IMAGE_NOTE = (
    "\n\nAn image is provided for this question. It is saved at "
    "'{image_filename}' in the current directory. Examine it as part "
    "of your work."
)

JUDGE_SYSTEM_PROMPT = (
    "Judge whether the following [response] to [question] is correct or not "
    "based on the precise and unambiguous [correct_answer] below."
)

JUDGE_USER_PROMPT_TEMPLATE = """[question]: {question}

[response]: {response}

Your judgement must be in the format and criteria specified below:

extracted_final_answer: The final exact answer extracted from the [response]. \
Put the extracted answer as 'None' if there is no exact, final answer to extract from the response.

[correct_answer]: {correct_answer}

reasoning: Explain why the extracted_final_answer is correct or incorrect \
based on [correct_answer], focusing only on if there are meaningful \
differences between [correct_answer] and the extracted_final_answer. \
Do not comment on any background to the problem, do not attempt to solve \
the problem, do not argue for any answer different than \
[correct_answer], focus only on whether the answers match.

correct: Answer 'yes' if extracted_final_answer matches the \
[correct_answer] given above, or is within a small margin of error for \
numerical problems. Answer 'no' otherwise, i.e. if there if there is any \
inconsistency, ambiguity, non-equivalency, or if the extracted answer is incorrect."""


def build_solver_prompt(image_filename: str | None) -> str:
    note = IMAGE_NOTE.format(image_filename=image_filename) if image_filename else ""
    return SOLVER_PROMPT_TEMPLATE.format(image_note=note)


def build_judge_prompt(question: str, response: str, correct_answer: str) -> str:
    user = JUDGE_USER_PROMPT_TEMPLATE.format(
        question=question,
        response=response,
        correct_answer=correct_answer,
    )
    return f"{JUDGE_SYSTEM_PROMPT}\n\n{user}"