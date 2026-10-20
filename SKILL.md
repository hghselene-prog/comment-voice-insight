---
name: bili-comment-insight
description: 把 B 站评论（Word/CSV 导出）变成四件套洞察成品——高信息密度 Word 报告、决策用 PPT、网页版 HTML、微信可分享长图。用于新品发布后的用户声音分析、竞品评论调研、产品改进点提炼。关键词：B站评论、评论分析、声量、用户洞察、评论报告、弹幕评论、产品口碑、新品反馈。
---

# B站评论洞察四件套

把一份评论导出，变成能直接进汇报的四个成品。

## 何时用

用户给了 B 站评论（Word 复制稿 / CSV / JSON），想要分析报告、PPT、口碑洞察、用户分层、改进建议。

## 四件产出

| 文件 | 用途 |
|---|---|
| `<产品>_评论洞察_高密度报告.docx` | 横向 A4 Word，可编辑，给深度阅读者 |
| `<产品>_评论洞察.pptx` | 16:9 九页，给决策会 |
| `<产品>_评论洞察.html` | 单文件自包含，可托管可直发 |
| `<产品>_评论洞察_长图.png` + `.pdf` | 微信分享 |

## 核心分工（必读）

这套流程**只有两件事需要动脑，其余全是脚本**：

| 层 | 内容 | 谁做 |
|---|---|---|
| 机械层 | 解析、去重、统计、渲染 | 脚本，别手动改数字 |
| **判断层** | **词典定制 + 洞察撰写** | **你（每次都得重做）** |

判断层产物固化为两个文件：`config.json`（三套词典）+ `insights.json`（洞察文本）。
**四个渲染器共用同一份 `_report_data.json`**，所以四件套的数字天然一致——绝不要在渲染脚本里手写数字。

## 执行流程

### 0. 建工作目录

```bash
SKILL=~/.codebuddy/skills/bili-comment-insight
WORK=/workspace/<项目名>            # 例：/workspace/bili-xiaomi17
mkdir -p $WORK && cd $WORK
```

### 1. 解析 → CSV

```bash
python3 $SKILL/scripts/parse_docx.py <评论.docx> \
  --bvid BVxxx --title "<视频标题>" --owner "<UP主>"
```

非 Word 输入（CSV/JSON）可跳过，但需确保有 `content` 列。

### 2. 清洗

```bash
python3 $SKILL/scripts/prep.py <上一步的csv>
# 产出 reports/_clean_<时间戳>.csv 与 _digest_<时间戳>.md
```

把 `_clean_*.csv` 拷到 `$WORK/` 下。

### 3. 起草词典 → `config.json`

```bash
python3 $SKILL/scripts/suggest_config.py --csv $WORK/_clean_*.csv
```

**读完输出的高频词和高赞长评**，然后基于 `templates/config.example.json` 写 `$WORK/config.json`。

关键判断（做不好这步，后面全废）：
- `themes` 必须按**这个品类**定制。分析汽车却用平板的「芯片/生态」词典 = 垃圾结果。
- `sentiment.玩梗` 要填**这条视频实际在玩的梗**，否则梗评论全被误判成中性。
- `intent.观望` 词典要写最厚，它是漏斗里最大也最模糊的一层。
- `contrast` / `polarity` 可选，但它们是产出「反直觉结论」的主要弹药，尽量配。

### 4. 读 digest，写 `insights.json`

**这一步是整套流程的价值所在，不能跳、不能套模板。**

先跑一遍数据层看真实数字：

```bash
python3 $SKILL/scripts/build_data.py --csv $WORK/_clean_*.csv \
  --config $WORK/config.json --out $WORK/_report_data.json
```

然后**通读 `_digest_*.md` 的高赞评论**，基于 `templates/insights.example.json` 写 `$WORK/insights.json`。

