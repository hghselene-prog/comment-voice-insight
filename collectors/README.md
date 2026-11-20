# 采集层（collectors/）

原 skill 的输入假设是「用户已拿到评论导出稿（Word/CSV）」。但很多时候你手上只有**产品名**，需要先从 B 站把高分视频和评论采下来——这一层补齐的就是这个前置环节。

> 本层只调用 B 站**匿名公开接口**，不读取、不写入任何账号凭证（无 SESSDATA）。因此受未登录态限流约束，产出定位是**方向性洞察**，不是精确民意统计。

## 四步流水线

```bash
cd collectors
cp config.example.json config.json      # 改成你的品类词表（见下）

# 1. related 扩散采集视频 → out/videos.json
python3 collect_videos.py config.json out/videos.json

# 2. 挑高分视频抓评论 → out/comments.json
python3 fetch_comments.py config.json out/videos.json out/comments.json

# 3. 主题聚类 + 归一化占比 → out/comments_tagged.json
python3 analyze_themes.py config.json out/comments.json out/comments_tagged.json

# 4.（可选）下载封面做报告配图 → covers/
python3 download_covers.py out/comments.json out/videos.json covers/

# 之后把 out/comments.json 交给主流水线：
#   parse_docx.py 那步可跳过，直接 prep.py → config.json → build_data.py → 四件套
```

依赖：仅 Python 标准库 + `curl`（下载封面用）。无需 pip 安装。

## 各脚本职责

| 脚本 | 做什么 | 关键设计 |
|---|---|---|
| `bili_api.py` | API 底座：匿名 cookie、WBI 签名、search/view/related/replies | 先访问首页拿 buvid3 cookie 降 412；所有请求带 Referer |
| `collect_videos.py` | 从种子 BV 做 related BFS 扩散 | **不用搜索接口**（常返回 v_voucher 风控空结果）；复用 related 自带 stat，不逐条调 view，避免请求爆炸 |
| `fetch_comments.py` | 按分类+代际挑视频，抓热评 | 代际按发布日期切分；每条评论带点赞数（声量权重）与 parent 视频 URL（可溯源） |
| `analyze_themes.py` | 主题聚类 + 组内归一化占比 | 主题可多命中；**跨代横比必须用归一化占比**，绝对声量受播放量影响不可比 |
| `download_covers.py` | 下载视频封面 | 完整浏览器 header 绕过 hdslb 403；强制 https；增量保存防超时中断 |

## 配置要点（`config.json`）

词表就是判断层，**词表质量直接决定采集纯度**：

- `seeds`：先用网页搜索 `产品名 site:bilibili.com/video` 找 3-5 个高播放真机视频当种子，种子选错后面全歪。
- `context_keywords` + `exclude_keywords`：领域准入 + 排噪。真实踩坑——分析「折叠电脑」时，三折叠**手机**（Mate XT）大量混入，必须靠这对词表切开。
- `groups`：每组 `match_any` 命中即归入；`signals` 用于两组都不命中时的决胜打分。
- `date_buckets`：同一产品分代（一代/二代/新品）时，按发布日期前缀切分，这是跨代对比的基础。
- `themes`：聚类词典，按品类定制。分析汽车却用平板的「芯片/生态」词典 = 垃圾结果。

完整示例见 `config.example.json`（MateBook Fold 三代对比的真实配置）。

## 平台限制（务必写进报告）

| 限制 | 表现 | 应对 |
|---|---|---|
| 搜索风控 | wbi search 返回 `v_voucher` / 空结果 | 走 related 扩散，不依赖搜索 |
| 评论只放 3 条 | 未登录态每视频仅返回少量热评，`all_count` 虽显示几千但翻页无效 | WBI 签名、换 UA、游标翻页均无效（已逐一验证）；需账号 cookie 才能拿全量，本工具不接入凭证 |
| 412 / 超时 | 高频请求被拦 | 内置重试 + sleep；采集分批跑，每 15 个访问增量落盘 |

因此本层产出适合回答「**用户在吵什么、情绪什么调、几代之间怎么变**」，不适合回答「精确百分之多少的用户认为 X」。

## 跨代对比方法论

采集完多组数据要做代际对比时，见 [`../references/crossgen-analysis.md`](../references/crossgen-analysis.md)——归一化占比、心态演进链、口径声明都在那里。
