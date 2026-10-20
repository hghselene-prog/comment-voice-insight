#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清洗后 CSV + config.json  →  _report_data.json
============================================================
机械层核心：所有统计口径在这里定死，四个渲染器共用同一份数字，
保证 Word / PPT / HTML / 长图 之间不会出现对不上的数据。

口径（重要，别改）：
  - 声量 = 累计点赞（含转评）。仅「点赞缺失==0」的行参与声量计算。
  - 条数 = 全部未剔除行（含点赞缺失），用于定性描述。
  - 主题可多命中（不互斥）→ 主题声量之和 > 总声量，属预期。
  - 分群唯一分配，优先级 已购 > 强意向 > 劝退 > 观望。

用法：
    python3 build_data.py --csv reports/_clean_xxx.csv --config config.json \
                          --out reports/_report_data.json
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit("需要 pandas：sudo pip3 install pandas")

PRI = ['已购/下单', '强意向', '劝退/放弃', '观望']   # 分群唯一分配优先级


def has(text, kws):
    if pd.isna(text):
        return False
    t = str(text).lower()
    return any(k.lower() in t for k in kws)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True, help='prep.py 产出的 _clean_*.csv')
    ap.add_argument('--config', required=True, help='config.json')
    ap.add_argument('--out', required=True, help='输出 _report_data.json')
    a = ap.parse_args()

    cfg = json.loads(Path(a.config).read_text(encoding='utf-8'))
    df = pd.read_csv(a.csv)

    # 兼容：prep.py 若未产出这两列则宽松处理
    if '点赞缺失' not in df.columns:
        df['点赞缺失'] = 0
    if '已剔除' not in df.columns:
        df['已剔除'] = False
    if '累计声量' not in df.columns:
        df['累计声量'] = df.get('原始点赞', 0)

    df_v = df[(df['点赞缺失'] == 0) & (df['已剔除'] == False)].copy()   # 声量基数
    df_all = df[df['已剔除'] == False].copy()                          # 条数基数

    TOTAL_VOL = int(df_v['累计声量'].sum())
    TOTAL_ROWS = int(len(df_all))
    if TOTAL_VOL == 0:
        sys.exit('错误：总声量为 0，检查 CSV 的「累计声量 / 点赞缺失」列是否正常')

    D = {}

    # ---------- 概览 ----------
    # coverage / conservation 是外部信息（CSV 推不出来），由 config.meta 提供：
    #   total_comments  = 视频实际评论总数（B站页面上看）→ 采集覆盖率
    #   source_like_sum = 源文档点赞总和（人工/脚本核对）→ 点赞守恒校验
    # 缺失时降级为可计算的「点赞覆盖率」，并把 conservation 置 None（渲染器会跳过）
    m = cfg.get('meta', {})
    like_cov = round(len(df_v) / max(len(df), 1) * 100, 1)
    total_cmt = m.get('total_comments')
    src_like = m.get('source_like_sum')

    D['overview'] = {
        'rows': TOTAL_ROWS,
        'vol': TOTAL_VOL,
        'coverage': round(TOTAL_ROWS / total_cmt * 100, 1) if total_cmt else like_cov,
        'coverage_label': '采集覆盖率' if total_cmt else '点赞覆盖率',
        'conservation': round(min(src_like, TOTAL_VOL) / max(src_like, TOTAL_VOL, 1) * 100, 1) if src_like else None,
        'like_coverage': like_cov,
    }

    # ---------- 情绪（中性自动兜底）----------
    SENT = cfg['sentiment']
    all_sent_kws = sum(SENT.values(), [])
    sent_rows = []
    for name, kws in SENT.items():
        m = df_v[df_v['content'].apply(lambda t: has(t, kws))]
        sent_rows.append({'name': name, 'cnt': int(len(m)), 'vol': int(m['累计声量'].sum()),
                          'vol_pct': round(m['累计声量'].sum() / TOTAL_VOL * 100, 1)})
    neu = df_v[~df_v['content'].apply(lambda t: has(t, all_sent_kws))]
    sent_rows.append({'name': '中性/陈述', 'cnt': int(len(neu)), 'vol': int(neu['累计声量'].sum()),
                      'vol_pct': round(neu['累计声量'].sum() / TOTAL_VOL * 100, 1)})
    D['sentiment'] = sorted(sent_rows, key=lambda x: -x['vol'])

    # ---------- 主题（可多命中）----------
    THEMES = cfg['themes']
    theme_rows = []
    for name, kws in THEMES.items():
        m = df_v[df_v['content'].apply(lambda t: has(t, kws))]
        theme_rows.append({'name': name, 'cnt': int(len(m)), 'vol': int(m['累计声量'].sum()),
                           'vol_pct': round(m['累计声量'].sum() / TOTAL_VOL * 100, 1)})
    D['themes'] = sorted(theme_rows, key=lambda x: -x['vol'])

    # ---------- 分群（唯一分配）----------
    INTENT = cfg['intent']
    order = [k for k in PRI if k in INTENT] + [k for k in INTENT if k not in PRI]

    def classify(text):
        for name in order:
            if has(text, INTENT[name]):
                return name
        return None

    df_v['_seg'] = df_v['content'].apply(classify)
    df_all['_seg'] = df_all['content'].apply(classify)
    seg_rows = []
    for name in order:
        m = df_v[df_v['_seg'] == name]
        seg_rows.append({'name': name, 'cnt': int((df_all['_seg'] == name).sum()),
                         'vol': int(m['累计声量'].sum()),
                         'vol_pct': round(m['累计声量'].sum() / TOTAL_VOL * 100, 1)})
    D['segments'] = seg_rows
    D['seg_names'] = order

    # ---------- 人群 × 主题 矩阵 ----------
    theme_names = [t['name'] for t in D['themes']]
    D['theme_names'] = theme_names
    matrix = {}
    for s in order:
        sub = df_v[df_v['_seg'] == s]
        if len(sub) == 0:                      # 该分群可能为空（小样本/新品类常见）
            matrix[s] = {t: 0 for t in theme_names}
            continue
        matrix[s] = {t: int(sub[sub['content'].apply(lambda x: has(x, THEMES[t]))]['累计声量'].sum())
                     for t in theme_names}
    D['matrix'] = matrix

    # ---------- 漏斗 ----------
    g = {r['name']: r['vol'] for r in seg_rows}
    buy = g.get('已购/下单', 0) + g.get('强意向', 0)
    repel = g.get('劝退/放弃', 0)
    D['funnel'] = {
        'buy_intent_vol': buy, 'repel_vol': repel, 'net': buy - repel,
        'ratio': round(buy / repel, 1) if repel else None,
    }

    # ---------- 对比组（可选）----------
    if cfg.get('contrast'):
        c = cfg['contrast']
        va = int(df_v[df_v['content'].apply(lambda t: has(t, c['side_a']['kws']))]['累计声量'].sum())
        vb = int(df_v[df_v['content'].apply(lambda t: has(t, c['side_b']['kws']))]['累计声量'].sum())
        D['contrast'] = {'label': c['label'], 'a_name': c['side_a']['name'], 'b_name': c['side_b']['name'],
                         'a_vol': va, 'b_vol': vb,
                         'ratio': round(va / vb, 1) if vb else None}

    # ---------- 正负比（可选）----------
    if cfg.get('polarity'):
        p = cfg['polarity']
        sub = df_v[df_v['content'].apply(lambda t: has(t, p['kws']))]
        tot = int(sub['累计声量'].sum())
        if len(sub):
            pos = int(sub[sub['content'].apply(lambda t: has(t, p['pos_kws']))]['累计声量'].sum())
            neg = int(sub[sub['content'].apply(lambda t: has(t, p['neg_kws']))]['累计声量'].sum())
        else:
            pos = neg = 0
        D['polarity'] = {
            'label': p['label'], 'total': int(len(sub)), 'vol': tot,
            'pos_vol': pos, 'neg_vol': neg,
            'pos_pct': round(pos / tot * 100, 1) if tot else 0,
            'neg_pct': round(neg / tot * 100, 1) if tot else 0,
            'ratio': round(pos / neg, 1) if neg else None,
        }

    # ---------- 高赞引用 ----------
    def quote(r):
        return {'vol': int(r['累计声量']), 'text': str(r['content']).strip().replace('\n', ' ')[:120]}

    top = df_v.nlargest(15, '累计声量')
    D['quotes_all'] = [quote(r) for _, r in top.iterrows()]
    D['quotes_seg'] = {s: [quote(r) for _, r in df_v[df_v['_seg'] == s].nlargest(5, '累计声量').iterrows()]
                       for s in order}
    D['quotes_theme'] = {t: [quote(r) for _, r in
                             df_v[df_v['content'].apply(lambda x: has(x, THEMES[t]))].nlargest(3, '累计声量').iterrows()]
                         for t in theme_names[:8]}

    D['meta'] = cfg['meta']

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(D, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"✅ 数据层完成 → {a.out}")
    print(f"   {TOTAL_ROWS} 条 / {TOTAL_VOL:,} 声量 / 覆盖率 {D['overview']['coverage']}%")
    print(f"   分群 " + " · ".join(f"{r['name']}{r['cnt']}条" for r in seg_rows))


if __name__ == '__main__':
    main()
