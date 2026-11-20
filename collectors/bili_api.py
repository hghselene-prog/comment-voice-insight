#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B站公开 API 通用封装：匿名 cookie、WBI 签名、搜索/详情/相关/评论。

这是采集层的底座，其他脚本都 import 它。只调用浏览器匿名访问所需的公开接口，
不读取、不写入任何账号凭证（无 SESSDATA），因此受 B 站未登录态限流约束，
详见 README.md「平台限制」。
"""
import urllib.parse, urllib.request, json, time, hashlib, re, sys, http.cookiejar

HEAD = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com',
    'Accept': 'application/json, text/plain, */*',
}

# WBI 签名置换表（B站官方前端算法，稳定）
MIXIN_TAB = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43,
             5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16,
             24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59,
             6, 63, 57, 62, 11, 36, 20, 34, 44, 52]


def build_opener():
    """先访问首页拿 buvid3 等匿名 cookie，后续请求带上，降低 412 概率。"""
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    try:
        op.open(urllib.request.Request('https://www.bilibili.com', headers=HEAD),
                timeout=15).read()
    except Exception as e:
        print('  [warn] home cookie: %s' % e, file=sys.stderr)
    return op, cj


OP, CJ = build_opener()


def get(url, params=None, retries=3):
    """带重试的 GET，返回 dict；失败返回 None。"""
    if params:
        url += '?' + urllib.parse.urlencode(params)
    for i in range(retries):
        try:
            with OP.open(urllib.request.Request(url, headers=HEAD), timeout=15) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception:
            if i == retries - 1:
                return None
            time.sleep(0.5)


def get_wbi_keys():
    data = get('https://api.bilibili.com/x/web-interface/nav') or {}
    wbi = (data.get('data') or {}).get('wbi_img') or {}
    img = wbi['img_url'].rsplit('/', 1)[-1].split('.')[0]
    sub = wbi['sub_url'].rsplit('/', 1)[-1].split('.')[0]
    return img + sub


def wbi_sign(params):
    """给参数加 w_rid + wts 签名（部分接口需要，如 wbi/search）。"""
    mixin = ''.join(get_wbi_keys()[i] for i in MIXIN_TAB)[:32]
    params = dict(params)
    params['wts'] = int(time.time())
    query = urllib.parse.urlencode(dict(sorted(params.items())))
    params['w_rid'] = hashlib.md5((query + mixin).encode()).hexdigest()
    return params


def clean(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or '')).strip()


def search(keyword, page=1, order='click'):
    """WBI 搜索视频。注意：B站常对搜索接口返回 v_voucher 风控空结果，
    此时应改用 collect_related.py 的 related 扩散路径（见 README）。"""
    params = {'keyword': keyword, 'search_type': 'video', 'order': order,
              'page': page, 'web_location': '333.1007'}
    data = get('https://api.bilibili.com/x/web-interface/wbi/search/type',
               wbi_sign(params)) or {}
    if data.get('code') != 0:
        print('  [warn] search code=%s msg=%s' % (data.get('code'), data.get('message')),
              file=sys.stderr)
        return []
    return (data.get('data') or {}).get('result') or []


def view(bvid):
    return get('https://api.bilibili.com/x/web-interface/view', {'bvid': bvid})


def related(bvid):
    return get('https://api.bilibili.com/x/web-interface/archive/related', {'bvid': bvid})


def replies(aid, mode=3, next_=0, ps=20):
    """评论。mode=3 热门 / 2 时间。未登录态每视频只放少量热评（见 README）。"""
    return get('https://api.bilibili.com/x/v2/reply/main',
               {'oid': aid, 'type': 1, 'mode': mode, 'next': next_, 'ps': ps})
