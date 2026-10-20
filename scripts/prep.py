#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B 站评论预处理器
============================================================
把浏览器导出的 CSV/JSON 变成"可以直接做分析的浓缩包"。

机械活交给这里：去重、水军过滤、噪声剔除、统计、排序、抽样。
语义分析（情绪归因、特性归类、争议识别）交给 LLM 做。

用法：
    python3 prep.py data/BV1xx_xxx.csv
    python3 prep.py data/                    # 目录内全部文件，合并处理
    python3 prep.py data/ --out digest.md    # 指定输出

输出：
    reports/_digest_<时间戳>.md   给人和 LLM 看的浓缩摘要
    reports/_clean_<时间戳>.csv   清洗后的全量数据（带标记列）
============================================================
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit("需要 pandas：pip3 install pandas")


# ============================================================
# 噪声规则：这些评论没有分析价值，剔除但保留计数
# ============================================================
NOISE_PATTERNS = [
    r'^[前排沙发板凳地板]{1,6}$',
    r'^(打卡|签到|来了|冲|顶|赞|好|哈{2,}|6+|awsl|nb+|yyds)$',
    r'^[\s\W_]*$',                      # 纯符号/表情/空白
    r'^(第一|第二|第三)$',
    r'^\D{0,2}(留名|标记|马克|mark)\D{0,2}$',
]
NOISE_RE = [re.compile(p, re.I) for p in NOISE_PATTERNS]

# 购买意向信号词（正/负/观望）
INTENT_LEXICON = {
    '已购/下单': ['下单了', '已购', '买了', '入手了', '已下单', '抢到了', '预定了', '冲了', '付款'],
    '强意向':   ['想买', '准备买', '打算入', '心动', '真香', '要冲', '蹲一个', '加购'],
    '观望':     ['再等等', '等降价', '观望', '等评测', '等首发', '看看再说', '等等党', '再看看'],
    '劝退/放弃': ['不buy', '劝退', '不值', '算了吧', '不如', '退了', '取消订单', '不推荐', '别买'],
}

# 产品特性维度词典（新品发布场景）
FEATURE_LEXICON = {
    '价格': ['价格', '定价', '多少钱', '贵', '便宜', '性价比', '溢价', '刀法', '加价', '预算', '涨价', '降价'],
    '外观设计': ['外观', '设计', '颜值', '手感', '配色', '质感', '模具', '厚度', '重量', '丑', '好看'],
    '性能': ['性能', '跑分', '芯片', '处理器', '算力', '卡顿', '流畅', '发热', '功耗', '散热'],
    '续航充电': ['续航', '电池', '充电', '快充', '电量', '掉电', '耐用'],
    '影像': ['拍照', '相机', '影像', '镜头', '画质', '成像', '摄像', '录像', '变焦'],
    '屏幕': ['屏幕', '显示', '色准', '刷新率', '亮度', '护眼', '频闪', '素质'],
    '系统软件': ['系统', 'ui', '软件', '广告', '流畅度', '生态', '互联', '适配', '更新', 'bug'],
    '供货渠道': ['现货', '缺货', '抢不到', '发货', '黄牛', '产能', '首发', '预售', '排队'],
    '售后服务': ['售后', '保修', '客服', '维修', '换新', '退货'],
    '竞品对比': ['对比', '不如', '比得上', '碾压', '还是买', '相比', '同价位', '隔壁'],
}


def norm_text(s):
    # pandas 读 CSV 时空单元格会变成 float('nan')，str() 之后是 "nan"。
    # 不处理的话这些空评论会以 "nan" 的形式混进分析结果。
    if s is None:
        return ''
    if isinstance(s, float) and s != s:      # NaN 判定
        return ''
    t = re.sub(r'\s+', ' ', str(s)).strip()
    return '' if t.lower() in ('nan', 'none', 'null') else t


def is_noise(text):
    t = norm_text(text)
    if len(t) <= 1:
        return True
    return any(r.match(t) for r in NOISE_RE)


