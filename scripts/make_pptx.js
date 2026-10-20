// 决策用 PPT（16:9，9 页）
// 用法: node make_pptx.js --data <data.json> --insights <insights.json> --out <out.pptx>
const fs = require("fs");
const pptxgen = require("pptxgenjs");

function arg(n, d) { const i = process.argv.indexOf("--" + n); return i > -1 ? process.argv[i + 1] : d; }
const DATA_PATH = arg("data"), INS_PATH = arg("insights"), OUT_PATH = arg("out");
if (!DATA_PATH || !INS_PATH || !OUT_PATH) {
  console.error("用法: node make_pptx.js --data <data.json> --insights <insights.json> --out <out.pptx>");
  process.exit(1);
}
const D = JSON.parse(fs.readFileSync(DATA_PATH, "utf-8"));
const INS = JSON.parse(fs.readFileSync(INS_PATH, "utf-8"));
const M = D.meta || {};
const fmt = (n) => Number(n).toLocaleString();

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "B站评论分析工具";
pres.title = `${M.product || "产品"} 评论区洞察`;

const FONT = "Noto Sans CJK SC";
const FONT_H = "Noto Serif CJK SC";

// ---- palette ----
const NAVY = "121A2E";
const NAVY2 = "1B2540";
const INK = "1E293B";
const SLATE = "64748B";
const LIGHT = "F4F6FA";
const WHITE = "FFFFFF";
const ACCENT = "E11D2A";   // 全局强调 / 未购阻力
const POS = "16A34A";     // 已购 / 正向
const WATCH = "F59E0B";   // 观望
const DATA = "2563EB";    // 声量数据
const LINE = "E2E8F0";
const GREY = "64748B";

const makeShadow = () => ({ type: "outer", color: "000000", blur: 7, offset: 3, angle: 135, opacity: 0.12 });

const PALETTE = { NAVY, ACCENT, POS, WATCH, DATA, INK, SLATE, GREY };
const col = (c) => PALETTE[c] || c || DATA;
const SENT_COLOR = { "玩梗": GREY, "中性/陈述": "94A3B8", "期待": POS, "失望": WATCH, "愤怒": ACCENT, "观望": DATA };
const SEG_COLOR = { "已购/下单": POS, "强意向": DATA, "观望": WATCH, "劝退/放弃": ACCENT };
const FOOT = [`${M.product || "产品"} · B站评论区洞察`,
  M.bvid ? `数据来源 ${M.bvid}${M.owner ? `（${M.owner}）` : ""}` : null, M.date]
  .filter(Boolean).join("  |  ");

function footer(slide, dark) {
  slide.addText(FOOT, {
    x: 0.5, y: 5.34, w: 9, h: 0.25, fontFace: FONT, fontSize: 8.5,
    color: dark ? "8A94A8" : "94A3B8", align: "left", margin: 0,
  });
}

// 卡片：圆角白卡 + 装饰色点 + 徽标(kicker) + 标题 + 正文
// 约定：圆形只作装饰色点，绝不在圆内塞字（避免数字/文字混排）；
// badge 作为圆点右侧的 kicker 呈现，可为序号或短标签。
function card(slide, x, y, w, h, badge, title, body, badgeColor) {
  const dot = 0.42;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, fill: { color: WHITE }, line: { color: LINE, width: 1 },
    rectRadius: 0.09, shadow: makeShadow(),
  });
  slide.addShape(pres.shapes.OVAL, { x: x + 0.2, y: y + 0.22, w: dot, h: dot, fill: { color: badgeColor } });
  if (badge) slide.addText(badge, {
    x: x + 0.2 + dot + 0.12, y: y + 0.14, w: w - 0.2 - dot - 0.3, h: dot + 0.12,
    align: "left", valign: "middle", fontFace: FONT_H, fontSize: 11.5, bold: true,
    color: badgeColor, margin: 0,
  });
  slide.addText(title, {
    x: x + 0.22, y: y + 0.72, w: w - 0.44, h: 0.4, fontFace: FONT_H, fontSize: 13,
    bold: true, color: INK, valign: "middle", margin: 0, lineSpacingMultiple: 1.0,
  });
  slide.addText(body, {
    x: x + 0.22, y: y + 1.14, w: w - 0.44, h: h - 1.24, fontFace: FONT, fontSize: 9,
    color: "475569", valign: "top", margin: 0, lineSpacingMultiple: 1.05,
  });
}

