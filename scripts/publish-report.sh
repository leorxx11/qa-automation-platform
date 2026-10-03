#!/usr/bin/env bash
# 发布 Allure 报告到 Web 托管目录：
#   <REPORT_ROOT>/<run_id>/   每次运行独立一份
#   <REPORT_ROOT>/latest      指向最新一次的符号链接（原子切换）
# 并只保留最近 KEEP_REPORTS 份，旧的自动清理。
#
# 用法: publish-report.sh <报告目录> <run_id>
set -euo pipefail

SRC="${1:?缺少报告目录}"
RUN_ID="${2:?缺少 run_id}"
ROOT="${REPORT_ROOT:-/srv/allure-reports}"
KEEP="${KEEP_REPORTS:-20}"

[[ "$RUN_ID" =~ ^[0-9A-Za-z._-]+$ ]] || { echo "非法 run_id: $RUN_ID" >&2; exit 1; }
[ -f "$SRC/index.html" ] || { echo "$SRC 不是有效的 Allure 报告" >&2; exit 1; }

dest="$ROOT/$RUN_ID"
rm -rf "$dest.tmp"
cp -r "$SRC" "$dest.tmp"
rm -rf "$dest"
mv "$dest.tmp" "$dest"

# 先建临时链接再 rename，避免 latest 出现短暂不可用
ln -sfn "$RUN_ID" "$ROOT/.latest.tmp"
mv -Tf "$ROOT/.latest.tmp" "$ROOT/latest"

# 只统计真实目录（不含 latest 链接），按修改时间保留最新的 KEEP 份
find "$ROOT" -mindepth 1 -maxdepth 1 -type d ! -name '*.tmp' -printf '%T@ %f\n' \
  | sort -rn | tail -n +"$((KEEP + 1))" | cut -d' ' -f2- \
  | while read -r old; do
      echo "清理旧报告: $old"
      rm -rf -- "${ROOT:?}/$old"
    done

echo "报告已发布: $dest"
