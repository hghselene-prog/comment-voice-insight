// 高信息密度 Word 报告（横向 A4）
// 用法: node make_docx.js --data <data.json> --insights <insights.json> --out <out.docx>
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, BorderStyle, WidthType, ShadingType, LevelFormat, PageBreak, PageOrientation, VerticalAlign, HeightRule
} = require('docx');

function arg(n, d) { const i = process.argv.indexOf('--' + n); return i > -1 ? process.argv[i + 1] : d; }
const DATA_PATH = arg('data'), INS_PATH = arg('insights'), OUT_PATH = arg('out');
if (!DATA_PATH || !INS_PATH || !OUT_PATH) {
  console.error('用法: node make_docx.js --data <data.json> --insights <insights.json> --out <out.docx>');
  process.exit(1);
}
const D = JSON.parse(fs.readFileSync(DATA_PATH, 'utf-8'));
const INS = JSON.parse(fs.readFileSync(INS_PATH, 'utf-8'));
const META = D.meta || {};

const NAVY='121A2E', ACCENT='E11D2A', POS='16A34A', WATCH='F59E0B', DATA='2563EB';
const INK='1E293B', SLATE='64748B', GREY='64748B', LIGHT='F4F6FA', LINE='E2E8F0';
const PALETTE = { NAVY, ACCENT, POS, WATCH, DATA, INK, SLATE, GREY };
const col = (c) => PALETTE[c] || c || DATA;   // insights 里写 "DATA" 或直接写十六进制都行
const FULL = 14678; // 横向A4 内容宽

const noBorder = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
const cB = { style: BorderStyle.SINGLE, size: 2, color: 'D5DEE8' };
const B = { top: cB, bottom: cB, left: cB, right: cB };
const noB = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

function T(text, o = {}) {
  return new TextRun({ text: String(text), font: 'Microsoft YaHei', size: o.size || 20,
    bold: o.bold || false, color: o.color || INK, italics: o.italics || false });
}
function P(children, o = {}) {
  return new Paragraph({ children: Array.isArray(children) ? children : [children],
    alignment: o.align || AlignmentType.LEFT, spacing: o.spacing || { after: 40, before: 0 },
    ...(o.border ? { border: o.border } : {}),
    ...(o.keepNext ? { keepNext: true, keepLines: true } : {}) });
}
// 实心色条（用表格单元格填色实现，比段落边框在各渲染器下都稳）
function rule(color, w = FULL, h = 24) {
  return new Table({
    width: { size: w, type: WidthType.DXA }, columnWidths: [w], borders: noB,
    rows: [new TableRow({ height: { value: h, rule: HeightRule.EXACT }, children: [
      new TableCell({ borders: noB, width: { size: w, type: WidthType.DXA },
        shading: { fill: color, type: ShadingType.CLEAR },
        margins: { top: 0, bottom: 0, left: 0, right: 0 },
        children: [new Paragraph({ children: [T('', { size: 2 })], spacing: { after: 0, before: 0 } })] })] })],
  });
}
// 左侧彩色竖条卡片
function card(title, color, body, pad = 90) {
  const BAR = 90, BODY = FULL - BAR;
  return new Table({
    width: { size: FULL, type: WidthType.DXA }, columnWidths: [BAR, BODY], borders: noB,
    rows: [new TableRow({ children: [
      new TableCell({ borders: noB, width: { size: BAR, type: WidthType.DXA },
        shading: { fill: color, type: ShadingType.CLEAR },
        margins: { top: 0, bottom: 0, left: 0, right: 0 },
        children: [new Paragraph({ children: [T('', { size: 2 })], spacing: { after: 0, before: 0 } })] }),
      new TableCell({ borders: noB, width: { size: BODY, type: WidthType.DXA },
        shading: { fill: LIGHT, type: ShadingType.CLEAR },
        margins: { top: pad, bottom: pad, left: 180, right: 180 },
        children: [
          new Paragraph({ children: [T(title, { size: 19, bold: true, color })], spacing: { after: 30 }, keepNext: true }),
          new Paragraph({ children: [T(body, { size: 17, color: INK })] }),
        ] }),
    ] })],
  });
}
function C(text, o = {}) {
  return new TableCell({
    borders: o.borders === 'none' ? noB : B,
    width: { size: o.width, type: WidthType.DXA },
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR } : undefined,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({ alignment: o.align || AlignmentType.LEFT,
      children: [T(text, { size: o.size || 18, bold: o.bold || false, color: o.color || INK })] })],
  });
}
function heat(v, mx) {
  if (mx <= 0) return 'F4F6FA';
  const t = Math.pow(Math.min(1, v / mx), 0.62); // gamma 提升低值区对比度
  const r = Math.round(248 + (30 - 248) * t), g = Math.round(250 + (88 - 250) * t), b = Math.round(252 + (230 - 252) * t);
  return [r, g, b].map(x => x.toString(16).padStart(2, '0')).join('');
}
function barRow(label, pct, color, valText) {
  const LBL = 1900, VAL = 2600, barW = 8100, unit = barW / 100;
  const fill = Math.max(1, Math.round(pct * unit)), rest = barW - fill;
  return new Table({
    width: { size: LBL + barW + VAL, type: WidthType.DXA },
    columnWidths: [LBL, fill, rest, VAL], borders: noB,
    rows: [new TableRow({ cantSplit: true, children: [
      C(label, { width: LBL, size: 18, bold: true, borders: 'none' }),
      new TableCell({ borders: noB, width: { size: fill, type: WidthType.DXA },
        shading: { fill: color, type: ShadingType.CLEAR }, margins: { top: 20, bottom: 20, left: 0, right: 0 },
        children: [new Paragraph({ children: [] })] }),
      new TableCell({ borders: noB, width: { size: rest, type: WidthType.DXA },
        shading: { fill: 'FFFFFF', type: ShadingType.CLEAR }, margins: { top: 20, bottom: 20, left: 0, right: 0 },
        children: [new Paragraph({ children: [] })] }),
      C(valText, { width: VAL, size: 18, bold: true, color: SLATE, align: AlignmentType.RIGHT, borders: 'none' }),
    ] })],
  });
}

