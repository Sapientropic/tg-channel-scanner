from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_mobile_sources_grid_keeps_source_recommendations_area():
    css = (ROOT / "dashboard" / "src" / "styles" / "responsive.css").read_text(encoding="utf-8")

    assert '"source-import"\n      "source-library"\n      "source-recommendations"' in css


def test_profile_matching_cards_do_not_stretch_bullets_into_blank_rows():
    css = (ROOT / "dashboard" / "src" / "styles" / "profiles.css").read_text(encoding="utf-8")

    assert ".profile-match-section,\n.profile-matching-more section {\n  display: grid;\n  align-content: start;" in css
    assert ".profile-match-section ul,\n.profile-matching-more ul {\n  display: grid;\n  align-content: start;" in css


def test_miniapp_source_discovery_stays_compact_before_review_cards():
    css = (ROOT / "dashboard" / "src" / "miniapp.css").read_text(encoding="utf-8")

    assert (
        ".miniapp-source-grid {\n"
        "  display: grid;\n"
        "  gap: 7px;\n"
        "  grid-auto-columns: minmax(190px, 1fr);\n"
        "  grid-auto-flow: column;"
    ) in css
    assert ".miniapp-source-grid {\n    grid-template-columns: minmax(0, 1fr);" not in css


def test_miniapp_learning_loop_stays_compact_on_mobile():
    css = (ROOT / "dashboard" / "src" / "miniapp.css").read_text(encoding="utf-8")

    assert ".miniapp-learning-loop {\n    grid-template-columns: minmax(0, 1fr);" not in css


def test_miniapp_light_effects_are_signal_scoped_and_motion_safe():
    css = (ROOT / "dashboard" / "src" / "miniapp.css").read_text(encoding="utf-8")

    assert ".miniapp-card::after" in css
    assert ".miniapp-card.rating-high::after" in css
    assert ".miniapp-state::after" in css
    assert ".miniapp-learning-next::after" in css
    assert '@media (prefers-reduced-motion: reduce)' in css
    assert ".miniapp-card::after,\n  .miniapp-state::after,\n  .miniapp-note::after,\n  .miniapp-source-discovery::after,\n  .miniapp-learning-next::after" in css


def test_miniapp_learning_copy_and_feedback_effects_stay_readable():
    css = (ROOT / "dashboard" / "src" / "miniapp.css").read_text(encoding="utf-8")

    assert ".miniapp-learning-copy {\n  background: color-mix(in oklch, var(--ink-2) 82%, transparent);" in css
    assert "color: color-mix(in oklch, var(--paper) 76%, var(--muted));" in css
    assert '.miniapp-action[data-review-action="feedback"][data-expanded="true"]' in css
    assert ".miniapp-note::after" in css
    assert "@keyframes feedback-open" in css


def test_miniapp_primary_actions_keep_mobile_touch_target():
    css = (ROOT / "dashboard" / "src" / "miniapp.css").read_text(encoding="utf-8")

    assert ".miniapp-action {\n  align-items: center;" in css
    assert "  min-height: 44px;" in css


def test_miniapp_source_discovery_is_readable_and_stateful():
    css = (ROOT / "dashboard" / "src" / "miniapp.css").read_text(encoding="utf-8")

    assert '.miniapp-source-discovery[data-ready="true"]::after' in css
    assert ".miniapp-source-discovery-head {\n  align-items: stretch;" in css
    assert ".miniapp-source-discovery-head > div {\n  background: color-mix(in oklch, var(--ink-2) 82%, transparent);" in css
    assert ".miniapp-source-badges,\n.miniapp-source-tags {" in css
    assert ".miniapp-source-card strong {\n  color: var(--paper);\n  display: -webkit-box;" in css
    assert ".miniapp-source-tags small {\n  border-color: color-mix(in oklch, var(--paper) 18%, transparent);" in css
