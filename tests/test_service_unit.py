import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = ROOT / "deploy"
TEMPLATE = (DEPLOY_DIR / "vibration-meter.service.in").read_text()

# 치환이 안 돼도 통과하지 않도록 pi 가 아닌 값.
REPO_DIR = "/home/nalang/Nalang"
RUN_USER = "nalang"
PLACEHOLDER_RE = re.compile(r"@[A-Z_]+@")


def render(template: str, repo_dir: str, run_user: str) -> str:
    return template.replace("@REPO_DIR@", repo_dir).replace("@RUN_USER@", run_user)


def test_template_contains_neither_home_pi_nor_user_pi():
    assert "/home/pi" not in TEMPLATE
    assert "User=pi" not in TEMPLATE


def test_template_placeholders_are_exactly_repo_dir_and_run_user():
    assert set(PLACEHOLDER_RE.findall(TEMPLATE)) == {"@REPO_DIR@", "@RUN_USER@"}


def test_render_sets_working_directory_pythonpath_and_execstart():
    # User= 만 고치고 경로 세 줄을 남기는 회귀(P-01). 한 단언으로 묶지 않는다.
    lines = render(TEMPLATE, REPO_DIR, RUN_USER).splitlines()
    assert f"WorkingDirectory={REPO_DIR}" in lines
    assert f"Environment=PYTHONPATH={REPO_DIR}/src" in lines
    assert f"ExecStart={REPO_DIR}/.venv/bin/python -m vibration_meter.app" in lines


def test_render_sets_user_and_leaves_no_pi():
    rendered = render(TEMPLATE, REPO_DIR, RUN_USER)
    assert f"User={RUN_USER}" in rendered.splitlines()
    assert "pi" not in rendered


def test_render_leaves_no_placeholders():
    rendered = render(TEMPLATE, REPO_DIR, RUN_USER)
    assert PLACEHOLDER_RE.findall(rendered) == []


def test_render_has_unit_service_and_install_sections():
    rendered = render(TEMPLATE, REPO_DIR, RUN_USER)
    assert "[Unit]" in rendered
    assert "[Service]" in rendered
    assert "[Install]" in rendered


def test_template_has_no_systemd_specifiers():
    # 시스템 스코프에서 %h 는 User= 홈이 아니라 /root 로 풀린다(P-05).
    assert "%h" not in TEMPLATE
    assert "%u" not in TEMPLATE
    assert "%i" not in TEMPLATE


def test_template_sets_syslog_identifier_vibration_meter():
    assert "SyslogIdentifier=vibration-meter" in TEMPLATE


def test_deploy_does_not_contain_rendered_service_file():
    names = {p.name for p in DEPLOY_DIR.iterdir()}
    assert "vibration-meter.service" not in names


def test_install_and_collect_scripts_start_with_posix_sh():
    install = (ROOT / "scripts" / "install-service.sh").read_text()
    collect = (ROOT / "scripts" / "collect-logs.sh").read_text()
    assert install.startswith("#!/bin/sh")
    assert collect.startswith("#!/bin/sh")
