# Source from any PiTV script:  . "$(dirname "$0")/../lib/env.sh"   (adjust the path)
# Loads pitv.env from the repo root, falling back to pitv.env.example for defaults.
PITV_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a
. "$PITV_ROOT/pitv.env.example"
[ -f "$PITV_ROOT/pitv.env" ] && . "$PITV_ROOT/pitv.env"
set +a