function titleBar(slide, kicker, title) {
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 0.42, w: 0.13, h: 0.62, fill: { color: ACCENT } });
  if (kicker) slide.addText(kicker, { x: 0.74, y: 0.36, w: 8.7, h: 0.26, fontFace: FONT, fontSize: 10.5, bold: true, color: ACCENT, charSpacing: 2, margin: 0 });
  slide.addText(title, { x: 0.72, y: 0.58, w: 8.8, h: 0.55, fontFace: FONT_H, fontSize: 23, bold: true, color: INK, margin: 0 });
}

// =========================================================
// SLIDE 1 — 封面
// =========================================================
let s = pres.addSlide();
s.background = { color: NAVY };
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.16, fill: { color: ACCENT } });
s.addText("B 站评论区 · 声量洞察报告", { x: 0.8, y: 1.2, w: 8, h: 0.4, fontFace: FONT, fontSize: 13, bold: true, color: "F59E0B", charSpacing: 3, margin: 0 });
s.addText(M.product || "产品", { x: 0.78, y: 1.72, w: 9.0, h: 1.0, fontFace: FONT_H, fontSize: 33, bold: true, color: WHITE, margin: 0 });
s.addText(`${fmt(D.overview.rows)} 条真实评论里的声音偏好，与${D.seg_names.join(" / ")}人群的分层解读`, { x: 0.8, y: 2.82, w: 8.8, h: 0.5, fontFace: FONT, fontSize: 14.5, color: "C7CEDB", margin: 0 });

const chips = [[fmt(D.overview.rows), "解析评论"], [fmt(D.overview.vol), "累计声量"], [`${D.overview.coverage}%`, "采集覆盖率"]];
chips.forEach((c, i) => {
  const x = 0.8 + i * 2.95;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.7, w: 2.7, h: 1.0, fill: { color: NAVY2 }, line: { color: "2C3858", width: 1 }, rectRadius: 0.08 });
  s.addText(c[0], { x, y: 3.83, w: 2.7, h: 0.55, align: "center", fontFace: FONT_H, fontSize: 27, bold: true, color: WHITE, margin: 0 });
  s.addText(c[1], { x, y: 4.37, w: 2.7, h: 0.3, align: "center", fontFace: FONT, fontSize: 11, color: "9AA6BD", margin: 0 });
});
s.addText([M.bvid ? `数据来源 ${M.bvid}` : null, M.owner, M.date ? `分析日期 ${M.date}` : null,
  M.subtitle_method ? `方法：${M.subtitle_method}` : null].filter(Boolean).join("  |  "),
  { x: 0.8, y: 5.12, w: 8.8, h: 0.3, fontFace: FONT, fontSize: 9.5, color: "7E8AA3", margin: 0 });

// =========================================================
// SLIDE 2 — 声量偏好总览
// =========================================================
s = pres.addSlide();
s.background = { color: LIGHT };
titleBar(s, "PART 1 · 数据化分析 ①", INS.slide_titles?.sentiment || "声音的偏好：情绪结构与声量分布");

const sent6 = D.sentiment.slice(0, 6);
s.addChart(pres.charts.DOUGHNUT, [{ name: "声量", labels: sent6.map(x => x.name), values: sent6.map(x => x.vol) }], {
  x: 0.35, y: 1.45, w: 4.1, h: 3.45, holeSize: 58, showLegend: false,
  chartColors: sent6.map(x => SENT_COLOR[x.name] || GREY), showValue: false, dataBorder: { pt: 2, color: LIGHT },
});
s.addText("声量\n结构", { x: 1.55, y: 2.78, w: 1.7, h: 0.8, align: "center", valign: "middle", fontFace: FONT_H, fontSize: 13, bold: true, color: INK, margin: 0 });

