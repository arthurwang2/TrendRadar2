---
name: tesla-daily-briefing-pro
description: 特斯拉上海交付团队「一站式」每日简报。用户提供日期（如 2026-05-22）或上传 TrendRadar JSON 文件时触发。自动完成：解析 JSON、新能源竞品/赛道筛选、强制屏蔽、联网核实升级权威信源、查询上海明日天气与工服、精选 Top 3，直接输出 V3 纯文本简报（可复制发微信群）。支持触发词：/tesla-daily-briefing-pro、发 JSON 生成简报、筛选新闻并生成简报。
---

# Tesla Daily Briefing Pro（V3 融合版）

## 何时使用
- 用户上传包含新闻标题/摘要的 JSON 文件（TrendRadar `trendradar_full_content.json` 格式），并要求生成某日「每日公开信息简报」
- 用户输入 `/tesla-daily-briefing-pro`、`发 JSON 生成简报` 或「筛选新闻并生成简报」+ 日期
- 仅提供日期且无 JSON 时：自动尝试从 GitHub Pages 拉取：
  - 原始条目：`https://arthurwang2.github.io/TrendRadar2/report/daily-json/YYYY-MM-DD.json`
  - **TrendRadar 已跑通的 AI 分析（硅基 7B，不另付费）**：`https://arthurwang2.github.io/TrendRadar2/report/meta/ai_analysis_latest.json` 或 `ai_analysis_YYYY-MM-DD.json`
  - V3 分类（若有）：`https://arthurwang2.github.io/TrendRadar2/report/meta/strict_v3_latest.json`
  若 JSON 拉取失败则按 V3 规则联网搜索近 2 日资讯后生成简报

## 输入
- 简报日期（必填）：用户指定的「今天」日期（格式 YYYY-MM-DD 或自然语言），用于标题与新闻时效判断
- 新闻 JSON（推荐）：爬虫抓取的条目列表，优先使用 Action 自动发布的每日 JSON
- 城市：默认上海（天气与工服）

## 端到端流程（必须严格按序执行）
1. **解析 JSON**  
   遍历全部条目，提取 title；有 summary / created_at / url / source 则一并记录。  
   不得直接沿用爬虫中的来源名称作为最终信源。

2. **分类筛选**  
   **第一类：中国新能源竞品动态**（满足其一即可收录）  
   - 竞品新车/技术发布、价格、渠道、出海、交付、产能  
   - 中国新能源车销量、渗透率、结构变化  
   - 与一线交付理解竞争有关的信息  
   主体示例见 `reference.md`「第一类主体列表」。

   **第二、三类：Tesla 相关赛道（非整车为主）**  
   优先：Optimus / Megapack / Supercharger / 已公开产能；智能驾驶与 Robotaxi（非 Tesla 主体或行业技术）；动力电池与储能；补能生态；人形机器人/具身智能；供应链与制造效率；海外充电/储能基础设施。  
   不选：纯整车销量复述、竞品车型发布堆砌、价格战、新能源车市场空泛复述。

3. **强制屏蔽**（一律不进入 Top 3，也不写入正文）  
   详见 `reference.md`「强制屏蔽清单」（事故伤亡、诉讼处罚、股价涨跌、拉踩标题、无日期自媒体爆料、旧闻翻炒、FSD/Robotaxi/未发布车型确定式推测等 20+ 条规则）。

4. **联网核实与信源升级**（每条拟入选新闻必做）  
   - 用标题关键词 web_search 查证，发布时间以网络可查证的首次发布为准，优先近 2 日内。  
   - 信源升级为：新华社、人民日报、央视、财联社、证券时报、盖世汽车、中国汽车报、品牌官网/官微等。  
   - 查无权威报道或 7 天以前首发 → 丢弃。

5. **天气与工服（必做）**  
   联网查询上海、简报日期次日天气预报（现象、温度区间、风向风力、降水描述）。  
   按次日星期匹配工服颜色规则（见 `reference.md`「工服颜色表」）：  
   周一/周四 = 黑色工服；周二/周五 = 金色工服；周三/周六/周日 = 红色工服。  
   生成穿衣指南、出行提醒各一句（参考 html.py 中的 genHint 逻辑）。

6. **精选 Top 3 并输出 V3 简报**  
   - 第 1 条：必须为第一类竞品/市场动态  
   - 第 2、3 条：必须为第二/三类非整车赛道（最多 1 条可为强相关市场数据，其余避开车型发布堆砌）  
   - 三条须覆盖至少两个赛道  
   - 每条格式：标题 + 一句话点评（帮一线理解趋势） + 权威来源 + 日期  
   - 严格使用 `reference.md` 中的「V3 输出模板」，纯文本、无 Markdown 代码块、无多余说明。

7. **自检报告**  
   列出 V3 检查项 1–20（见 `reference.md`），逐项写「通过」或说明例外。

## 内容原则
最新、真实、有用、不拉踩、有趋势、可群发。

## 禁止在简报正文外
- 不要输出长篇筛选表、待核实清单（除非用户明确要求「只要筛选结果」）
- 用户只要筛选不要简报时：输出分类列表 + 屏蔽统计即可，不生成天气块

## 工具使用
- 解析 JSON：优先使用用户上传文件或从 GitHub Pages 自动拉取（https://arthurwang2.github.io/TrendRadar2/report/daily-json/{date}.json）
- 核实与天气：使用 web_search / 网页抓取工具
- 不得编造来源或日期

## 参考资料
- 完整分类主体列表、强制屏蔽清单、工服颜色表、V3 检查项 1-20、输出模板：`reference.md`
- 工服穿衣建议生成逻辑与网页版一致（来自 trendradar/report/html.py）

## 示例触发
- “/tesla-daily-briefing-pro 2026-05-22”
- 把今天的 JSON 文件拖进来 + “给 5 月 22 日生成简报”
- “用 tesla-daily-briefing-pro 自动拉取最新 JSON 生成简报”
