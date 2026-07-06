#!/usr/bin/env bash
set -euo pipefail

# Prints exactly one line per key in the form KEY=SET or KEY=MISSING.
# The literal MISSING token is a contract: skill skip rules and
# audit_reference_report.py blocker detection grep for it.
PROBE_SNIPPET='
  report_key() {
    if [ -n "${2:-}" ]; then
      printf "%s=SET\n" "$1"
    else
      printf "%s=MISSING\n" "$1"
    fi
  }
  report_key TRIPO_API_KEY "${TRIPO_API_KEY:-}"
  report_key GEMINI_API_KEY "${GEMINI_API_KEY:-}"
  report_key ELEVENLABS_API_KEY "${ELEVENLABS_API_KEY:-}"
'

if command -v zsh >/dev/null 2>&1; then
  zsh -lc '
    source "$HOME/.zprofile" >/dev/null 2>&1 || true
    source "$HOME/.zshrc" >/dev/null 2>&1 || true
    '"$PROBE_SNIPPET"
else
  bash -lc '
    source "$HOME/.bash_profile" >/dev/null 2>&1 || true
    source "$HOME/.bashrc" >/dev/null 2>&1 || true
    '"$PROBE_SNIPPET"
fi
