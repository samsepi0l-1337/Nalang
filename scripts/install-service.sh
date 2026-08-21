#!/bin/sh
set -eu

UNIT=vibration-meter
DEST=/etc/systemd/system/vibration-meter.service
JOURNAL_LINES=200

# sudo 아래 id -un 은 root 가 된다. SUDO_USER 가 실제 실행 사용자다.
RUN_USER="${RUN_USER:-${SUDO_USER:-$(id -un)}}"
REPO_DIR="${REPO_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"

fail() {
	echo "[$1] FAIL $2 | HINT $3" >&2
	exit 1
}

warn() {
	echo "[$1] FAIL $2 | HINT $3" >&2
}

has_group() {
	printf '%s\n' "$1" | tr ' ' '\n' | grep -qx "$2"
}

if [ "$RUN_USER" = root ] && [ "${ALLOW_ROOT:-}" != 1 ]; then
	fail USER "User=root 는 저장소 소유자와 어긋난다" \
		"ALLOW_ROOT=1 로만 통과한다. sudo 로 부르면 SUDO_USER 를 쓴다"
fi

case "$REPO_DIR" in
*'|'*)
	fail RENDER "REPO_DIR 에 | 가 있다" "sed 구분자와 충돌한다"
	;;
*'
'*)
	fail RENDER "REPO_DIR 에 개행이 있다" "sed 구분자와 충돌한다"
	;;
esac

case "$RUN_USER" in
*'|'*)
	fail RENDER "RUN_USER 에 | 가 있다" "sed 구분자와 충돌한다"
	;;
*'
'*)
	fail RENDER "RUN_USER 에 개행이 있다" "sed 구분자와 충돌한다"
	;;
esac

if [ ! -x "$REPO_DIR/.venv/bin/python" ]; then
	fail VENV "$REPO_DIR/.venv/bin/python 이 없다" \
		"python3 -m venv \"$REPO_DIR/.venv\" && \"$REPO_DIR/.venv/bin/pip\" install -r \"$REPO_DIR/requirements-pi.txt\""
fi

user_groups=$(id -nG "$RUN_USER")
missing=
for group in spi i2c gpio; do
	if ! has_group "$user_groups" "$group"; then
		missing="${missing:+$missing,}$group"
	fi
done
if [ -n "$missing" ]; then
	fail GROUP "$RUN_USER 에 $missing 그룹이 없다" \
		"sudo usermod -aG $missing $RUN_USER 후 재로그인한다. usermod 는 현재 셸에 즉시 반영되지 않는다"
fi

# adm 은 저널을 읽는 권한이라 서비스 기동과 무관하다. 설치는 막지 않는다.
can_read_journal=1
if ! has_group "$user_groups" adm && ! has_group "$user_groups" systemd-journal; then
	can_read_journal=0
	warn JOURNAL "$RUN_USER 가 adm 또는 systemd-journal 에 없다" \
		"sudo usermod -aG adm $RUN_USER 후 재로그인. 지금은 sudo journalctl -u $UNIT -n $JOURNAL_LINES --no-pager"
fi

template="$REPO_DIR/deploy/vibration-meter.service.in"
if [ ! -f "$template" ]; then
	fail RENDER "$template 이 없다" "저장소의 deploy/vibration-meter.service.in 을 확인한다"
fi

rendered=$(mktemp "${TMPDIR:-/tmp}/vibration-meter.XXXXXX")
trap 'rm -f "$rendered"' EXIT

sed -e "s|@REPO_DIR@|$REPO_DIR|g" -e "s|@RUN_USER@|$RUN_USER|g" "$template" >"$rendered"

# grep -c 는 0건이면 종료 코드 1 이라 set -e 에서 끊긴다.
leftover=$(grep -c '@[A-Z_]*@' "$rendered" || true)
if [ "$leftover" -ne 0 ]; then
	fail RENDER "자리표시자가 ${leftover}개 남았다" \
		"$template 의 @이름@ 가 sed 치환과 맞는지 확인한다"
fi

sudo cp "$rendered" "$DEST"
sudo systemctl daemon-reload
sudo systemctl enable --now "$UNIT"
sudo systemctl cat "$UNIT"

if [ "$can_read_journal" -eq 1 ]; then
	echo "journalctl -u $UNIT -n $JOURNAL_LINES --no-pager"
else
	echo "sudo journalctl -u $UNIT -n $JOURNAL_LINES --no-pager"
fi
