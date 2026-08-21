import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install-service.sh"

# 가드는 모두 sudo 앞에서 끝난다. 아래 케이스는 systemd 를 건드리지 않는다.


def run(repo_dir: str, run_user: str, allow_root: str | None = None):
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "REPO_DIR": repo_dir, "RUN_USER": run_user}
    if allow_root is not None:
        env["ALLOW_ROOT"] = allow_root
    return subprocess.run(
        ["sh", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=30
    )


def fake_repo(tmp_path: Path) -> Path:
    python = tmp_path / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n")
    python.chmod(0o755)
    return tmp_path


def test_repo_dir_with_space_is_rejected(tmp_path):
    # systemd 가 ExecStart 를 공백으로 쪼개 실행 파일이 첫 공백 앞에서 잘린다.
    result = run(str(fake_repo(tmp_path)) + "/foo bar", "nalang")
    assert result.returncode == 1
    assert "[RENDER] FAIL" in result.stderr
    assert "공백" in result.stderr


def test_run_user_with_space_is_rejected(tmp_path):
    result = run(str(fake_repo(tmp_path)), "na lang")
    assert result.returncode == 1
    assert "[RENDER] FAIL" in result.stderr


def test_repo_dir_with_sed_delimiter_is_rejected(tmp_path):
    result = run(str(fake_repo(tmp_path)) + "/a|b", "nalang")
    assert result.returncode == 1
    assert "[RENDER] FAIL" in result.stderr


def test_root_is_rejected_without_allow_root(tmp_path):
    # sudo 아래 id -un 이 root 가 되면 유닛의 User= 와 저장소 소유자가 어긋난다.
    result = run(str(fake_repo(tmp_path)), "root")
    assert result.returncode == 1
    assert "[USER] FAIL" in result.stderr


def test_missing_venv_is_rejected(tmp_path):
    result = run(str(tmp_path), "nalang")
    assert result.returncode == 1
    assert "[VENV] FAIL" in result.stderr


def test_unknown_account_fails_with_stage_line(tmp_path):
    # id -nG 가 그냥 죽으면 [STAGE] FAIL 없이 raw 에러만 남는다.
    result = run(str(fake_repo(tmp_path)), "no-such-account-xyzzy")
    assert result.returncode == 1
    assert "[USER] FAIL" in result.stderr
    assert "계정이 없다" in result.stderr
