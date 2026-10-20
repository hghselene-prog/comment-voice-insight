#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_report_data.json + insights.json  →  自包含 HTML 报告
============================================================
无外部依赖（不引 CDN、不引字体文件），单文件可直接发送/托管。
同时作为长图的渲染源。

用法：
    python3 build_html.py --data _report_data.json --insights insights.json --out 报告.html
"""
import argparse
import html
import json
from pathlib import Path

PALETTE = {'NAVY': '#121A2E', 'ACCENT': '#E11D2A', 'POS': '#16A34A',
           'WATCH': '#F59E0B', 'DATA': '#2563EB', 'INK': '#1E293B', 'SLATE': '#64748B'}
SENT_COLOR = {'玩梗': '#F59E0B', '期待': '#16A34A', '中性/陈述': '#64748B',
              '失望': '#E11D2A', '愤怒': '#E11D2A', '观望': '#2563EB'}
SEG_COLOR = {'已购/下单': '#16A34A', '强意向': '#2563EB', '观望': '#F59E0B', '劝退/放弃': '#E11D2A'}


def c(name):
    return PALETTE.get(name, name if name and name.startswith('#') else PALETTE['DATA'])


def esc(s):
    return html.escape(str(s))


def heat(v, mx):
    """白→蓝插值，gamma 0.62 提升低值区对比度"""
    if not mx:
        return '#F8FAFC'
    t = min(1.0, v / mx) ** 0.62
    r, g, b = (round(248 + (30 - 248) * t), round(250 + (88 - 250) * t), round(252 + (230 - 252) * t))
    return f'#{r:02x}{g:02x}{b:02x}'


def bars(rows, cmap, total_key='vol', label_fmt=None):
    mx = max((r[total_key] for r in rows), default=1) or 1
    out = []
    for r in rows:
        w = r[total_key] / mx * 100
        color = cmap(r) if callable(cmap) else cmap
        lbl = label_fmt(r) if label_fmt else f"{r['vol']:,}（{r['vol_pct']}%）"
        out.append(f'''<div class="bar-row"><div class="bar-lbl">{esc(r['name'])}</div>
<div class="bar-track"><div class="bar-fill" style="width:{w:.1f}%;background:{color}"></div></div>
<div class="bar-val">{esc(lbl)}</div></div>''')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--insights', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    D = json.loads(Path(a.data).read_text(encoding='utf-8'))
    INS = json.loads(Path(a.insights).read_text(encoding='utf-8'))
    M = D.get('meta', {})
    ov, fn = D['overview'], D['funnel']
    net_pos = fn['net'] >= 0

    # KPI
    if D.get('polarity'):
        k6 = (f"{D['polarity'].get('ratio', '—')}:1", f"{D['polarity']['label']}正负声量比", '#F59E0B')
    elif D.get('contrast'):
        k6 = (f"{D['contrast'].get('ratio', '—')}:1", D['contrast']['label'], '#F59E0B')
    else:
        k6 = (str(len(D['themes'])), '主题维度数', '#F59E0B')
    net_ratio_txt = f"（{fn['ratio']}:1）" if fn.get('ratio') else ''
    kpis = [
        (f"{ov['rows']:,}", '解析评论（条）', '#121A2E'),
        (f"{ov['vol']:,}", '总声量（赞·含转评）', '#121A2E'),
        (f"{ov['coverage']}%", ov.get('coverage_label', '样本覆盖率'), '#2563EB'),
        (f"{ov['conservation']}%", '点赞守恒校验', '#16A34A') if ov.get('conservation') is not None
        else (f"{len(D['sentiment'])}", '情绪分类数', '#16A34A'),
        (f"{'+' if net_pos else ''}{fn['net']:,}", f"意向净值{net_ratio_txt}",
         '#16A34A' if net_pos else '#E11D2A'),
        k6,
    ]
    kpi_html = '\n'.join(
        f'<div class="kpi"><div class="kpi-v" style="color:{col}">{esc(v)}</div>'
        f'<div class="kpi-l">{esc(l)}</div></div>' for v, l, col in kpis)

    # 矩阵
    seg_names, theme_names, mx = D['seg_names'], D['theme_names'], D['matrix']
    col_max = {t: max((mx[s][t] for s in seg_names), default=0) for t in theme_names}
    head = ''.join(f'<th>{esc(t)}</th>' for t in theme_names)
    body = ''
    for s in seg_names:
        tds = ''
        for t in theme_names:
            v = mx[s][t]
            bg = heat(v, col_max[t])
            fg = '#fff' if col_max[t] and v / col_max[t] > 0.55 else '#1E293B'
            tds += f'<td style="background:{bg};color:{fg}">{v:,}</td>' if v else \
                   f'<td style="background:{bg};color:#CBD5E1">·</td>'
        body += f'<tr><th class="rowh">{esc(s)}</th>{tds}</tr>'

    # 洞察卡片
    def cards(items, key_body='body'):
        return '\n'.join(
            f'<div class="card" style="border-left-color:{c(i.get("color"))}">'
            f'<div class="card-t" style="color:{c(i.get("color"))}">{esc(i["title"])}</div>'
            f'<div class="card-b">{esc(i[key_body])}</div></div>' for i in items)

    def item_html(it):
        """items 兼容字符串 / {badge,title,body} 两种写法"""
        if isinstance(it, str):
            return f'<li>{esc(it)}</li>'
        head = esc(it.get('title', ''))
        badge = f'<span class="ibadge">{esc(it["badge"])}</span>' if it.get('badge') else ''
        return f'<li>{badge}<b>{head}</b>{"：" if head else ""}{esc(it.get("body", ""))}</li>'

    layers_html = ''
    for l in INS.get('layers', []):
        lc = c(l.get('color'))
        its = ''.join(item_html(x) for x in l.get('items', []))
        smy = f'<div class="lsum">{esc(l["summary"])}</div>' if l.get('summary') else ''
        layers_html += (f'<div class="layer"><div class="layer-t" style="border-left-color:{lc};color:{lc}">'
                        f'{esc(l["title"])}</div><ul>{its}</ul>{smy}</div>')

    def quotes(qs):
        return '\n'.join(f'<div class="q"><span class="qv">{q["vol"]:,}</span>{esc(q["text"])}</div>' for q in qs)

    seg_q = ''
    for s in seg_names:
        qs = D['quotes_seg'].get(s, [])
        if qs:
            seg_q += (f'<div class="qgrp"><div class="qgrp-t" style="color:{SEG_COLOR.get(s, "#121A2E")}">'
                      f'{esc(s)}（TOP{len(qs)}）</div>{quotes(qs)}</div>')

    sub = ' · '.join(filter(None, [
        f"数据源 {M['bvid']}" if M.get('bvid') else None,
        f"UP主 {M['owner']}" if M.get('owner') else None,
        f"分析日期 {M['date']}" if M.get('date') else None,
        f"方法：{M['subtitle_method']}" if M.get('subtitle_method') else None]))

    findings = INS.get('findings', [])
    improvements = INS.get('improvements', [])

    HTML = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(M.get('product', '产品'))} · 评论洞察</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"Noto Sans SC","Microsoft YaHei","PingFang SC",sans-serif;color:#1E293B;
background:#fff;line-height:1.65;font-size:14px}}
.wrap{{max-width:960px;margin:0 auto;padding:32px 28px 60px}}
h1{{font-size:26px;color:#121A2E;letter-spacing:-.3px}}
.sub{{color:#64748B;font-size:12.5px;margin:6px 0 22px}}
h2{{font-size:18px;color:#121A2E;margin:34px 0 4px;padding-bottom:8px;border-bottom:3px solid #121A2E}}
h3{{font-size:15px;color:#121A2E;margin:18px 0 10px}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}}
.kpi{{background:#F4F6FA;border:1px solid #E2E8F0;border-radius:8px;padding:14px 16px}}
.kpi-v{{font-size:25px;font-weight:700;line-height:1.15}}
.kpi-l{{font-size:11.5px;color:#64748B;margin-top:3px}}
.headline{{background:#121A2E;color:#fff;border-radius:8px;padding:16px 20px;margin:16px 0;font-size:14.5px}}
.headline b{{color:#F59E0B}}
.bar-row{{display:flex;align-items:center;gap:10px;margin:5px 0}}
.bar-lbl{{width:108px;font-size:12.5px;font-weight:600;flex-shrink:0;text-align:right}}
.bar-track{{flex:1;background:#F1F5F9;border-radius:3px;height:17px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:3px}}
.bar-val{{width:150px;font-size:11.5px;color:#64748B;font-weight:600;flex-shrink:0}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:11px}}
th,td{{border:1px solid #D5DEE8;padding:5px 4px;text-align:center}}
thead th{{background:#121A2E;color:#fff;font-weight:600;font-size:10.5px}}
.rowh{{background:#F4F6FA;text-align:left;padding-left:8px;font-size:11.5px;white-space:nowrap}}
.note{{font-size:11.5px;color:#64748B;font-style:italic;margin:8px 0 0}}
.card{{background:#F4F6FA;border-left:5px solid;border-radius:0 6px 6px 0;padding:12px 16px;margin:10px 0}}
.card-t{{font-weight:700;font-size:14.5px;margin-bottom:4px}}
.card-b{{font-size:13px}}
.layer{{margin:16px 0}}
.layer-t{{font-weight:700;font-size:14.5px;border-left:5px solid;padding-left:10px;margin-bottom:8px}}
.layer ul{{padding-left:26px}}.layer li{{font-size:13px;margin:4px 0}}
.ibadge{{display:inline-block;background:#E2E8F0;color:#475569;border-radius:3px;
padding:0 6px;font-size:11px;font-weight:700;margin-right:6px}}
.lsum{{font-size:12px;color:#64748B;font-style:italic;margin:6px 0 0 26px}}
.q{{font-size:12.5px;margin:5px 0;padding-left:2px}}
.qv{{display:inline-block;min-width:52px;font-weight:700;color:#E11D2A;font-variant-numeric:tabular-nums}}
.qgrp{{margin:14px 0}}.qgrp-t{{font-weight:700;font-size:13.5px;margin-bottom:5px}}
.meth{{border:1px solid #D5DEE8;border-radius:8px;padding:16px 18px;margin-top:26px;font-size:12px;color:#64748B}}
.meth b{{color:#121A2E;font-size:13.5px}}
@media(max-width:640px){{.kpis{{grid-template-columns:repeat(2,1fr)}}.bar-lbl{{width:76px}}.bar-val{{width:104px}}}}
</style></head><body><div class="wrap">
<h1>{esc(M.get('product', '产品'))} · B站评论洞察</h1>
<div class="sub">{esc(sub)}</div>
<div class="kpis">{kpi_html}</div>
<div class="headline"><b>一句话结论：</b>{esc(INS.get('headline', ''))}</div>

<h2>① 情绪结构（按声量）</h2>
{bars(D['sentiment'], lambda r: SENT_COLOR.get(r['name'], '#64748B'))}
<h3>主题声量分布 TOP{len(D['themes'])}</h3>
{bars(D['themes'], '#2563EB')}

<h2>② 购买意向漏斗（词典粗筛·中置信）</h2>
{bars(D['segments'], lambda r: SEG_COLOR.get(r['name'], '#64748B'),
      label_fmt=lambda r: f"{r['vol']:,} 声量 · {r['cnt']} 条 · {r['vol_pct']}%")}
<p class="note">已购+强意向 {fn['buy_intent_vol']:,} 声量 vs 劝退 {fn['repel_vol']:,} 声量 → 净值
{'+' if net_pos else ''}{fn['net']:,}{f"（约 {fn['ratio']}:1 {'正向' if net_pos else '负向'}）" if fn.get('ratio') else ''}。
{esc(INS.get('funnel_note', ''))}</p>

<h2>③ 人群 × 主题 声量矩阵</h2>
<table><thead><tr><th class="rowh">人群＼主题</th>{head}</tr></thead><tbody>{body}</tbody></table>
<p class="note">单元格=该人群讨论该主题的累计声量；一条评论可跨多主题，故行和大于分群总声量。颜色越深=该主题在该人群中越主导。</p>

{f'<h2>④ 反直觉数据结论</h2>{cards(findings)}' if findings else ''}

<h2>⑤ 高赞引用（声量加权）</h2>
<h3>全局 TOP{len(D['quotes_all'])}</h3>
{quotes(D['quotes_all'])}
{seg_q}

{f'<h2>⑥ 人群分层深挖</h2>{layers_html}' if layers_html else ''}
{f'<h2>⑦ 改进点路线图</h2>{cards(improvements)}' if improvements else ''}

<div class="meth"><b>方法论与数据说明</b><br>
{esc(INS.get('confidence_note', '分群与主题均用词典粗筛，属「中置信」。'))}<br><br>
口径：声量=累计点赞（含转评）；仅含有点赞的评论参与声量加权，缺失点赞的评论参与定性分析但不计入声量。
共解析 {ov['rows']:,} 条 / {ov['vol']:,} 声量{f"，点赞守恒校验 {ov['conservation']}%" if ov.get('conservation') is not None else ""}，{ov.get('coverage_label', '样本覆盖率')} {ov['coverage']}%。
主题可多命中（不互斥），故主题声量之和大于总声量；分群唯一分配，优先级 已购 &gt; 强意向 &gt; 劝退 &gt; 观望。</div>
</div></body></html>'''

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(HTML, encoding='utf-8')
    print(f"✅ HTML 完成 → {a.out}（{len(HTML) / 1024:.1f} KB）")


if __name__ == '__main__':
    main()