const topQ = D.quotes_all[0];
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.85, y: 1.45, w: 4.65, h: 1.05, fill: { color: NAVY }, rectRadius: 0.08 });
s.addText([
  { text: "TOP1 评论：", options: { bold: true, color: "F59E0B" } },
  { text: `「${topQ.text.slice(0, 24)}」${fmt(topQ.vol)} 赞`, options: { color: WHITE } },
], { x: 5.05, y: 1.55, w: 4.3, h: 0.85, fontFace: FONT, fontSize: 12, valign: "middle", margin: 0, lineSpacingMultiple: 1.05 });

const leg = sent6.map(x => [x.name, `${x.vol_pct}%`, SENT_COLOR[x.name] || GREY]);
leg.forEach((l, i) => {
  const y = 2.72 + i * 0.42;
  s.addShape(pres.shapes.RECTANGLE, { x: 4.9, y: y + 0.05, w: 0.22, h: 0.22, fill: { color: l[2] } });
  s.addText(l[0], { x: 5.22, y, w: 3.0, h: 0.32, fontFace: FONT, fontSize: 11.5, color: INK, valign: "middle", margin: 0 });
  s.addText(l[1], { x: 8.3, y, w: 1.2, h: 0.32, fontFace: FONT_H, fontSize: 12, bold: true, color: (l[2] === "94A3B8" ? SLATE : l[2]), align: "right", valign: "middle", margin: 0 });
});
footer(s, false);

// =========================================================
// SLIDE 3 — 已购 vs 未购 人群画像
// =========================================================
s = pres.addSlide();
s.background = { color: LIGHT };
titleBar(s, "PART 1 · 数据化分析 ②", INS.slide_titles?.segments || "购买意向分群：表态人群的声量结构");

// ===== 数据表（左）：5 列分类对比，4 色徽标 =====
const tableX = 0.35, tableY = 1.55, tableW = 4.95;
const colW = [1.05, 0.7, 0.8, 0.75, 1.65]; // 人群 / 条数 / 声量 / 占比 / 立场
const headerH = 0.38, dataH = 0.62;

// 表头（深蓝底 + 白字）
s.addShape(pres.shapes.RECTANGLE, {
  x: tableX, y: tableY, w: tableW, h: headerH,
  fill: { color: NAVY }, line: { color: NAVY, width: 0 },
});
const headers = ["人群", "条数", "声量", "占比", "标志性立场"];
let hx = tableX;
headers.forEach((h, i) => {
  s.addText(h, {
    x: hx, y: tableY, w: colW[i], h: headerH,
    align: i === 0 || i === 4 ? "left" : "center", valign: "middle",
    fontFace: FONT_H, fontSize: 10.5, bold: true, color: WHITE, margin: 6,
  });
  hx += colW[i];
});

