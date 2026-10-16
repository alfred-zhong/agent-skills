#!/usr/bin/env bash
# 把本仓库里的 skill 同步到 ~/.agents/skills/（Kimi Code 的加载目录）
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${SKILLS_DEST:-$HOME/.agents/skills}"

mkdir -p "$DEST"

if [ $# -gt 0 ]; then
  targets=("$@")
else
  targets=()
  for d in "$SRC"/*/; do
    [ -f "$d/SKILL.md" ] && targets+=("$(basename "$d")")
  done
fi

if [ ${#targets[@]} -eq 0 ]; then
  echo "没有找到任何 skill（子目录需含 SKILL.md）" >&2
  exit 1
fi

for name in "${targets[@]}"; do
  if [ ! -f "$SRC/$name/SKILL.md" ]; then
    echo "跳过 $name：$SRC/$name/SKILL.md 不存在" >&2
    continue
  fi
  rsync -a --delete --exclude '__pycache__' --exclude '.DS_Store' \
    "$SRC/$name/" "$DEST/$name/"
  echo "已同步 $name → $DEST/$name"
done

echo
echo "提示：新装的 skill 需要新开会话才会被加载。"
