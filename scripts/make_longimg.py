#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML → 微信可分享长图（PNG）+ PDF
============================================================
路径：weasyprint 渲染 PDF → pdftoppm 转位图 → PIL 纵向拼接

为什么不用截长屏：weasyprint 渲染稳定、无需浏览器、中文字体不会掉。
长图宽度固定 1241px（A4@150dpi），微信预览清晰度足够且不会因太宽被压缩。

用法：
    python3 make_longimg.py --html 报告.html --out-img 长图.png [--out-pdf 报告.pdf] [--dpi 150]
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--html', required=True)
    ap.add_argument('--out-img', required=True)
    ap.add_argument('--out-pdf')
    ap.add_argument('--dpi', type=int, default=150)
    a = ap.parse_args()

    html_path = Path(a.html).resolve()
    if not html_path.exists():
        sys.exit(f'找不到 HTML：{html_path}')

    tmp = Path(tempfile.mkdtemp(prefix='longimg_'))
    pdf_path = tmp / 'r.pdf'

    # 1) HTML → PDF
    try:
        from weasyprint import HTML
        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    except ImportError:
        sys.exit('需要 weasyprint：sudo pip3 install weasyprint')

    if a.out_pdf:
        Path(a.out_pdf).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(pdf_path, a.out_pdf)
        print(f"✅ PDF 完成 → {a.out_pdf}")

    # 2) PDF → 逐页 PNG
    if not shutil.which('pdftoppm'):
        sys.exit('需要 poppler-utils：sudo apt-get install -y poppler-utils')
    subprocess.run(['pdftoppm', '-png', '-r', str(a.dpi), str(pdf_path), str(tmp / 'pg')], check=True)
    pages = sorted(tmp.glob('pg-*.png'))
    if not pages:
        sys.exit('PDF 转图失败，未产出页面')

    # 3) 纵向拼接
    try:
        from PIL import Image
    except ImportError:
        sys.exit('需要 pillow：sudo pip3 install pillow')

    imgs = [Image.open(p).convert('RGB') for p in pages]
    W = max(i.width for i in imgs)
    H = sum(i.height for i in imgs)
    canvas = Image.new('RGB', (W, H), 'white')
    y = 0
    for im in imgs:
        canvas.paste(im, ((W - im.width) // 2, y))
        y += im.height

    Path(a.out_img).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(a.out_img, optimize=True)
    size_mb = Path(a.out_img).stat().st_size / 1024 / 1024
    print(f"✅ 长图完成 → {a.out_img}（{W}×{H}，{len(pages)} 页拼接，{size_mb:.1f} MB）")
    if size_mb > 9:
        print("   ⚠️ 超过 10MB 微信可能压缩，建议降低 --dpi 到 120")

    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
