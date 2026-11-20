#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤1：从种子 BV 做 related 扩散，采集相关视频并按 config 词表分类。

为什么不用搜索接口：B站 wbi 搜索常返回 v_voucher 风控空结果，related 扩散稳定得多。
直接用 related 返回的 stat，不逐条调 view，避免请求量爆炸触发 412/超时。

用法：
  python3 collect_videos.py config.json out/videos.json
"""
import sys, json, time
import bili_api as b

config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
out_path = sys.argv[2] if len(sys.argv) > 2 else 'out/videos.json'
cfg = json.load(open(config_path, encoding='utf-8'))

SEEDS = cfg['seeds']
MIN_VIEW = cfg.get('min_view', 5000)
MAX_VISIT = cfg.get('max_visit', 120)
CTX = cfg['context_keywords']
EXCLUDE = cfg.get('exclude_keywords', [])
GROUPS = cfg['groups']
FALLBACK = cfg.get('fallback_group')


def classify(title, desc):
    t = (title + ' ' + desc).lower()
    if not any(k.lower() in t for k in CTX):
        return None
    if any(e.lower() in t for e in EXCLUDE):
        return None
    scores = {}
    for g, rule in GROUPS.items():
        if any(k.lower() in t for k in rule['match_any']):
            return g  # match_any 命中即归入，优先级最高
        scores[g] = sum(1 for k in rule.get('signals', []) if k.lower() in t)
    best = max(scores, key=scores.get) if scores else None
    if best and scores[best] > 0:
        return best
    return FALLBACK


def norm(it):
    st = it.get('stat') or {}
    title = b.clean(it.get('title', ''))
    desc = b.clean(it.get('desc', ''))[:160]
    bv = it.get('bvid')
    pub = it.get('pubdate', 0)
    import datetime
    try:
        date = datetime.datetime.fromtimestamp(pub).strftime('%Y-%m-%d')
    except Exception:
        date = '?'
    return {
        'bvid': bv, 'aid': it.get('aid'), 'title': title,
        'author': (it.get('owner') or {}).get('name', ''),
        'view': st.get('view', 0) or 0, 'like': st.get('like', 0) or 0,
        'reply': st.get('reply', 0) or 0, 'favorite': st.get('favorite', 0) or 0,
        'pubdate': pub, 'date': date, 'cat': classify(title, desc),
        'desc': desc, 'url': 'https://www.bilibili.com/video/%s' % bv,
    }


def main():
    import os
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    videos, seen, queue, visited = {}, set(), list(SEEDS), 0

    for s in SEEDS:
        d = b.view(s)
        if d and d.get('code') == 0:
            dt = d['data']
            it = {'bvid': s, 'aid': dt['aid'], 'title': dt['title'],
                  'owner': dt['owner'], 'stat': dt['stat'],
                  'pubdate': dt['pubdate'], 'desc': dt.get('desc', '')}
            videos[s] = norm(it)
        seen.add(s)

    while queue and visited < MAX_VISIT:
        bv = queue.pop(0)
        visited += 1
        d = b.related(bv)
        if not d or d.get('code') != 0:
            continue
        for it in (d.get('data') or [])[:18]:
            rbv = it.get('bvid')
            if not rbv or rbv in seen:
                continue
            seen.add(rbv)
            r = norm(it)
            if r['cat']:
                videos[rbv] = r
                if len(queue) < MAX_VISIT * 2:
                    queue.append(rbv)
        if visited % 15 == 0:
            flush(videos, out_path)
            print('visited=%d kept=%d' % (visited, len(videos)), file=sys.stderr, flush=True)
        time.sleep(0.1)

    flush(videos, out_path)
    print('\nDONE visited=%d kept=%d -> %s' % (visited, len(videos), out_path),
          file=sys.stderr, flush=True)


def flush(videos, out_path):
    items = sorted([v for v in videos.values() if v['cat'] and v['view'] >= MIN_VIEW],
                   key=lambda x: -x['view'])
    json.dump(items, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
