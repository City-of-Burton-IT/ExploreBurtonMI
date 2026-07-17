import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
USES = re.compile(r"^\s*-?\s*uses:\s*[^\s@]+@([^\s#]+)", re.MULTILINE)
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


def test_every_action_is_pinned_to_an_immutable_commit():
    mutable = []
    for workflow in WORKFLOWS:
        for ref in USES.findall(workflow.read_text(encoding="utf-8")):
            if not FULL_SHA.fullmatch(ref):
                mutable.append(f"{workflow.name}: {ref}")
    assert mutable == []


def test_checkout_never_persists_credentials_in_the_worktree():
    missing = []
    for workflow in WORKFLOWS:
        lines = workflow.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if "uses: actions/checkout@" not in line:
                continue
            nearby = "\n".join(lines[index + 1 : index + 5])
            if "persist-credentials: false" not in nearby:
                missing.append(f"{workflow.name}:{index + 1}")
    assert missing == []


def test_shell_run_blocks_never_expand_secrets_as_template_source():
    unsafe = []
    for workflow in WORKFLOWS:
        lines = workflow.read_text(encoding="utf-8").splitlines()
        run_indent = None
        for index, line in enumerate(lines):
            indent = len(line) - len(line.lstrip())
            if run_indent is not None and line.strip() and indent <= run_indent:
                run_indent = None
            if re.match(r"^\s*run:\s*", line):
                run_indent = indent
                if "${{ secrets." in line:
                    unsafe.append(f"{workflow.name}:{index + 1}")
            elif run_indent is not None and "${{ secrets." in line:
                unsafe.append(f"{workflow.name}:{index + 1}")
    assert unsafe == []


def test_every_workflow_declares_explicit_root_permissions():
    missing = []
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")
        if not re.search(r"^permissions:\s*(?:\n|\{)", text, re.MULTILINE):
            missing.append(workflow.name)
    assert missing == []


def test_write_permissions_are_scoped_to_the_jobs_that_use_them():
    for name in ("apply-listing.yml", "deploy.yml"):
        workflow = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert re.search(r"^permissions:\s*\{\}\s*$", workflow, re.MULTILINE)


def test_dependabot_updates_github_actions_pins():
    config = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert 'package-ecosystem: "github-actions"' in config


def test_listing_workflow_never_tracks_unvetted_candidates():
    workflow = (ROOT / ".github" / "workflows" / "apply-listing.yml").read_text(
        encoding="utf-8"
    )
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "pending-additions.json" not in workflow
    assert "tools/pending-additions.json" in gitignore


def test_listing_pr_does_not_depend_on_the_repository_github_token():
    workflow = (ROOT / ".github" / "workflows" / "apply-listing.yml").read_text(
        encoding="utf-8"
    )
    assert "secrets.LISTING_PR_TOKEN" in workflow
    pr_step = workflow.split(
        "- name: Open the review pull request when scoped automation is configured", 1
    )[1]
    assert "GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}" not in pr_step


def test_android_backup_is_disabled():
    root = ET.parse(ROOT / "android" / "app" / "src" / "main" / "AndroidManifest.xml")
    application = root.getroot().find("application")
    assert application is not None
    assert application.get(ANDROID_NS + "allowBackup") == "false"


def test_address_lookup_has_an_accepted_governance_adr_and_public_provenance():
    adr = ROOT / "docs" / "adr" / "ADR-0002-public-address-lookup.md"
    privacy = (ROOT / "public" / "privacy.html").read_text(encoding="utf-8")
    assert adr.exists()
    assert "**Status:** accepted" in adr.read_text(encoding="utf-8")
    assert "assessing situs addresses" in privacy.lower()


def test_public_address_lookup_schema_is_minimized_to_three_value_tuples():
    payload = json.loads((ROOT / "public" / "address-points.json").read_text(encoding="utf-8"))
    assert set(payload) == {"updated", "points"}
    assert payload["points"]
    assert all(
        isinstance(point, list)
        and len(point) == 3
        and isinstance(point[0], (int, float))
        and isinstance(point[1], (int, float))
        and isinstance(point[2], str)
        for point in payload["points"]
    )
