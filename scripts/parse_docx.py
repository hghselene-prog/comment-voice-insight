#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B 站移动端 Word 评论文档 → 标准 CSV 解析器
============================================================
把用户从 B 站 App 复制进 Word 的评论解析成 prep.py 能直接吃的 CSV。

文档实测存在两种块结构（复制产物的差异）：
  Type-1 : 内容 / 日期 / 点赞 / 回复            ← 有点赞数
  Type-2 : 内容 / 日期 / 回复                  ← 点赞行缺失（约占 42%）

处理方式：
  - 用「回复」作为每条评论的可靠终结符（全文档 1121 条均有）。
  - 点赞取日期后第一行；若非数字则判定为缺失（like=0，点赞缺失=1）。
  - 「共N条回复，/点击查看」回填到父评论的 回复数。
  - 「NO. 000272」作为代理 评论ID；含 NO. 元数据判定为二级（回复）评论。
  - UID / 等级 / IP 属地移动端复制本就没有，留空。

用法：
    python3 parse_docx.py <评论.docx> [--bvid BVxxx] [--title 标题] [--owner UP]
"""

import argparse
import csv
import re
import sys
from pathlib import Path

try:
    from docx import Document
except ImportError:
    sys.exit("需要 python-docx：sudo pip3 install python-docx")

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$')
HEADER_TOKENS = {'评论', '最热', '最新'}

# 视频元信息（移动端 docx 不含，由调用方/上下文提供；此处给默认占位）
DEFAULT_META = {
    'bvid': 'BV1g5m4ByE2B',
    'title': '华为 MatePad Edge 鸿蒙二合一平板 评测',
    'owner': '笔吧评测室',
}

LIKE_RE = re.compile(r'^[\d.]+(万|w|W)?\+?$')


def parse_like(s: str) -> int:
    """点赞数：支持纯数字、'1.2万'、'9999+' 等写法。非点赞文本返回 None。"""
    s = s.strip()
    if not s or not LIKE_RE.match(s):
        return None
    wan = 10000 if ('万' in s or 'w' in s.lower()) else 1
    s = re.sub(r'[^0-9.]', '', s)
    try:
        return int(float(s) * wan)
    except ValueError:
        return None


def parse_docx(path: Path, meta: dict):
    d = Document(str(path))
    lines = [p.text.strip() for p in d.paragraphs]
    lines = [l for l in lines if l != '']          # 去掉整段空白
    n = len(lines)

    comments = []
    i = 0

    # 跳过文件头：评论 / 5142(总数) / 最热 / 最新
    while i < n and (lines[i] in HEADER_TOKENS or
                     (lines[i].isdigit() and i < 20)):
        i += 1

    cur = None
    user_idx = -1

    while i < n:
        line = lines[i]

        # —— 寻找下一条评论的昵称 ——
        if cur is None:
            if DATE_RE.match(line):          # 异常：还没拿到昵称就遇到日期，跳过
                i += 1
                continue
            cur = {'user_name': line}
            user_idx = i
            i += 1
            continue

        # —— 命中日期：定稿当前评论 ——
        if DATE_RE.match(line):
            di = i
            content = lines[di - 1].strip() if di - 1 > user_idx else ''

            # 点赞：日期后第一行若是数字则采信，否则缺失
            like_raw = lines[di + 1] if di + 1 < n else ''
            like = parse_like(like_raw)
            like_missing = like is None
            like = like or 0

            # 「回复」按钮位置：Type-1 在 di+2，Type-2（无点赞）在 di+1
            if di + 1 < n and lines[di + 1] == '回复':
                reply_pos = di + 1
            elif di + 2 < n and lines[di + 2] == '回复':
                reply_pos = di + 2
            else:
                reply_pos = di + 1

            # 元数据（昵称与内容之间）：取 NO. 代理ID，判定二级评论
            meta_lines = lines[user_idx + 1: di - 1]
            rpid = ''
            level = '1'
            for j, m in enumerate(meta_lines):
                if m == 'NO.' and j + 1 < len(meta_lines):
                    rpid = meta_lines[j + 1].strip()
                    level = '2'
                    break

            cur.update({
                'content': content,
                'ctime': line,
                'like': like,
                'like_missing': 1 if like_missing else 0,
                'rpid': rpid,
                'level': level,
                'reply_count': 0,
            })
            comments.append(cur)
            cur = None

            # 落到「回复」之后的那一行
            i = reply_pos + 1
            # 处理紧随的「共N条回复，/点击查看」标记（属于刚结束的评论）
            if i < n and '条回复' in lines[i]:
                m = re.search(r'共(\d+)条回复', lines[i])
                if m:
                    comments[-1]['reply_count'] = int(m.group(1))
                i += 1
                if i < n and lines[i] == '点击查看':
                    i += 1
            continue

        # 其它行（元数据 / 内容）：暂存，遇到日期再定稿
        i += 1

    rows = []
    for c in comments:
        rows.append({
            '楼层': '',
            '层级': c['level'],
            '被回复者': '',
            '评论ID': c['rpid'],
            '昵称': c['user_name'],
            'UID': '',
            '等级': '',
            '评论内容': c['content'],
            '点赞数': c['like'],
            '点赞缺失': c['like_missing'],
            '回复数': c['reply_count'],
            'IP属地': '',
            '发布时间': c['ctime'],
            '视频BVID': meta['bvid'],
            '视频标题': meta['title'],
            'UP主': meta['owner'],
        })
    return rows


def main():
    ap = argparse.ArgumentParser(description='B 站移动端 Word 评论 → CSV')
    ap.add_argument('docx', help='评论 .docx 路径')
    ap.add_argument('--bvid')
    ap.add_argument('--title')
    ap.add_argument('--owner')
    ap.add_argument('--out', help='输出 CSV 路径（默认 data/<bvid>.csv）')
    args = ap.parse_args()

    meta = dict(DEFAULT_META)
    if args.bvid:
        meta['bvid'] = args.bvid
    if args.title:
        meta['title'] = args.title
    if args.owner:
        meta['owner'] = args.owner

    rows = parse_docx(Path(args.docx), meta)
    if not rows:
        sys.exit("⚠️ 未解析到任何评论，请检查文档结构")

    base = Path(__file__).parent
    out = Path(args.out) if args.out else base / 'data' / f"{meta['bvid']}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    cols = ['楼层', '层级', '被回复者', '评论ID', '昵称', 'UID', '等级',
            '评论内容', '点赞数', '点赞缺失', '回复数', 'IP属地', '发布时间',
            '视频BVID', '视频标题', 'UP主']
    with out.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # ---- 自检 ----
    l1 = sum(1 for r in rows if r['层级'] == '1')
    l2 = sum(1 for r in rows if r['层级'] == '2')
    with_no = sum(1 for r in rows if r['评论ID'])
    with_rep = sum(1 for r in rows if r['回复数'] > 0)
    miss_like = sum(1 for r in rows if r['点赞缺失'])
    have_like = len(rows) - miss_like
    print(f"✅ 解析 {len(rows)} 条 → {out}")
    print(f"   一级 {l1} / 二级 {l2} · 代理ID {with_no} · 子回复数 {with_rep}")
    print(f"   ⚠️ 点赞数据：{have_like} 条有 / {miss_like} 条缺失"
          f"（覆盖率 {have_like/max(len(rows),1):.0%}）")
    print("\n--- 前 3 条样本 ---")
    for r in rows[:3]:
        flag = ' [点赞缺失]' if r['点赞缺失'] else ''
        print(f"  [{r['层级']}级|{r['点赞数']}赞|{r['回复数']}回复|id={r['评论ID'] or '-'}] "
              f"{r['昵称']}: {r['评论内容'][:36]}{flag}")


if __name__ == '__main__':
    main()