// 4 行数据（占比分母 = 本组 4 类声量合计，非全站总声量）
const segTotal = D.segments.reduce((a, b) => a + b.vol, 0) || 1;
const stance = INS.segment_stance || {};
const rows = D.segments.map(sg => [
  sg.name.replace(/\/.*$/, ""), fmt(sg.cnt), fmt(sg.vol),
  `${(sg.vol / segTotal * 100).toFixed(1)}%`,
  stance[sg.name] || "—", SEG_COLOR[sg.name] || GREY,
]);
rows.forEach((r, i) => {
  const y = tableY + headerH + i * dataH;
  // 斑马纹底
  s.addShape(pres.shapes.RECTANGLE, {
    x: tableX, y, w: tableW, h: dataH,
    fill: { color: i % 2 === 0 ? "FFFFFF" : "F4F6FA" }, line: { color: "F4F6FA", width: 0 },
  });
  // 下边线
  s.addShape(pres.shapes.LINE, {
    x: tableX, y: y + dataH, w: tableW, h: 0,
    line: { color: LINE, width: 0.5 },
  });

  let cx = tableX;
  // 列1：人群（彩点 + 文字）
  s.addShape(pres.shapes.OVAL, { x: cx + 0.12, y: y + 0.22, w: 0.18, h: 0.18, fill: { color: r[5] } });
  s.addText(r[0], {
    x: cx + 0.34, y, w: colW[0] - 0.36, h: dataH,
    fontFace: FONT_H, fontSize: 11, bold: true, color: INK, valign: "middle", margin: 0,
  });
  cx += colW[0];
  // 列2：条数
  s.addText(r[1], {
    x: cx, y, w: colW[1], h: dataH,
    align: "center", valign: "middle", fontFace: FONT_H, fontSize: 12, color: INK, margin: 0,
  });
  cx += colW[1];
  // 列3：声量（按类别上色）
  s.addText(r[2], {
    x: cx, y, w: colW[2], h: dataH,
    align: "center", valign: "middle", fontFace: FONT_H, fontSize: 13, bold: true, color: r[5], margin: 0,
  });
  cx += colW[2];
  // 列4：占比
  s.addText(r[3], {
    x: cx, y, w: colW[3], h: dataH,
    align: "center", valign: "middle", fontFace: FONT, fontSize: 11, color: SLATE, margin: 0,
  });
  cx += colW[3];
  // 列5：立场
  s.addText(r[4], {
    x: cx, y, w: colW[4], h: dataH,
    fontFace: FONT, fontSize: 10.2, color: "475569", valign: "middle", margin: 6,
  });
});

const F = D.funnel, fPos = F.net >= 0;
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.35, y: 1.5, w: 4.15, h: 1.15, fill: { color: NAVY }, rectRadius: 0.08 });
s.addText(`${fPos ? "+" : ""}${fmt(F.net)}`, { x: 5.55, y: 1.62, w: 2.0, h: 0.9, fontFace: FONT_H, fontSize: 30, bold: true, color: fPos ? "4ADE80" : "F87171", valign: "middle", margin: 0 });
s.addText([
  { text: "意向净值（声量）\n", options: { fontSize: 11, color: "9AA6BD", breakLine: true } },
  { text: `已购+强意向 ${fmt(F.buy_intent_vol)}  vs  劝退 ${fmt(F.repel_vol)}${F.ratio ? `  ≈ ${F.ratio} : 1` : ""}`, options: { fontSize: 11, color: WHITE, bold: true } },
], { x: 7.55, y: 1.6, w: 1.85, h: 0.95, fontFace: FONT, valign: "middle", margin: 0, lineSpacingMultiple: 1.1 });

// ===== 右侧：占比横条 + 洞察 =====
// （占比横条已合并进左侧表格的"占比"列，这里只保留关键洞察卡）

// 关键洞察 1：本组合计
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.45, y: 2.95, w: 4.1, h: 1.05,
  fill: { color: WHITE }, line: { color: LINE, width: 1 }, rectRadius: 0.08, shadow: makeShadow() });
const segCnt = D.segments.reduce((a, b) => a + b.cnt, 0);
s.addText(`表态人群合计 ${fmt(segCnt)} 条 · ${fmt(segTotal)} 声量`, {
  x: 5.6, y: 3.0, w: 3.85, h: 0.3,
  fontFace: FONT_H, fontSize: 11, bold: true, color: INK, valign: "middle", margin: 0,
});
s.addText(`已购+强意向 ${fmt(F.buy_intent_vol)} 声量（${(F.buy_intent_vol / segTotal * 100).toFixed(1)}%） vs 劝退 ${fmt(F.repel_vol)} 声量（${(F.repel_vol / segTotal * 100).toFixed(1)}%）。${INS.funnel_note || ""}`, {
  x: 5.6, y: 3.32, w: 3.85, h: 0.65,
  fontFace: FONT, fontSize: 10.5, color: "475569", valign: "top", margin: 0, lineSpacingMultiple: 1.2,
});

// 关键洞察 2：市场定位结论
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.45, y: 4.05, w: 4.1, h: 0.75,
  fill: { color: NAVY2 }, line: { color: "2C3858", width: 1 }, rectRadius: 0.08 });
