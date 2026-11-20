#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤2：按分类 + 代际挑选高分视频，抓取热门评论，落盘 comments.json。

平台限制：未登录态评论接口每视频只放少量热评（实测 3 条），WBI 签名、换 UA、
游标翻页均无法突破——这是 B站当前策略，需账号 cookie 才能拿全量。
因此本工具产出是「方向性洞察」，不是精确民意统计。详见 README.md。

用法：
  python3 fetch_comments.py config.json out/videos.json out/comments.json
"""
import sys, json, time
import bili_api as b

config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
videos_path = sys.argv[2] if len(sys.argv) > 2 else 'out/videos.json'
out_path = sys.argv[3] if len(sys.argv) > 3 else 'out/comments.json'
cfg = json.load(open(config_path, encoding='utf-8'))
videos = json.load(open(videos_path, encoding='utf-8'))
PICK = cfg.get('comment_pick', {})


def bucket(cat, date):
    """按 date_buckets 规则给视频打代际标签；未命中返回 cat 本身。"""
    rules = cfg.get('date_buckets', {}).get(cat, {})
    for label, prefixes in rules.items():
        if any(date.startswith(p) for p in prefixes):
            return label
    return cat


def pick_targets():
    targets = []
    for base_cat, n in PICK.get('per_group', {}).items():
        # 若 base_cat 有代际细分，按细分各自取；否则直接按 cat 取
        sub_rules = cfg.get('date_buckets', {}).get(base_cat, {})
        if sub_rules:
            for label in sub_rules:
                pool = [v for v in videos if bucket(v['cat'], v['date']) == label]
                pool.sort(key=lambda x: -x.get(PICK.get('sort_by', 'reply'), 0))
                targets += [(v, label) for v in pool[:n]]
        else:
            pool = [v for v in videos if v['cat'] == base_cat]
            pool.sort(key=lambda x: -x.get(PICK.get('sort_by', 'reply'), 0))
            targets += [(v, base_cat) for v in pool[:n]]
    return targets


def main():
    targets = pick_targets()
    print('目标视频:', {t[1]: sum(1 for x in targets if x[1] == t[1]) for t in targets},
          file=sys.stderr)
    result = []
    for v, tag in targets:
        aid = v.get('aid')
        if not aid:
            print('  SKIP %s 无aid' % v['bvid'], file=sys.stderr)
            continue
        allc, seen = [], set()
        for page in range(3):
            d = b.replies(aid, mode=3, next_=page)
            if not d or d.get('code') != 0:
                break
            replies = (d.get('data') or {}).get('replies') or []
            if page == 0:
                replies = ((d.get('data', {}).get('top') or {}).get('replies') or []) + replies
            for r in replies:
                rid = r.get('rpid')
                if rid in seen:
                    continue
                seen.add(rid)
                msg = b.clean((r.get('content') or {}).get('message', ''))
                if not msg:
                    continue
                allc.append({'name': (r.get('member') or {}).get('uname', ''),
                             'msg': msg, 'like': r.get('like', 0), 'time': r.get('ctime', 0)})
            if (d.get('data', {}).get('cursor') or {}).get('is_end'):
                break
            time.sleep(0.2)
        result.append({
            'bvid': v['bvid'], 'title': v['title'], 'tag': tag,
            'view': v['view'], 'like': v['like'], 'author': v['author'],
            'date': v['date'], 'url': v['url'],
            'ccount': len(allc), 'voice': sum(c['like'] for c in allc),
            'comments': allc,
        })
        print('  %-12s 评%3d 声量%6d | %s' % (tag, len(allc), sum(c['like'] for c in allc),
                                             v['title'][:36]), file=sys.stderr, flush=True)

    json.dump(result, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('\nDONE %d 视频 / %d 条评论 -> %s' %
          (len(result), sum(r['ccount'] for r in result), out_path), file=sys.stderr)


if __name__ == '__main__':
    main()
