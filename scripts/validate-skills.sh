#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source_dir="${1:-skills}"

if [[ ! -d "$source_dir" ]]; then
  echo "Skills directory not found: $source_dir" >&2
  exit 1
fi

# Always run the self-contained repository validator (works on Codex, Claude Code, Antigravity, and CI).
python3 "$script_dir/validate_skills.py" "$source_dir"

# Also run Codex's quick_validate.py when installed locally for strict schema parity.
codex_validator="${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py"
if [[ -f "$codex_validator" ]]; then
  for skill in "$source_dir"/*; do
    [[ -d "$skill" && -f "$skill/SKILL.md" ]] || continue
    python3 "$codex_validator" "$skill"
  done
fi
