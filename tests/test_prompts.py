from dsstar.prompts import coder_prompt


def test_coder_prompt_includes_propose_dir_rules() -> None:
    prompt = coder_prompt(
        question="q",
        descriptions={},
        plan=[],
        next_step={"id": 1, "title": "t", "details": "d", "status": "todo"},
        previous_code=None,
        last_exec=None,
    )

    assert "DSSTAR_PROPOSE_DIR" in prompt
    assert "Do not modify any file under DSSTAR_REPO_ROOT" in prompt
    assert "README.md" in prompt
