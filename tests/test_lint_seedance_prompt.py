from scripts.lint_seedance_prompt import lint_prompt


VALID_PROMPT = """
Use the uploaded storyboard image as the primary visual reference.
Animate the storyboard frames left to right, top to bottom.

- Duration: 15 seconds
- Aspect ratio: 9:16
- Audio mode: preserve original dialogue

Dialogue Timeline
00:00.000-00:02.000 Speaker says: "Look at this."
"""


def test_lint_prompt_accepts_required_storyboard_rules():
    assert lint_prompt(VALID_PROMPT, speech="yes") == []


def test_lint_prompt_rejects_reference_video_instruction():
    errors = lint_prompt(VALID_PROMPT + "\nUse the uploaded reference video as the reference.\n")

    assert any("forbidden reference-video instruction" in error for error in errors)


def test_lint_prompt_requires_dialogue_when_speech_present():
    prompt = VALID_PROMPT.replace('00:00.000-00:02.000 Speaker says: "Look at this."', "")

    assert "speech is marked present, but timestamped dialogue is missing" in lint_prompt(prompt, speech="yes")