def text_fingerprint(text):
    """去掉标点数字后的指纹，用于识别复读/水军刷屏"""
    t = re.sub(r'[\W\d_]+', '', norm_text(text))
    return hashlib.md5(t.encode()).hexdigest() if t else ''


# ============================================================
# 载入
# ============================================================
COLMAP = {
    '楼层': 'floor', '层级': 'level', '被回复者': 'parent_name', '评论ID': 'rpid',
    '昵称': 'user_name', 'UID': 'user_id', '等级': 'user_level',
    '评论内容': 'content', '点赞数': 'like', '点赞缺失': 'like_missing',
    '回复数': 'reply_count', 'IP属地': 'ip', '发布时间': 'ctime',
    '视频BVID': 'bvid', '视频标题': 'video_title', 'UP主': 'owner',
}


def load_one(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == '.json':
        obj = json.loads(path.read_text(encoding='utf-8'))
        meta = obj.get('meta', {})
        df = pd.DataFrame(obj.get('comments', []))
        rename = {'userName': 'user_name', 'userId': 'user_id', 'userLevel': 'user_level',
                  'parentName': 'parent_name', 'replyCount': 'reply_count', 'ipLocation': 'ip'}
        df = df.rename(columns=rename)
        for k, v in [('bvid', meta.get('bvid')), ('video_title', meta.get('title')),
                     ('owner', meta.get('owner'))]:
            df[k] = v
    else:
        df = pd.read_csv(path, encoding='utf-8-sig')
        df = df.rename(columns={k: v for k, v in COLMAP.items() if k in df.columns})

    for c in ['floor', 'level', 'parent_name', 'rpid', 'user_name', 'user_id',
              'user_level', 'content', 'like', 'like_missing', 'reply_count',
              'ip', 'ctime', 'bvid', 'video_title', 'owner']:
        if c not in df.columns:
            df[c] = ''
    if 'like_missing' in df.columns:
        df['like_missing'] = pd.to_numeric(df['like_missing'], errors='coerce').fillna(0).astype(int)
    else:
        df['like_missing'] = 0
    df['_src_file'] = path.name
    return df


def load_all(target: Path) -> pd.DataFrame:
    files = []
    if target.is_dir():
        files = sorted([p for p in target.iterdir()
                        if p.suffix.lower() in ('.csv', '.json') and not p.name.startswith('_')])
    elif target.exists():
        files = [target]
    if not files:
        sys.exit(f"没找到数据文件：{target}")

    print(f"读取 {len(files)} 个文件：{', '.join(f.name for f in files)}")
    df = pd.concat([load_one(f) for f in files], ignore_index=True)

    df['content'] = df['content'].map(norm_text)
    for c in ['ip', 'user_name', 'parent_name', 'video_title', 'owner']:
        if c in df.columns:
            df[c] = df[c].map(norm_text)
    df['like'] = pd.to_numeric(df['like'], errors='coerce').fillna(0).astype(int)
    df['reply_count'] = pd.to_numeric(df['reply_count'], errors='coerce').fillna(0).astype(int)
    df['user_level'] = pd.to_numeric(df['user_level'], errors='coerce')
    df['level_txt'] = df['level'].astype(str)
    df['is_sub'] = df['level_txt'].str.contains('二级|2')

    # 跨文件去重
    before = len(df)
    df = df[df['content'].str.len() > 0]
    mask = df['rpid'].astype(str).str.len() > 0
    df = pd.concat([df[mask].drop_duplicates(subset=['rpid']),
                    df[~mask].drop_duplicates(subset=['content', 'user_name'])],
                   ignore_index=True)
    print(f"去重：{before} → {len(df)}")
    return df


# ============================================================
# 清洗标记
# ============================================================
def mark(df: pd.DataFrame) -> pd.DataFrame:
    df['_noise'] = df['content'].map(is_noise)
    df['_fp'] = df['content'].map(text_fingerprint)

    # 复读处理：同一指纹出现 >=3 次视为复读组。
    # 不整组剔除，只保留一条代表 —— 但代表条目必须继承全组的点赞总和。
    #
    # 【为什么必须累计点赞】
    # 一条观点被复读 17 次、每条各有几十赞，真实声量是全组之和。
    # 只取组内最高值会系统性低估高频观点的影响力，
    # 而高频观点恰恰是最接近社区共识的那部分。这是分析里最不能丢的信号。
    df['_dup_n'] = 1
    df['_like_sum'] = df['like']        # 累计点赞（声量真值）
    df['_like_own'] = df['like']        # 该条自身点赞（保留原值，可追溯）
    df['_repeat'] = False

    valid_fp = df[df['_fp'] != '']
    fp_count = valid_fp['_fp'].value_counts()
    for fp in fp_count[fp_count >= 3].index:
        idx = df.index[df['_fp'] == fp]
        keeper = df.loc[idx, 'like'].idxmax()
        df.loc[idx.difference([keeper]), '_repeat'] = True
        df.loc[keeper, '_dup_n'] = len(idx)
        df.loc[keeper, '_like_sum'] = int(df.loc[idx, 'like'].sum())   # ← 全组累计

    # 疑似刷屏账号：同一用户 >=5 条且内容高度同质
    sus = set()
    for uid, g in df[df['user_id'].astype(str).str.len() > 0].groupby('user_id'):
        if len(g) >= 5 and g['_fp'].nunique() <= max(1, len(g) // 3):
            sus.add(uid)
    df['_spam_user'] = df['user_id'].isin(sus)

    df['_drop'] = df['_noise'] | df['_repeat'] | df['_spam_user']

    # 【点赞审计】被剔除的评论里如果混进了高赞条目，说明规则可能误杀。
    # 灌水词通常是低赞的；一条"前排"如果有 2000 赞，那它已经不是灌水，
    # 而是一个被社区高度认可的现象级发言，不该无声丢弃。
    dropped = df[df['_drop']]
    if len(dropped):
        thr = max(50, int(df['like'].quantile(0.90)) if len(df) > 10 else 50)
        df['_drop_highlike'] = df['_drop'] & (df['like'] >= thr) & (~df['_repeat'])
    else:
        df['_drop_highlike'] = False
    return df


def tag_dimensions(df: pd.DataFrame) -> pd.DataFrame:
    def hit(text, lex):
        t = str(text).lower()
        return [k for k, ws in lex.items() if any(w in t for w in ws)]
    df['_features'] = df['content'].map(lambda c: hit(c, FEATURE_LEXICON))
    df['_intent'] = df['content'].map(lambda c: hit(c, INTENT_LEXICON))
    return df


# ============================================================
# 摘要生成
# ============================================================
def build_digest(df: pd.DataFrame) -> str:
    L = []
    w = L.append
    kept = df[~df['_drop']]

    w("# B 站评论预处理摘要\n")
    w(f"> 生成于 {datetime.now():%Y-%m-%d %H:%M} · 供 LLM 分析使用\n")

    # --- 数据概况 ---
    w("## 一、数据概况\n")
    videos = df.groupby('bvid').agg(
        标题=('video_title', 'first'), UP主=('owner', 'first'), 评论数=('content', 'size')
    ).reset_index()
    w("| BVID | 标题 | UP主 | 采集条数 |")
    w("|---|---|---|---|")
    for _, r in videos.iterrows():
        w(f"| {r['bvid']} | {str(r['标题'])[:40]} | {r['UP主']} | {r['评论数']} |")
    w("")

    n_all, n_keep = len(df), len(kept)
    w(f"- 采集总量 **{n_all}** 条（一级 {int((~df['is_sub']).sum())} / 二级 {int(df['is_sub'].sum())}）")
    w(f"- 清洗后有效 **{n_keep}** 条（{n_keep/max(n_all,1):.0%}）")
    w(f"- 剔除：噪声灌水 {int(df['_noise'].sum())} · 复读合并 {int(df['_repeat'].sum())} · 疑似刷屏账号 {int(df['_spam_user'].sum())}")
    w("")

    # --- 数据质量：点赞覆盖率（移动端复制常漏点赞行）---
    miss_like = int(df['like_missing'].sum())
    if miss_like:
        cov = (n_all - miss_like) / max(n_all, 1)
        w("> ⚠️ **点赞数据缺口**：本批数据有 **%d** 条评论在源文档中**缺失点赞数**"
          "（覆盖率 %.0f%%）。\n"
          "> 声量（累计点赞）类指标仅基于有点赞的 %d 条计算，缺失点赞的评论"
          "仍参与**内容/维度/意向**等定性分析，但不计入声量加权。\n"
          "> 若要做严谨的声量排行，建议回到 B 站对其补采点赞。" %
          (miss_like, cov * 100, n_all - miss_like))
        w("")
    w("")

    # --- 点赞守恒校验：确认没有声量在清洗中凭空消失 ---
    like_all = int(df['like'].sum())
    like_kept = int(kept['_like_sum'].sum())
    like_lost = like_all - like_kept
    w("**点赞守恒校验**（声量是分析的权重基准，不能丢）：")
    w(f"- 原始点赞总量 **{like_all}** → 保留在有效样本中 **{like_kept}**（{like_kept/max(like_all,1):.1%}）")
    if like_lost > 0:
        lost_noise = int(df[df['_noise']]['like'].sum())
        lost_spam = int(df[df['_spam_user'] & ~df['_noise']]['like'].sum())
        w(f"- 流失 {like_lost}：噪声灌水 {lost_noise} · 刷屏账号 {lost_spam}")
        w("- 复读组的点赞已**全量累计**到代表条目上，未流失")
    w("")

    # --- 误杀预警 ---
    mis = df[df.get('_drop_highlike', False)]
    if len(mis):
        w("> ⚠️ **可能误杀**：以下评论被规则剔除，但点赞很高。灌水通常是低赞的，")
        w("> 高赞说明它已获社区认可，请人工复核是否该放回：")
        for _, r in mis.nlargest(10, 'like').iterrows():
            why = '噪声词' if r['_noise'] else ('刷屏账号' if r['_spam_user'] else '其他')
            w(f"> - [{int(r['like'])}赞 · 判定={why}] {r['content'][:80]}")
        w("")

    dups = kept[kept['_dup_n'] > 1].nlargest(10, '_like_sum')
    if len(dups):
        w("**被高频复读的观点**（复读即共识信号，声量已累计全组点赞）：")
        for _, r in dups.iterrows():
            w(f"- ×{int(r['_dup_n'])}次 · 累计 **{int(r['_like_sum'])}** 赞"
              f"（最高单条 {int(r['_like_own'])}）｜{r['content'][:70]}")
    w("")

    # --- 互动分布 ---
    w("## 二、互动分布\n")
    likes = kept['_like_sum']
    if len(likes):
        w(f"- 有效声量：总计 {int(likes.sum())} · 中位数 {int(likes.median())} · 最高 {int(likes.max())}")
        hi = int((likes >= 50).sum())
        w(f"- 高声量评论（≥50 赞）{hi} 条，占 {hi/max(n_keep,1):.1%} —— **分析权重应显著高于长尾**")
        # 声量集中度：判断是"少数人主导"还是"广泛共识"
        top10 = int(likes.nlargest(max(1, n_keep // 10)).sum())
        w(f"- 声量集中度：TOP 10% 的评论占据 **{top10/max(int(likes.sum()),1):.0%}** 的总点赞")
        w("  （占比越高，说明舆论越被少数几条高赞评论主导）")
    w("")

    # --- 时间演化 ---
    times = pd.to_datetime(kept['ctime'], errors='coerce').dropna()
    if len(times) > 5:
        w("### 时间分布\n")
        by_day = times.dt.strftime('%m-%d').value_counts().sort_index()
        w("| 日期 | 评论数 |")
        w("|---|---|")
        for d, c in by_day.head(15).items():
            w(f"| {d} | {c} |")
        w("")

    # --- IP 属地 ---
    ips = kept[kept['ip'].astype(str).str.len() > 0]['ip'].value_counts().head(10)
    if len(ips):
        w("### IP 属地 TOP10\n")
        w("| 属地 | 条数 |")
        w("|---|---|")
        for k, v in ips.items():
            w(f"| {k} | {v} |")
        w("")

    # --- 特性维度命中 ---
    w("## 三、产品特性维度命中（词典粗筛，需 LLM 复核）\n")
    fc = Counter()
    for fs in kept['_features']:
        fc.update(fs)
    if fc:
        w("| 维度 | 命中条数 | **累计声量** | 声量占比 |")
        w("|---|---|---|---|")
        # 按声量排序，不按条数 —— 5 条 3000 赞的意见，比 50 条 0 赞的更重要
        rows_ = []
        for k in fc:
            hit_rows = kept[kept['_features'].map(lambda fs: k in fs)]
            rows_.append((k, fc[k], int(hit_rows['_like_sum'].sum())))
        total_like = max(int(kept['_like_sum'].sum()), 1)
        for k, n, lk in sorted(rows_, key=lambda x: -x[2]):
            w(f"| {k} | {n} | **{lk}** | {lk/total_like:.1%} |")
        w("")
        w("> 排序依据是**累计声量**而非条数。若某维度条数少但声量高，")
        w("> 说明它是「少数人强烈关注」——往往比「多数人随口一提」更值得处理。")
    else:
        w("_未命中，可能是非消费电子品类，需 LLM 自行归纳维度_")
    w("")

    # --- 购买意向 ---
    w("## 四、购买意向信号（词典粗筛）\n")
    ic = Counter()
    for xs in kept['_intent']:
        ic.update(xs)
    if ic:
        w("| 信号 | 条数 | 累计声量 |")
        w("|---|---|---|")
        for k, v in ic.most_common():
            lk = int(kept[kept['_intent'].map(lambda xs: k in xs)]['_like_sum'].sum())
            w(f"| {k} | {v} | {lk} |")
    else:
        w("_未命中明显意向词_")
    w("")

    # --- 高声量 TOP（全量给 LLM） ---
    w("## 五、高声量评论 TOP 50（重点分析对象）\n")
    w("_声量 = 该观点累计点赞（含复读）；单条 = 最高单条点赞_\n")
    top = kept[~kept['is_sub']].nlargest(50, '_like_sum')
    for i, (_, r) in enumerate(top.iterrows(), 1):
        feat = '/'.join(r['_features']) or '-'
        dup = (f" · ×{int(r['_dup_n'])}复读(单条{int(r['_like_own'])})"
               if r['_dup_n'] > 1 else "")
        w(f"{i}. **[声量{int(r['_like_sum'])} · {r['reply_count']}回复 · {r['ip'] or '?'}{dup}]** "
          f"（维度:{feat}）{r['content'][:200]}")
    w("")

    # --- 争议候选：高声量且高回复 ---
    w("## 六、争议点候选（高声量 + 高回复，最可能是舆论战场）\n")
    ctrl = kept[(kept['_like_sum'] >= max(10, kept['_like_sum'].median())) & (kept['reply_count'] >= 5)]
    ctrl = ctrl.nlargest(20, 'reply_count')
    if len(ctrl):
        w("| # | 声量 | 回复 | 赞回比 | 内容 |")
        w("|---|---|---|---|---|")
        for i, (_, r) in enumerate(ctrl.iterrows(), 1):
            ratio = r['_like_sum'] / max(r['reply_count'], 1)
            # 赞回比低 = 争议大（很多人想说话而非单纯点赞）
            flag = '🔥争议' if ratio < 20 else ('认可' if ratio > 60 else '中性')
            w(f"| {i} | {int(r['_like_sum'])} | {int(r['reply_count'])} | "
              f"{ratio:.0f} {flag} | {r['content'][:80]} |")
        w("")
        w("> **赞回比**是判断争议的关键：比值低说明「想说话的人多于单纯点赞的人」，")
        w("> 意味着分歧激烈；比值高说明被广泛认可、无需争辩。")
    else:
        w("_无明显争议点_")
    w("")

    # --- 疑问清单候选 ---
    w("## 七、疑问句候选（信息缺口线索）\n")
    q = kept[kept['content'].str.contains(r'[?？]|请问|求问|有没有人知道|怎么|如何|能不能|值不值',
                                          regex=True, na=False)]
    q = q.nlargest(25, '_like_sum')
    for i, (_, r) in enumerate(q.iterrows(), 1):
        w(f"{i}. [声量{int(r['_like_sum'])}] {r['content'][:150]}")
    w("")

    # --- 全量正文 ---
    w("## 八、清洗后全量评论正文\n")
    w(f"_共 {n_keep} 条，格式：[声量|层级|属地|复读数] 内容_\n")
    w("```")
    for _, r in kept.sort_values('like', ascending=False).iterrows():
        lv = '↳' if r['is_sub'] else '●'
        dup = f"|x{int(r['_dup_n'])}" if r['_dup_n'] > 1 else ""
        w(f"[{int(r['_like_sum']):>5}|{lv}|{str(r['ip'] or '?')[:4]:<4}{dup}] {r['content'][:300]}")
    w("```")
    return '\n'.join(L)


# ============================================================
def main():
    ap = argparse.ArgumentParser(description='B 站评论预处理')
    ap.add_argument('input', nargs='?', default='data', help='CSV/JSON 文件或目录')
    ap.add_argument('--out', help='输出 digest 路径')
    args = ap.parse_args()

    base = Path(__file__).parent
    target = Path(args.input)
    if not target.is_absolute():
        target = base / target

    df = load_all(target)
    df = mark(df)
    df = tag_dimensions(df)

    ts = datetime.now().strftime('%m%d_%H%M')
    outdir = base / 'reports'
    outdir.mkdir(exist_ok=True)

    digest_path = Path(args.out) if args.out else outdir / f'_digest_{ts}.md'
    digest_path.write_text(build_digest(df), encoding='utf-8')

    # 清洗表保留原始 like 和累计声量两列，任何时候都能回溯
    clean_path = outdir / f'_clean_{ts}.csv'
    cols = ['bvid', 'video_title', 'floor', 'level', 'parent_name', 'user_name',
            'user_level', 'content', 'like', 'like_missing', '_like_sum', '_dup_n',
            'reply_count', 'ip', 'ctime', '_drop', '_noise', '_repeat', '_spam_user']
    out = df[[c for c in cols if c in df.columns]].rename(
        columns={'like': '原始点赞', 'like_missing': '点赞缺失', '_like_sum': '累计声量',
                 '_dup_n': '复读次数', '_drop': '已剔除', '_noise': '判定_噪声',
                 '_repeat': '判定_复读', '_spam_user': '判定_刷屏号'})
    out.to_csv(clean_path, index=False, encoding='utf-8-sig')

    like_all = int(df['like'].sum())
    like_kept = int(df[~df['_drop']]['_like_sum'].sum())
    print(f"\n✅ 摘要  → {digest_path}")
    print(f"✅ 清洗表 → {clean_path}  （含原始点赞 + 累计声量，可回溯）")
    print(f"   有效 {int((~df['_drop']).sum())} / 总计 {len(df)} 条")
    print(f"   点赞守恒：原始 {like_all} → 保留 {like_kept} "
          f"（{like_kept/max(like_all,1):.1%}）")
    if int(df.get('_drop_highlike', pd.Series(dtype=bool)).sum()):
        print(f"   ⚠️ 有 {int(df['_drop_highlike'].sum())} 条高赞评论被规则剔除，"
              f"摘要里已列出，请复核")


if __name__ == '__main__':
    main()