const ov = D.overview, fn = D.funnel, mx = D.matrix;
const sent = D.sentiment, th = D.themes, seg = D.segments;
const segNames = D.seg_names, themeNames = D.theme_names;
const sentColor = { '玩梗': WATCH, '期待': POS, '中性/陈述': SLATE, '失望': ACCENT, '愤怒': ACCENT, '观望': DATA };
const segColor = { '已购/下单': POS, '强意向': DATA, '观望': WATCH, '劝退/放弃': ACCENT };

const blocks = [];
const H = (t) => {
  blocks.push(P([], { spacing: { after: 120 } }));
  blocks.push(P([T(t, { size: 24, bold: true, color: NAVY })], { spacing: { before: 0, after: 40 }, keepNext: true }));
  blocks.push(rule(NAVY, FULL, 24));
  blocks.push(P([], { spacing: { after: 60 } }));
};

// 标题
blocks.push(P([T(`${META.product || '产品'} · B站评论洞察`, { size: 30, bold: true, color: NAVY })]));
blocks.push(P([T([
  META.bvid ? `数据源 ${META.bvid}` : null,
  META.owner ? `UP主 ${META.owner}` : null,
  META.date ? `分析日期 ${META.date}` : null,
  META.subtitle_method ? `方法：${META.subtitle_method}` : null,
].filter(Boolean).join(' · '), { size: 16, color: SLATE })]));
blocks.push(P([], { spacing: { after: 60 } }));

// KPI
const netPos = fn.net >= 0;
const kpis = [
  [`${ov.rows.toLocaleString()}`, '解析评论（条）', NAVY],
  [`${ov.vol.toLocaleString()}`, '总声量（赞·含转评）', NAVY],
  [`${ov.coverage}%`, ov.coverage_label || '样本覆盖率', DATA],
  ov.conservation != null
    ? [`${ov.conservation}%`, '点赞守恒校验', POS]
    : [`${D.sentiment.length}`, '情绪分类数', POS],
  [`${netPos ? '+' : ''}${fn.net.toLocaleString()}`,
    `意向净值${fn.ratio ? `（声量 ${fn.ratio}:1）` : ''}`, netPos ? POS : ACCENT],
  D.polarity
    ? [`${D.polarity.ratio ?? '—'}:1`, `${D.polarity.label}正负声量比`, WATCH]
    : (D.contrast
        ? [`${D.contrast.ratio ?? '—'}:1`, D.contrast.label, WATCH]
        : [`${th.length}`, '主题维度数', WATCH]),
];
const kpiRows = [];
for (let r = 0; r < 2; r++) {
  const cells = [];
  for (let c = 0; c < 3; c++) {
    const [v, l, col] = kpis[r * 3 + c];
    cells.push(new TableCell({ borders: B, width: { size: 4892, type: WidthType.DXA },
      shading: { fill: LIGHT, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 160, right: 160 },
      children: [ new Paragraph({ children: [T(v, { size: 30, bold: true, color: col })] }),
        new Paragraph({ children: [T(l, { size: 15, color: SLATE })] }) ] }));
  }
  kpiRows.push(new TableRow({ children: cells }));
}
blocks.push(new Table({ width: { size: FULL, type: WidthType.DXA }, columnWidths: [4892, 4892, 4892], rows: kpiRows }));

