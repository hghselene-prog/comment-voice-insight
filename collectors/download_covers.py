#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步骤4（可选）：下载核心视频封面作为报告配图。

两个必踩的坑（已在本脚本处理）：
1. hdslb.com 直接 curl 会 403/返回 0 字节 → 必须带完整浏览器 header（UA+Referer+Accept）。
2. i2.hdslb.com 用 http 会被拦 → 强制 https。

用法：
  python3 download_covers.py out/comments.json out/videos.json covers/
"""
import sys, json, os, subprocess, time
import bili_api as b

comments_path = sys.argv[1] if len(sys.argv) > 1 else 'out/comments.json'
videos_path = sys.argv[2] if len(sys.argv) > 2 else 'out/videos.json'
out_dir = sys.argv[3] if len(sys.argv) > 3 else 'covers/'

comments = json.load(open(comments_path, encoding='utf-8'))
videos = json.load(open(videos_path, encoding='utf-8'))
target_bv = {c['bvid'] for c in comments}
for v in sorted(videos, key=lambda x: -x['view']):
    if len(target_bv) >= 24:
        break
    if v['view'] >= 30000:
        target_bv.add(v['bvid'])

os.makedirs(out_dir, exist_ok=True)
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
HEADERS = ['-H', 'User-Agent: ' + UA, '-H', 'Referer: https://www.bilibili.com/',
           '-H', 'Accept: image/avif,image/webp,image/apng,image/*,*/*;q=0.8']

manifest = []
for v in videos:
    if v['bvid'] not in target_bv:
        continue
    bv = v['bvid']
    try:
        d = b.view(bv)
        if not d or d.get('code') != 0:
            continue
        pic = (d['data']['pic'] or '').replace('http://', 'https://')
        name = '%s_%s.jpg' % (v.get('cat') or 'video', bv)
        dest = os.path.join(out_dir, name)
        subprocess.run(['curl', '-sL', '--max-time', '20'] + HEADERS +
                       [pic, '-o', dest], capture_output=True)
        sz = os.path.getsize(dest) if os.path.exists(dest) else 0
        if sz > 3000:
            manifest.append({'file': name, 'bv': bv, 'title': v['title'],
                             'tag': v.get('cat'), 'view': v['view'], 'url': v['url']})
            print('OK %s %dKB | %s' % (name, sz // 1024, v['title'][:35]), flush=True)
        time.sleep(0.1)
    except Exception as e:
        print('ERR %s %s' % (bv, str(e)[:40]), flush=True)

json.dump(manifest, open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=2)
print('总封面:', len(manifest))
