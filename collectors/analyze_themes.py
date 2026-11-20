#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤3：评论主题聚类 + 归一化声量占比（跨代对比的基础）。

关键方法：绝对声量受播放量影响巨大（头部视频 5000 赞 vs 新品 600 赞），
跨组横比必须用「组内归一化占比」——每组内主题声量 / 该组总声量 = 100%，
否则会得出「一代热度远高于新品」这种由样本量造成的假结论。

用法：
  python3 analyze_themes.py config.json out/comments.json out/comments_tagged.json
"""
import sys, json
from collections import Counter

config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
comments_path = sys.argv[2] if len(sys.argv) > 2 else 'out/comments.json'
out_path = sys.argv[3] if len(sys.argv) > 3 else 'out/comments_tagged.json'
cfg = json.load(open(config_path, encoding='utf-8'))
THEMES = cfg['themes']
data = json.load(open(comments_path, encoding='utf-8'))


def classify(msg):
    m = msg.lower()
    hits = [theme for theme, kws in THEMES.items() if any(k.lower() in m for k in kws)]
    return hits or ['其他']


def main():
    groups = sorted({v['tag'] for v in data})
    tagged = {}
    for g in groups:
        items = []
        for v in data:
            if v['tag'] != g:
                continue
            for c in v['comments']:
                items.append({'msg': c['msg'], 'like': c['like'],
                              'themes': classify(c['msg']),
                              'video': v['title'], 'url': v['url'], 'bv': v['bvid']})
        tagged[g] = items

        voice = Counter()
        cnt = Counter()
        for c in items:
            for t in c['themes']:
                voice[t] += c['like']
                cnt[t] += 1
        total = sum(c['like'] for c in items) or 1
        print('\n' + '=' * 55)
        print('%s: %d 条评论 / 声量 %d' % (g, len(items), total))
        print('=' * 55)
        for t, v in voice.most_common(8):
            print('  %-18s 声量%6d (%4.1f%%) 提及%3d条' % (t, v, v / total * 100, cnt[t]))

    json.dump(tagged, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('\nDONE -> %s' % out_path)


if __name__ == '__main__':
    main()