// 一句话结论
const conclCell = new TableCell({
  borders: B, width: { size: FULL, type: WidthType.DXA }, shading: { fill: NAVY, type: ShadingType.CLEAR },
  margins: { top: 140, bottom: 140, left: 200, right: 200 },
  children: [new Paragraph({ children: [
    T('一句话结论：', { size: 18, bold: true, color: WATCH }),
    T(INS.headline || '（待填写 headline）', { size: 18, color: 'FFFFFF' }),
  ] })],
});
const conclRow = new TableRow({ children: [conclCell] });
blocks.push(new Table({ width: { size: FULL, type: WidthType.DXA }, columnWidths: [FULL], rows: [conclRow] }));


// ① 情绪 + 主题
H('① 情绪结构（按声量）');
const sentMax = Math.max(...sent.map(s => s.vol));
sent.forEach(s => blocks.push(barRow(s.name, s.vol / sentMax * 100, sentColor[s.name] || SLATE, `${s.vol.toLocaleString()}（${s.vol_pct}%）`)));

blocks.push(P([], { spacing: { after: 40 } }));
blocks.push(P([T(`主题声量分布 TOP${th.length}`, { size: 19, bold: true, color: NAVY })], { spacing: { before: 80, after: 40 }, keepNext: true }));
const thMax = Math.max(...th.map(t => t.vol));
th.forEach(t => blocks.push(barRow(t.name, t.vol / thMax * 100, DATA, `${t.vol.toLocaleString()}（${t.vol_pct}%）`)));

// ② 漏斗
H('② 购买意向漏斗（词典粗筛·中置信）');
const segMax = Math.max(...seg.map(s => s.vol));
seg.forEach(s => blocks.push(barRow(s.name, s.vol / segMax * 100, segColor[s.name] || SLATE, `${s.vol.toLocaleString()} 声量 · ${s.cnt} 条 · ${s.vol_pct}%`)));
blocks.push(P([T(`已购+强意向 ${fn.buy_intent_vol.toLocaleString()} 声量 vs 劝退 ${fn.repel_vol.toLocaleString()} 声量 → 净值 ${netPos ? '+' : ''}${fn.net.toLocaleString()}${fn.ratio ? `（约 ${fn.ratio}:1 ${netPos ? '正向' : '负向'}）` : ''}。${INS.funnel_note || ''}`, { size: 16, color: SLATE, italics: true })], { spacing: { before: 60, after: 40 } }));

// ③ 矩阵
H('③ 人群 × 主题 声量矩阵（热力，列内归一）');
const colMax = {}; themeNames.forEach(t => colMax[t] = Math.max(...segNames.map(s => mx[s][t])));
const headCells = [C('人群＼主题', { width: 1300, size: 15, bold: true, fill: NAVY, color: 'FFFFFF' })];
themeNames.forEach(t => headCells.push(C(t, { width: 1030, size: 15, bold: true, fill: NAVY, color: 'FFFFFF', align: AlignmentType.CENTER })));
const mRows = [new TableRow({ children: headCells })];
segNames.forEach(s => {
  const cells = [C(s, { width: 1300, size: 16, bold: true, fill: LIGHT })];
  themeNames.forEach(t => {
    const v = mx[s][t];
    const txt = v > 0 ? v.toLocaleString() : '·';
    const col = heat(v, colMax[t]);
    const fontCol = (colMax[t] > 0 && v / colMax[t] > 0.55) ? 'FFFFFF' : INK;
    cells.push(C(txt, { width: 1030, size: 15, color: fontCol, fill: col, align: AlignmentType.CENTER }));
  });
  mRows.push(new TableRow({ children: cells }));
});
blocks.push(new Table({ width: { size: FULL, type: WidthType.DXA }, columnWidths: [1300, ...themeNames.map(() => 1030)], rows: mRows }));
blocks.push(P([T('单元格=该人群讨论该主题的累计声量；一条评论可跨多主题，故行和大于分群总声量。颜色越深=该主题在该人群中越主导。空白/「·」=几乎无讨论。', { size: 15, color: SLATE, italics: true })], { spacing: { before: 50, after: 40 } }));

// ④ 反直觉结论
const findings = INS.findings || [];
if (findings.length) {
  H(`④ ${findings.length === 3 ? '三大' : ''}反直觉数据结论`);
  findings.forEach(f => {
    blocks.push(card(f.title, col(f.color), f.body, 90));
    blocks.push(P([], { spacing: { after: 60 } }));
  });
}