s.addText(INS.segment_verdict || INS.headline || "", {
  x: 5.6, y: 4.1, w: 3.85, h: 0.7,
  fontFace: FONT, fontSize: 10.5, color: WHITE, valign: "middle", margin: 0, lineSpacingMultiple: 1.15,
});
footer(s, false);

// =========================================================
// SLIDE 4 — 数据化三大洞察
// =========================================================
s = pres.addSlide();
s.background = { color: LIGHT };
titleBar(s, "PART 1 · 数据化分析 ③", INS.slide_titles?.findings || "三个反直觉的数据结论");

const ins = (INS.findings || []).slice(0, 3).map(f => [f.title, f.body, col(f.color)]);
ins.forEach((c, i) => {
  const x = 0.5 + i * 3.05;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.55, w: 2.85, h: 2.95, fill: { color: WHITE }, line: { color: LINE, width: 1 }, rectRadius: 0.09, shadow: makeShadow() });
  s.addShape(pres.shapes.RECTANGLE, { x, y: 1.55, w: 2.85, h: 0.14, fill: { color: c[2] } });
  s.addText("0" + (i + 1), { x: x + 0.2, y: 1.78, w: 1.2, h: 0.6, fontFace: FONT_H, fontSize: 30, bold: true, color: c[2], margin: 0 });
  s.addText(c[0], { x: x + 0.2, y: 2.45, w: 2.5, h: 0.5, fontFace: FONT_H, fontSize: 16, bold: true, color: INK, margin: 0 });
  s.addText(c[1], { x: x + 0.2, y: 2.98, w: 2.5, h: 1.4, fontFace: FONT, fontSize: 11.3, color: "475569", valign: "top", margin: 0, lineSpacingMultiple: 1.12 });
});
footer(s, false);

// =========================================================
// SLIDE 5 — Part 2 分隔（2x2 网格）
// =========================================================
s = pres.addSlide();
s.background = { color: NAVY };
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.16, h: 5.625, fill: { color: ACCENT } });
s.addText("PART 2", { x: 0.9, y: 0.7, w: 8, h: 0.4, fontFace: FONT, fontSize: 14, bold: true, color: "F59E0B", charSpacing: 4, margin: 0 });
s.addText("人群分层深读", { x: 0.85, y: 1.05, w: 8.5, h: 0.8, fontFace: FONT_H, fontSize: 34, bold: true, color: WHITE, margin: 0 });
s.addText("从已购、未购、观望三类人群，拆解真实痛点与改进方向", { x: 0.9, y: 1.85, w: 8.5, h: 0.35, fontFace: FONT, fontSize: 13, color: "9AA6BD", margin: 0 });

const LAYERS = INS.layers || [];
const p2 = [
  ...LAYERS.slice(0, 3).map((l, i) => [
    String(i + 1).padStart(2, "0"),
    (l.nav_title || l.title.split(/[·:：]/)[0] || l.title).trim(),
    (l.nav_sub || l.title.split(/[·:：]/).slice(1).join("·") || "").trim(),
  ]),
  ["0" + (Math.min(LAYERS.length, 3) + 1), "改进点路线图", "来自评论原话的方向清单"],
];
const px = [0.9, 5.15], py = [2.45, 3.8];
p2.forEach((p, i) => {
  const x = px[i % 2], y = py[Math.floor(i / 2)];
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 4.0, h: 1.15, fill: { color: NAVY2 }, line: { color: "2C3858", width: 1 }, rectRadius: 0.08 });
  s.addShape(pres.shapes.OVAL, { x: x + 0.22, y: y + 0.3, w: 0.55, h: 0.55, fill: { color: ACCENT } });
  s.addText(p[0], { x: x + 0.22, y: y + 0.3, w: 0.55, h: 0.55, align: "center", valign: "middle", fontFace: FONT_H, fontSize: 16, bold: true, color: WHITE, margin: 0 });
  s.addText(p[1], { x: x + 0.95, y: y + 0.18, w: 2.9, h: 0.45, fontFace: FONT_H, fontSize: 15, bold: true, color: WHITE, valign: "middle", margin: 0 });
  s.addText(p[2], { x: x + 0.95, y: y + 0.62, w: 2.9, h: 0.4, fontFace: FONT, fontSize: 10.5, color: "9AA6BD", margin: 0 });
});

