#!/usr/bin/env bash
# 一键出四件套：Word / PPT / HTML / 长图
# 用法: ./run_all.sh <工作目录> <产品短名>
#   工作目录须已存在 config.json、insights.json、_clean_*.csv
set -euo pipefail

WORK="${1:?用法: run_all.sh <工作目录> <产品短名>}"
NAME="${2:?用法: run_all.sh <工作目录> <产品短名>}"
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$WORK/outputs"
mkdir -p "$OUT"

# 渲染器依赖自包含在 skill 内，换机器/新沙盒时自动补装
if [ ! -d "$SKILL_DIR/node_modules/docx" ] || [ ! -d "$SKILL_DIR/node_modules/pptxgenjs" ]; then
  echo "── 首次运行，安装 Node 依赖 ──"
  (cd "$SKILL_DIR" && npm install --silent --no-fund --no-audit)
fi

CSV=$(ls -t "$WORK"/_clean_*.csv 2>/dev/null | head -1)
[ -z "$CSV" ] && { echo "❌ 找不到 _clean_*.csv，请先跑 prep.py"; exit 1; }
for f in config.json insights.json; do
  [ -f "$WORK/$f" ] || { echo "❌ 缺少 $WORK/$f"; exit 1; }
done

echo "── 1/5 数据层 ────────────────────────────"
python3 "$SKILL_DIR/build_data.py" --csv "$CSV" \
  --config "$WORK/config.json" --out "$WORK/_report_data.json"

echo "── 2/5 Word ─────────────────────────────"
node "$SKILL_DIR/make_docx.js" --data "$WORK/_report_data.json" \
  --insights "$WORK/insights.json" --out "$OUT/${NAME}_评论洞察_高密度报告.docx"

echo "── 3/5 PPT ──────────────────────────────"
node "$SKILL_DIR/make_pptx.js" --data "$WORK/_report_data.json" \
  --insights "$WORK/insights.json" --out "$OUT/${NAME}_评论洞察.pptx"

echo "── 4/5 HTML ─────────────────────────────"
python3 "$SKILL_DIR/build_html.py" --data "$WORK/_report_data.json" \
  --insights "$WORK/insights.json" --out "$OUT/${NAME}_评论洞察.html"

echo "── 5/5 长图 + PDF ───────────────────────"
python3 "$SKILL_DIR/make_longimg.py" --html "$OUT/${NAME}_评论洞察.html" \
  --out-img "$OUT/${NAME}_评论洞察_长图.png" --out-pdf "$OUT/${NAME}_评论洞察.pdf"

echo
echo "✅ 四件套完成 → $OUT"
ls -lh "$OUT" | tail -n +2 | awk '{printf "   %-52s %s\n", $9, $5}'
