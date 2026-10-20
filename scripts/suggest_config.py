#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词典起草助手：扫描评论高频词 → 给 LLM 一份定制 config 的原料
============================================================
不自动生成 config.json（机器分不清「等」是期待还是观望），
只把「按声量加权的高频词 + 高赞长评样本」摆出来，让分析者据此定制词典。

用法：
    python3 suggest_config.py --csv reports/_clean_xxx.csv [--topn 80]
"""
import argparse
import re
import sys
from collections import Counter

try:
    import pandas as pd
except ImportError:
    sys.exit("需要 pandas：sudo pip3 install pandas")

# 停用词：这些词高频但没有分析价值
STOP = set("""
的 了 是 我 你 他 她 它 们 这 那 有 在 和 就 都 也 不 人 一个 什么 怎么 这个 那个 但是 因为 所以
还 要 会 能 说 看 想 到 去 来 好 很 太 更 最 没 别 把 被 给 让 对 从 用 做 出 上 下 中 里 个 些
啊 吧 呢 吗 哦 嗯 呀 哈 啦 嘛 哟 咯 唉 额 emmm 然后 而且 其实 感觉 觉得 应该 可能 已经 现在 还是
真的 确实 反正 反而 完全 直接 各种 一样 一直 只是 只能 如果 虽然 不过 而是 以及 或者 这样 那样
自己 大家 东西 时候 问题 情况 方面 时间 现在 之前 之后 目前 基本 主要 特别 非常 比较 有点 一点
知道 发现 看到 听说 记得 希望 需要 可以 应该 必须 一定 肯定 估计 大概 差不多 左右 起来 下来
""".split())

WORD_RE = re.compile(r'[\u4e00-\u9fa5]{2,6}|[A-Za-z][A-Za-z0-9+\-.]{1,14}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--topn', type=int, default=80)
    a = ap.parse_args()

    df = pd.read_csv(a.csv)
    if '已剔除' in df.columns:
        df = df[df['已剔除'] == False]
    if '累计声量' not in df.columns:
        df['累计声量'] = df.get('原始点赞', 1)
    df = df.dropna(subset=['content'])

    # 声量加权词频：一条 900 赞的评论，它的词比 1 赞的重要得多
    weighted, plain = Counter(), Counter()
    for _, r in df.iterrows():
        vol = max(int(r['累计声量']) if pd.notna(r['累计声量']) else 0, 0)
        words = {w.lower() for w in WORD_RE.findall(str(r['content'])) if w.lower() not in STOP}
        for w in words:
            weighted[w] += vol + 1     # +1 保证零赞评论也有基础权重
            plain[w] += 1

    print("=" * 68)
    print(f"高频词 TOP{a.topn}（按声量加权，格式：词 / 声量 / 出现条数）")
    print("=" * 68)
    for i, (w, v) in enumerate(weighted.most_common(a.topn), 1):
        print(f"{w:<14} {v:>7,}  {plain[w]:>4}条", end='   ' if i % 3 else '\n')
    print()

    print("=" * 68)
    print("高赞长评 TOP20（判断语气/梗/态度的主要依据）")
    print("=" * 68)
    long_c = df[df['content'].str.len() > 25].nlargest(20, '累计声量')
    for _, r in long_c.iterrows():
        print(f"[{int(r['累计声量']):>5,}] {str(r['content']).strip()[:110]}")

    print()
    print("=" * 68)
    print("下一步：据此定制 config.json 的 sentiment / themes / intent 三套词典")
    print("注意：高频不等于有分析价值，要挑能区分立场的词，别把通用词塞进去")
    print("=" * 68)


if __name__ == '__main__':
    main()
