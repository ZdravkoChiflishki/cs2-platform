#!/usr/bin/env bash
set -euo pipefail

python --version
python -c 'import cs2_server, yaml; print("python runtime ok")'
ldconfig -p | grep -E 'libicu' >/dev/null || {
  echo 'libicu not found' >&2
  exit 1
}
command -v rsync >/dev/null
command -v jq >/dev/null
test -x /opt/steamcmd/steamcmd.sh
su -s /bin/sh steam -c '/opt/steamcmd/steamcmd.sh +quit >/dev/null'