// =========================================================
// SLIDE 6~8 — 人群分层（由 insights.layers 驱动，最多 3 层）
// =========================================================
const gx = [0.5, 5.25], gy = [1.5, 3.25]; // layer 2x2 用
const gx9 = [0.5, 5.25], gy9 = [1.45, 3.5]; // slide 9 用
// item 兼容两种写法：字符串 "标题：正文" 或 {badge,title,body}
function normItem(it) {
  if (typeof it === "string") {
    const m = it.match(/^(.{2,14}?)[：:](.+)$/s);
    return m ? { badge: "", title: m[1].trim(), body: m[2].trim() } : { badge: "", title: "", body: it };
  }
  return { badge: it.badge || "", title: it.title || "", body: it.body || "" };
}

LAYERS.slice(0, 3).forEach((L, li) => {
  s = pres.addSlide();
  s.background = { color: LIGHT };
  const lc = col(L.color);
  titleBar(s, L.kicker || `PART 2 · 0${li + 1}`, L.title);
  const items = (L.items || []).slice(0, 4).map(normItem);

  if (items.length <= 3) {
    // 3 卡横排（大卡，正文更充裕）；徽标作为圆点旁 kicker
    items.forEach((it, i) => {
      const x = 0.5 + i * 3.05, w = 2.85, h = 3.1, dot = 0.5;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.6, w, h, fill: { color: WHITE }, line: { color: LINE, width: 1 }, rectRadius: 0.09, shadow: makeShadow() });
      s.addShape(pres.shapes.OVAL, { x: x + 0.22, y: 1.85, w: dot, h: dot, fill: { color: lc } });
      if (it.badge) s.addText(it.badge, { x: x + 0.22 + dot + 0.12, y: 1.8, w: w - 0.22 - dot - 0.3, h: dot + 0.08, align: "left", valign: "middle", fontFace: FONT_H, fontSize: 13, bold: true, color: lc, margin: 0 });
      s.addText(it.title, { x: x + 0.22, y: 2.5, w: w - 0.44, h: 0.5, fontFace: FONT_H, fontSize: 15, bold: true, color: INK, margin: 0 });
      s.addText(it.body, { x: x + 0.22, y: 3.05, w: w - 0.44, h: 1.5, fontFace: FONT, fontSize: 10.8, color: "475569", valign: "top", margin: 0, lineSpacingMultiple: 1.08 });
    });
  } else {
    // 2×2 网格
    items.forEach((it, i) => {
      const x = gx[i % 2], y = gy[Math.floor(i / 2)];
      card(s, x, y, 4.25, 1.62, it.badge || String(i + 1), it.title, it.body, lc);
    });
  }
  if (L.summary) s.addText(L.summary, { x: 0.5, y: 4.95, w: 9, h: 0.3, fontFace: FONT, fontSize: 10.2, italic: true, color: SLATE, margin: 0 });
  footer(s, false);
});

// =========================================================
// SLIDE 9 — 二合一改进点
// =========================================================
s = pres.addSlide();
s.background = { color: LIGHT };
titleBar(s, `PART 2 · 0${Math.min(LAYERS.length, 3) + 1} 改进方向`,
  INS.slide_titles?.improvements || "改进点路线图（来自评论原话）");

const imps = (INS.improvements || []).slice(0, 4);
imps.forEach((im, i) => {
  const x = gx9[i % 2], y = gy9[Math.floor(i / 2)];
  card(s, x, y, 4.25, 1.95, String(i + 1), im.title, im.body, col(im.color));
});
footer(s, false);

pres.writeFile({ fileName: OUT_PATH }).then(f => console.log(`✅ PPT 完成 → ${f}`));
