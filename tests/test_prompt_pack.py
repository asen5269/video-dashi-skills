from scripts.build_prompt_pack import render_seedance_prompt


def test_render_seedance_prompt_keeps_user_aspect_ratio():
    result = render_seedance_prompt(
        {
            "replacement_target": "original ring",
            "duration": "15 seconds",
            "aspect_ratio": "1:1",
            "audio_mode": "preserve original music rhythm",
            "style": "UGC product demo",
            "preserve_rules": "- Preserve model\n- Preserve hand motion",
            "change_rules": "- Replace ring with uploaded ring",
            "negative_rules": "- Do not change face\n- Do not change background",
            "shot_prompts": "Shot 1: close-up hand reveal.",
        }
    )

    assert "1:1" in result
    assert "preserve original music rhythm" in result
    assert "Replace only: original ring" in result
    assert "Do not assume" not in result


def test_render_seedance_prompt_uses_storyboard_image_not_reference_video():
    result = render_seedance_prompt(
        {
            "storyboard_image": "storyboard_grid.jpg",
            "replacement_target": "top-left reaction inset",
            "duration": "14-15 seconds",
            "aspect_ratio": "9:16",
            "audio_mode": "upbeat rhythm",
            "style": "realistic UGC sports video",
            "preserve_rules": "- Preserve frame order",
            "change_rules": "- Remove top-left reaction inset",
            "negative_rules": "- No picture-in-picture",
            "shot_prompts": "Animate storyboard frames left to right, top to bottom.",
        }
    )

    assert "Use the uploaded storyboard image as the primary visual reference." in result
    assert "Animate the storyboard frames left to right, top to bottom." in result
    assert "storyboard_grid.jpg" in result
    assert "uploaded reference video as the reference" not in result


def test_render_seedance_prompt_includes_timestamped_dialogue():
    result = render_seedance_prompt(
        {
            "storyboard_image": "storyboard_grid.jpg",
            "replacement_target": "none",
            "duration": "14-15 seconds",
            "aspect_ratio": "9:16",
            "audio_mode": "spoken dialogue with original timing",
            "style": "realistic UGC",
            "preserve_rules": "- Preserve gestures",
            "change_rules": "- None",
            "negative_rules": "- Do not summarize dialogue",
            "shot_prompts": "Shot 1: character points at product.",
            "dialogue_timeline": '00:00-00:02 Character says: "Look at this." Tone: excited.',
        }
    )

    assert "## Dialogue Timeline" in result
    assert '00:00-00:02 Character says: "Look at this."' in result
    assert "Sync mouth movement, facial expression, and gestures to the dialogue timing" in result
