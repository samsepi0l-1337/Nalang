#!/bin/sh
set -eu

UNIT=vibration-meter
LINES=200
fail_only=0

for arg in "$@"; do
	case "$arg" in
	--fail-only)
		fail_only=1
		;;
	*)
		echo "usage: $0 [--fail-only]" >&2
		exit 1
		;;
	esac
done

emit() {
	if [ "$fail_only" -eq 1 ]; then
		grep '\] FAIL ' || true
	else
		cat
	fi
}

if systemctl cat "$UNIT" >/dev/null 2>&1; then
	logs=$(journalctl -u "$UNIT" -n "$LINES" --no-pager 2>/dev/null || true)
	if [ -z "$logs" ]; then
		echo "[JOURNAL] FAIL journalctl -u $UNIT 결과가 비었다 | HINT adm 그룹. 지금은 sudo journalctl -u $UNIT -n $LINES --no-pager. 영구 해결: sudo usermod -aG adm \$USER 후 재로그인" >&2
		logs=$(sudo journalctl -u "$UNIT" -n "$LINES" --no-pager)
	fi
else
	logs=$(journalctl -t "$UNIT" -n "$LINES" --no-pager)
fi

if [ -n "$logs" ]; then
	printf '%s\n' "$logs" | emit
fi