// ⑤ 高赞引用
H('⑤ 高赞引用（声量加权）');
blocks.push(P([T(`全局 TOP${D.quotes_all.length}`, { size: 18, bold: true, color: NAVY })], { spacing: { before: 40, after: 30 }, keepNext: true }));
D.quotes_all.forEach(q => blocks.push(P([
  T(`${q.vol.toLocaleString()}  `, { size: 17, bold: true, color: ACCENT }),
  T(q.text, { size: 17 }),
], { spacing: { after: 30 } })));
segNames.forEach(s => {
  const qs = D.quotes_seg[s] || [];
  if (!qs.length) return;
  blocks.push(P([T(`${s}（TOP${qs.length}）`, { size: 18, bold: true, color: segColor[s] })], { spacing: { before: 80, after: 30 }, keepNext: true }));
  qs.forEach(q => blocks.push(P([
    T(`${q.vol.toLocaleString()}  `, { size: 17, bold: true, color: ACCENT }),
    T(q.text, { size: 17 }),
  ], { spacing: { after: 30 } })));
});

// ⑥ 分层深挖（items 兼容字符串 / {badge,title,body} 两种写法）
function itemText(it) {
  if (typeof it === 'string') return it;
  const head = [it.title, it.badge ? `（${it.badge}）` : ''].filter(Boolean).join('');
  return head ? `${head}：${it.body || ''}` : (it.body || '');
}
const layers = (INS.layers || []).map(l => [l.title, col(l.color), (l.items || []).map(itemText)]);
if (layers.length) H('⑥ 人群分层深挖');
layers.forEach(([h, c, items]) => {
  const BAR = 70;
  blocks.push(P([], { spacing: { after: 80 } }));
  blocks.push(new Table({
    width: { size: FULL, type: WidthType.DXA }, columnWidths: [BAR, FULL - BAR], borders: noB,
    rows: [new TableRow({ children: [
      new TableCell({ borders: noB, width: { size: BAR, type: WidthType.DXA },
        shading: { fill: c, type: ShadingType.CLEAR }, margins: { top: 0, bottom: 0, left: 0, right: 0 },
        children: [new Paragraph({ children: [T('', { size: 2 })], spacing: { after: 0, before: 0 } })] }),
      new TableCell({ borders: noB, width: { size: FULL - BAR, type: WidthType.DXA },
        margins: { top: 30, bottom: 30, left: 140, right: 0 }, verticalAlign: VerticalAlign.CENTER,
        children: [new Paragraph({ children: [T(h, { size: 19, bold: true, color: c })],
          spacing: { after: 0, before: 0 }, keepNext: true })] }),
    ] })],
  }));
  blocks.push(P([], { spacing: { after: 40 } }));
  items.forEach(it => blocks.push(P([T('• ' + it, { size: 17 })], { spacing: { after: 24 } })));
});

// ⑦ 改进点
const improves = INS.improvements || [];
if (improves.length) {
  H('⑦ 改进点路线图');
  improves.forEach(im => {
    blocks.push(card(im.title, col(im.color), im.body, 80));
    blocks.push(P([], { spacing: { after: 50 } }));
  });
}

// 方法论
blocks.push(P([], { spacing: { after: 40 } }));
blocks.push(new Table({ width: { size: FULL, type: WidthType.DXA }, columnWidths: [FULL], rows: [new TableRow({ children: [
  new TableCell({ borders: B, width: { size: FULL, type: WidthType.DXA },
    margins: { top: 120, bottom: 120, left: 180, right: 180 },
    children: [
      new Paragraph({ children: [T('方法论与数据说明', { size: 18, bold: true, color: NAVY })], spacing: { after: 40 } }),
      new Paragraph({ children: [T(INS.confidence_note || '分群与主题均用词典粗筛，属「中置信」：方向与量级可用，精确百分比谨慎参考。', { size: 16, color: SLATE })] }),
      new Paragraph({ children: [T(`口径：声量=累计点赞（含转评）；仅含有点赞的评论参与声量加权，缺失点赞的评论参与定性分析但不计入声量。共解析 ${ov.rows.toLocaleString()} 条 / ${ov.vol.toLocaleString()} 声量${ov.conservation != null ? `，点赞守恒校验 ${ov.conservation}%` : ''}，${ov.coverage_label || '样本覆盖率'} ${ov.coverage}%。主题可多命中（不互斥），故主题声量之和大于总声量；分群唯一分配，优先级 已购 > 强意向 > 劝退 > 观望。`, { size: 16, color: SLATE })], spacing: { before: 40 } }),
    ] }) ] }) ] }));

// ---------- 组装文档 ----------
const doc = new Document({
  styles: { default: { document: { run: { font: 'Microsoft YaHei', size: 20 } } } },
  sections: [{
    properties: {
      page: { size: { width: 11906, height: 16838, orientation: PageOrientation.LANDSCAPE },
        margin: { top: 1080, right: 1080, bottom: 900, left: 1080 } },
    },
    children: blocks,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(OUT_PATH, buf);
  console.log(`✅ Word 完成 → ${OUT_PATH}（${(buf.length / 1024).toFixed(1)} KB）`);
});
