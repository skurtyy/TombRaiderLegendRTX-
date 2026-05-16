from linear.parse_changelog import _classify_line, parse_changelog


def test_classify_line_per_build():
    # Matching build number
    assert _classify_line("- Build 077: FIXED", "unknown", 77) == "pass"
    assert _classify_line("Build 077: FAIL", "unknown", 77) == "fail"
    assert _classify_line("Build 77: working", "fail", 77) == "pass"

    # Non-matching build number (result is unchanged)
    assert _classify_line("- Build 076: FAIL", "unknown", 77) == "unknown"
    assert _classify_line("- Build 076: FIXED", "pass", 77) == "pass"


def test_classify_line_general():
    # Pass words
    assert _classify_line("the lights are fixed now", "unknown", 77) == "pass"
    assert _classify_line("confirmed stable", "unknown", 77) == "pass"

    # Fail words - exact match required as lowercase
    assert _classify_line("black screen occurs", "unknown", 77) == "fail"
    assert _classify_line("this is a regression", "pass", 77) == "fail"

    # Crash handling
    assert _classify_line("it will crash", "unknown", 77) == "fail"
    assert _classify_line("no crash observed", "unknown", 77) == "unknown"
    assert _classify_line("crash guard engaged", "unknown", 77) == "unknown"

    # Sticky fail (if it's already fail, pass words don't override unless it's a per-build specific match)
    assert _classify_line("the lights are fixed now", "fail", 77) == "fail"


def test_parse_changelog(tmp_path):
    log_content = """# Changelog

## [2026-04-13] BUILDS-076-077 -- title
Some general context.
- Build 076: FAIL
- Build 077: FIXED
Hit a dead-end trying to do this.
Found a blocker here.

## [2026-04-14] BUILD-078 -- another title
The game works great, confirmed.
Wait, a regression happened.

## TERRAIN-ANALYSIS
This is not a build.
"""
    log_file = tmp_path / "CHANGELOG.md"
    log_file.write_text(log_content, encoding="utf-8")

    builds = parse_changelog(str(log_file))

    assert len(builds) == 2

    b77 = builds[0]
    assert b77["build"] == 77
    assert b77["result"] == "pass"
    assert len(b77["dead_ends"]) == 1
    assert "dead-end" in b77["dead_ends"][0].lower()
    assert len(b77["blockers"]) == 1
    assert "blocker" in b77["blockers"][0].lower()
    # It parses 6 lines including the blank line before the next heading
    assert len(b77["lines"]) == 6

    b78 = builds[1]
    assert b78["build"] == 78
    assert (
        b78["result"] == "fail"
    )  # It was pass due to 'confirmed', but then 'regression' made it sticky fail
    assert len(b78["dead_ends"]) == 0
    assert len(b78["blockers"]) == 0
    assert len(b78["lines"]) == 3  # 2 text lines + 1 blank line before TERRAIN-ANALYSIS
