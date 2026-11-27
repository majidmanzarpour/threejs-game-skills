#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: ./install.sh [--codex] [--claude] [--antigravity] [--all] [--agents] [--force] [--prune-managed]

Installs the Three.js game skills from ./skills into local agent skill
directories.

Recommended:
  ./install.sh --codex
  ./install.sh --claude
  ./install.sh --antigravity
  ./install.sh --all

Targets:
  --codex        Install into ${CODEX_HOME:-$HOME/.codex}/skills
  --claude       Install into ${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}
  --antigravity  Install into ${ANTIGRAVITY_SKILLS_DIR:-$HOME/.gemini/config/skills}
  --all          Install into Codex and Claude

Advanced:
  --agents  Install into ${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}
            Only use this for agent surfaces that read .agents/skills without
            also reading Codex or Claude skills, otherwise skills can duplicate.

Options:
  --force          Replace same-named skills in the target directory
  --prune-managed  Remove stale skills recorded in this repo's managed manifest
USAGE
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source_dir="$script_dir/skills"
codex="false"
claude="false"
antigravity="false"
agents="false"
force="false"
prune="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --codex)
      codex="true"
      shift
      ;;
    --claude)
      claude="true"
      shift
      ;;
    --antigravity)
      antigravity="true"
      shift
      ;;
    --all)
      codex="true"
      claude="true"
      shift
      ;;
    --agents)
      agents="true"
      shift
      ;;
    --force)
      force="true"
      shift
      ;;
    --prune-managed)
      prune="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 1
      ;;
  esac
done

if [[ "$codex" != "true" && "$claude" != "true" && "$antigravity" != "true" && "$agents" != "true" ]]; then
  usage
  exit 1
fi

if [[ ! -d "$source_dir" ]]; then
  echo "Source skills directory not found: $source_dir" >&2
  exit 1
fi

copy_skill() {
  local source="$1"
  local dest="$2"

  if command -v rsync >/dev/null 2>&1; then
    rsync -a \
      --exclude '.DS_Store' \
      --exclude '__pycache__/' \
      --exclude 'node_modules/' \
      --exclude 'dist/' \
      --exclude 'artifacts/' \
      --exclude 'test-results/' \
      --exclude 'playwright-report/' \
      --exclude 'coverage/' \
      "$source"/ "$dest"/
  else
    cp -R "$source"/. "$dest"/
    find "$dest" \( \
      -name '.DS_Store' -o \
      -name '__pycache__' -o \
      -name 'node_modules' -o \
      -name 'dist' -o \
      -name 'artifacts' -o \
      -name 'test-results' -o \
      -name 'playwright-report' -o \
      -name 'coverage' \
      \) -prune -exec rm -rf {} +
  fi
}

install_skills() {
  local target="$1"
  local label="$2"
  local manifest="$target/.threejs-game-skills-managed"
  local source_names=" "

  mkdir -p "$target"
  echo "Installing Three.js game skills for $label -> $target"

  for skill in "$source_dir"/*; do
    [[ -d "$skill" && -f "$skill/SKILL.md" ]] || continue
    local skill_name
    skill_name="$(basename "$skill")"
    source_names="$source_names$skill_name "
    local dest="$target/$skill_name"

    if [[ -e "$dest" && "$force" != "true" ]]; then
      echo "Skipping existing skill: $dest"
      continue
    fi

    rm -rf "$dest"
    mkdir -p "$dest"
    copy_skill "$skill" "$dest"
    echo "Installed $skill_name -> $dest"
  done

  if [[ "$prune" == "true" && -f "$manifest" ]]; then
    while IFS= read -r installed_name; do
      [[ -n "$installed_name" ]] || continue
      if [[ "$source_names" != *" $installed_name "* && -d "$target/$installed_name" ]]; then
        rm -rf "$target/$installed_name"
        echo "Pruned stale managed skill: $target/$installed_name"
      fi
    done < "$manifest"
  fi

  for skill in "$source_dir"/*; do
    [[ -d "$skill" && -f "$skill/SKILL.md" ]] || continue
    basename "$skill"
  done | sort > "$manifest"
}

if [[ "$codex" == "true" ]]; then
  install_skills "${CODEX_HOME:-$HOME/.codex}/skills" "Codex"
fi

if [[ "$claude" == "true" ]]; then
  install_skills "${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}" "Claude"
fi

if [[ "$antigravity" == "true" ]]; then
  install_skills "${ANTIGRAVITY_SKILLS_DIR:-$HOME/.gemini/config/skills}" "Antigravity"
fi

if [[ "$agents" == "true" ]]; then
  echo "Warning: --agents can duplicate skills in Codex if Codex also reads ~/.agents/skills." >&2
  install_skills "${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}" ".agents"
fi
