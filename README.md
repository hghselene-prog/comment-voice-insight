# comment-voice-insight

> 把 B 站评论（Word / CSV / JSON 导出）变成四件套洞察成品——高密度 Word 报告、决策用 PPT、网页版 HTML、微信可分享长图。

**完整文档请阅读 [`SKILL.md`](./SKILL.md)**——那是这套流水线的唯一权威说明（何时用、四件产出、判断层与机械层的分工、执行流程、词典定制方法、洞察撰写口径）。

## 一句话介绍

用户给一份评论导出（Word 复制稿、CSV 或 JSON），这个 skill 跑一遍流水线，产出可汇报的四件套：
- `<产品>_评论洞察_高密度报告.docx` —— 横向 A4 Word 深度阅读版
- `<产品>_评论洞察.pptx` —— 16:9 九页决策版
- `<产品>_评论洞察.html` —— 单文件自包含网页版
- `<产品>_评论洞察_长图.png` + `.pdf` —— 微信分享长图

典型用法：新品发布后的用户声音分析、竞品评论调研、产品改进点提炼。

## 仓库结构

```
.
├── SKILL.md                 # 唯一权威文档（必读）
├── README.md                # 你正在看的
├── .gitignore
├── scripts/                 # 机械层：所有跑流水线的脚本
│   ├── parse_docx.py        # Word 复制稿 → CSV
│   ├── prep.py              # CSV 清洗 → _clean_*.csv + _digest_*.md
│   ├── suggest_config.py    # 草拟词典初稿
│   ├── build_data.py        # config + clean.csv → _report_data.json
│   ├── build_html.py        # _report_data.json + insights.json → HTML
│   ├── make_docx.js         # → Word
│   ├── make_pptx.js         # → PPT
│   ├── make_longimg.py      # → 长图 + PDF
│   ├── run_all.sh           # 一键跑完出四件套
│   ├── package.json         # Node 依赖声明
│   └── package-lock.json
└── templates/
    ├── config.example.json    # 词典配置示例
    └── insights.example.json  # 洞察 JSON 示例
```

## 快速开始

> 第一次跑需要先装 Node 依赖：`cd scripts && npm install`

```bash
# 1) 把评论放进 data/ 目录（B站 API 抓取 / Word 导出 / CSV 都可）
# 2) 跑清洗
python3 scripts/prep.py data/raw.csv --out _digest.md

# 3) 定制 config.json（词典）与 insights.json（洞察文本）
cp templates/config.example.json    config.json
cp templates/insights.example.json  insights.json
#  ← 编辑这两个文件，改完再跑下一步

# 4) 一键出四件套
bash scripts/run_all.sh . MyProduct
```

## 核心理念

**只有两件事需要动脑，其余全是脚本。**

| 层 | 谁做 | 内容 |
|---|---|---|
| 机械层 | 脚本 | 解析、去重、统计、渲染——别手动改数字 |
| 判断层 | 你（每次重做） | 词典定制 + 洞察撰写 |

四个渲染器共用同一份 `_report_data.json`，所以 PPT/Word/HTML/长图里的数字天然一致。

## 许可证

仅作个人/团队内部使用，未附带开源许可证。