写作铁律：
- 每个数字必须能在 `_report_data.json` 里查到出处。**查不到出处的结论直接删**，不要估算。
- `findings` 挑**算出来跟直觉相反**的（比如"以为在吵价格，实际价格只占 6%"）。不反直觉的不配叫 finding。
- 引用高赞原话时带上赞数，这是说服力来源。
- `layers` 最多 3 层，每层 3-4 条（3 条排大卡，4 条排 2×2）。
- 别写"提升用户体验"这种正确的废话，`improvements` 要能直接进需求池。

### 5. 一键出四件套

```bash
bash $SKILL/scripts/run_all.sh $WORK <产品短名>
# 产出全部落在 $WORK/outputs/
```

单独重跑某一件时用 `scripts/` 下对应脚本，参数见文件头注释。

### 6. 质检（不要跳过）

```bash
cp $WORK/outputs/<产品短名>_评论洞察_高密度报告.docx /tmp/qa.docx
soffice --headless -env:UserInstallation=file:///tmp/lo_qa \
  --convert-to pdf --outdir /tmp/qa /tmp/qa.docx
pdftoppm -png -r 100 /tmp/qa/qa.pdf /tmp/qa/p
```

然后**逐张看渲染图**（可派 subagent 做视觉质检）。重点查：中文有无豆腐块、条形图长度是否有区分、热力矩阵深浅梯度、表格是否溢出、标题与正文是否跨页分离。

PPT 同理：`soffice --convert-to pdf <pptx>`。

## 数据口径（写进报告，别改）

- **声量** = 累计点赞（含转评）。仅「点赞缺失==0」的行参与声量计算。
- **条数** = 全部未剔除行，用于定性描述。
- 主题**可多命中**（不互斥）→ 主题声量之和 > 总声量，这是预期行为，不是 bug。
- 分群**唯一分配**，优先级 已购 > 强意向 > 劝退 > 观望。
- B 站 App 复制稿约 **42% 评论缺点赞行**，是导出特性不是解析丢失。覆盖率 20% 左右属正常，必须在报告里写明。
- 词典粗筛属**中置信**：方向和量级可用，精确百分比要标注谨慎参考。

## 踩过的坑

| 症状 | 原因 / 解法 |
|---|---|
| soffice 报 `source file could not be loaded`，任何 docx 都打不开 | 沙盒没装 Writer 模块。`apt-get install -y libreoffice-writer` |
| Word 里段落 `border` 画的横线/竖条不显示 | LibreOffice 对段落边框支持不稳。已改用**填色表格单元格**模拟（`rule()` / `card()`），别改回去 |
| pptxgenjs 柱状图全绿、`chartColors` 不生效 | LibreOffice 渲染 bug。数据量小时**改用手绘表格**（addShape + addText），别用 addChart |
| soffice 中文文件名报错 | 先 `cp` 到 `/tmp/ascii.docx` 再转 |
| `pkill -f soffice` 把当前 shell 也杀了 | 别用 pkill，改用不同的 `-env:UserInstallation=file:///tmp/lo_xxx` 配置目录 |
| ShareLink 工具 403 | 环境限制。改交付长图 + PDF |
| 长图超 10MB 被微信压缩 | `make_longimg.py --dpi 120` |

## 文件清单

```
scripts/
  parse_docx.py      B站App Word复制稿 → CSV
  prep.py            去重/水军过滤/噪声剔除/声量统计
  suggest_config.py  扫高频词，给定制词典当原料
  build_data.py      CSV + config → _report_data.json（唯一数据源）
  make_docx.js       → Word（横向A4）
  make_pptx.js       → PPT（16:9 九页）
  build_html.py      → HTML（自包含单文件）
  make_longimg.py    HTML → 长图 PNG + PDF
  run_all.sh         2~5 步一键编排
templates/
  config.example.json    词典配置模板（含定制要点注释）
  insights.example.json  洞察文本模板（含写作要求注释）
```

依赖：`pandas` `python-docx` `weasyprint` `pillow`（pip）/ `docx` `pptxgenjs`（npm）/ `libreoffice-writer` `poppler-utils`（apt）
