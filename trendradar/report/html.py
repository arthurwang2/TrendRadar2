# coding=utf-8
"""
HTML 报告渲染模块

提供 HTML 格式的热点新闻报告生成功能
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from trendradar.report.helpers import html_escape
from trendradar.utils.time import convert_time_for_display
from trendradar.ai.formatter import render_ai_analysis_html_rich


def render_html_content(
    report_data: Dict,
    total_titles: int,
    mode: str = "daily",
    update_info: Optional[Dict] = None,
    *,
    region_order: Optional[List[str]] = None,
    get_time_func: Optional[Callable[[], datetime]] = None,
    rss_items: Optional[List[Dict]] = None,
    rss_new_items: Optional[List[Dict]] = None,
    display_mode: str = "keyword",
    standalone_data: Optional[Dict] = None,
    ai_analysis: Optional[Any] = None,
    show_new_section: bool = True,
) -> str:
    """渲染HTML内容

    Args:
        report_data: 报告数据字典，包含 stats, new_titles, failed_ids, total_new_count
        total_titles: 新闻总数
        mode: 报告模式 ("daily", "current", "incremental")
        update_info: 更新信息（可选）
        region_order: 区域显示顺序列表
        get_time_func: 获取当前时间的函数（可选，默认使用 datetime.now）
        rss_items: RSS 统计条目列表（可选）
        rss_new_items: RSS 新增条目列表（可选）
        display_mode: 显示模式 ("keyword"=按关键词分组, "platform"=按平台分组)
        standalone_data: 独立展示区数据（可选），包含 platforms 和 rss_feeds
        ai_analysis: AI 分析结果对象（可选），AIAnalysisResult 实例
        show_new_section: 是否显示新增热点区域

    Returns:
        渲染后的 HTML 字符串
    """
    # 默认区域顺序
    default_region_order = ["hotlist", "rss", "new_items", "standalone", "ai_analysis"]
    if region_order is None:
        region_order = default_region_order

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>雷达简报</title>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js" integrity="sha512-BNaRQnYJYiPSqHHDb58B0yaPfCu+Wgds8Gp/gU33kqBtgNS4tSPHuGibyoeqMV/TJlSKda6FXzoEyYGjTe+vXA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
        <style>
            * { box-sizing: border-box; }
            :root {
                --glass-heavy: rgba(255,255,255,0.18);
                --glass-mid: rgba(255,255,255,0.12);
                --glass-light: rgba(255,255,255,0.07);
                --glass-border: rgba(255,255,255,0.26);
                --glass-border-light: rgba(255,255,255,0.14);
                --tw: rgba(255,255,255,0.97);
                --tm: rgba(255,255,255,0.70);
                --td: rgba(255,255,255,0.45);
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
                margin: 0;
                padding: 16px;
                background: #fafafa;
                color: #333;
                line-height: 1.5;
            }

            .container {
                max-width: 600px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 2px 16px rgba(0,0,0,0.06);
            }

            /* ===== 新版 Header ===== */
            .header {
                position: relative;
                overflow: hidden;
                padding: 24px 22px 22px;
                background: linear-gradient(160deg, #1a6fba 0%, #3b8fd4 40%, #6fb3e8 100%);
                transition: background 1.4s ease;
            }
            .header-glow {
                position: absolute; inset: 0; pointer-events: none; z-index: 0;
                background:
                    radial-gradient(ellipse 55% 45% at 85% 5%, rgba(255,255,255,0.10) 0%, transparent 65%),
                    radial-gradient(ellipse 35% 35% at 5% 95%, rgba(0,0,0,0.12) 0%, transparent 60%);
            }
            .header-watermark {
                position: absolute; top: 50%; left: 50%;
                transform: translate(-50%, -50%);
                font-size: clamp(38px, 8vw, 76px); font-weight: 900; letter-spacing: 0.06em;
                color: rgba(255,255,255,0.055); pointer-events: none; white-space: nowrap;
                user-select: none; z-index: 1;
                transition: color .3s, -webkit-mask-image .3s, mask-image .3s;
                -webkit-mask-image: radial-gradient(circle 0px at 50% 50%, black 0%, transparent 100%);
                mask-image: radial-gradient(circle 0px at 50% 50%, black 0%, transparent 100%);
            }

            .header-top {
                position: relative; z-index: 2;
                display: flex; align-items: center; justify-content: space-between;
                margin-top: 40px; 
                margin-bottom: 16px;
            }
            .header-title {
                font-size: 20px; font-weight: 700;
                color: var(--tw); letter-spacing: 0.3px;
            }
            .gen-time-pill {
                display: flex; align-items: center; gap: 6px;
                background: var(--glass-heavy);
                border: 1px solid var(--glass-border);
                border-radius: 20px; padding: 5px 12px;
                backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
                font-size: 12px; font-weight: 600; color: var(--tw);
            }
            .gen-dot {
                width: 6px; height: 6px; border-radius: 50%;
                background: #4ade80; flex-shrink: 0;
                animation: pulse-dot 2.2s ease-in-out infinite;
            }
            @keyframes pulse-dot {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.5; transform: scale(0.75); }
            }

            /* ===== 天气面板 ===== */
            .weather-panel {
                position: relative; z-index: 2;
                display: flex; flex-direction: column; gap: 12px;
            }

            /* 今日主卡 */
            .weather-today {
                background: var(--glass-heavy);
                border: 1px solid var(--glass-border);
                border-radius: 20px;
                backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px);
                padding: 16px 18px 14px;
                display: flex; align-items: center;
                min-height: 86px; position: relative; overflow: hidden;
                transition: opacity .4s;
            }
            .weather-today::before {
                content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.45), transparent);
            }
            .weather-today.loading { justify-content: center; opacity: 0.55; }

            .wt-icon-wrap {
                flex-shrink: 0; width: 72px; height: 72px;
                position: relative; display: flex; align-items: center; justify-content: center;
            }
            .wt-icon {
                width: 72px; height: 72px; object-fit: contain;
                filter: brightness(0) invert(1) drop-shadow(0 2px 6px rgba(0,0,0,0.25));
            }

            .wt-center { flex: 1; padding: 0 12px; border-right: 1px solid var(--glass-border-light); }
            .wt-temp-row { display: flex; align-items: flex-start; gap: 2px; line-height: 1; margin-bottom: 3px; }
            .wt-temp { font-size: 50px; font-weight: 200; color: var(--tw); letter-spacing: -3px; font-variant-numeric: tabular-nums; line-height: 1; }
            .wt-unit { font-size: 21px; font-weight: 300; color: var(--tm); margin-top: 6px; }
            .wt-desc { font-size: 13px; font-weight: 500; color: var(--tw); margin-bottom: 5px; }
            .wt-range { font-size: 11px; color: var(--tm); font-variant-numeric: tabular-nums; }

            .wt-right { flex-shrink: 0; padding-left: 15px; display: flex; flex-direction: column; gap: 6px; }
            .wt-detail { display: flex; align-items: center; gap: 5px; font-size: 11.5px; color: var(--tm); white-space: nowrap; }
            .wt-detail-icon { width: 13px; height: 13px; opacity: 0.75; flex-shrink: 0; }
            .wt-detail-val { color: var(--tw); font-weight: 500; font-variant-numeric: tabular-nums; }

            /* 逐小时 */
            .weather-hourly {
                background: var(--glass-mid); border: 1px solid var(--glass-border-light);
                border-radius: 15px; backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
                padding: 12px 4px 10px; overflow: hidden;
            }
            .hourly-label { font-size: 9.5px; font-weight: 700; color: var(--td); letter-spacing: 0.9px; text-transform: uppercase; padding: 0 13px; margin-bottom: 9px; }
            .hourly-scroll { display: flex; gap: 4px; overflow-x: auto; padding: 0 9px 2px; scrollbar-width: none; -webkit-overflow-scrolling: touch; }
            .hourly-scroll::-webkit-scrollbar { display: none; }
            .hourly-item { 
                flex-shrink: 0; display: flex; flex-direction: column; align-items: center; 
                justify-content: flex-start; gap: 6px; padding: 8px 6px; 
                border-radius: 12px; min-width: 56px; height: 86px; cursor: default; 
            }
            .hourly-item.now { background: var(--glass-heavy); border: 1px solid var(--glass-border); }
            .hourly-time { font-size: 11px; color: var(--tm); font-variant-numeric: tabular-nums; font-weight: 500; line-height: 1; }
            .hourly-item.now .hourly-time { color: var(--tw); font-weight: 700; }
            .hourly-icon { width: 28px; height: 28px; object-fit: contain; filter: brightness(0) invert(1); flex-shrink: 0; }
            .hourly-temp { font-size: 13px; font-weight: 600; color: var(--tw); font-variant-numeric: tabular-nums; line-height: 1; margin-top: auto; }

            /* 明日预报 */
            .weather-tomorrow {
                background: var(--glass-mid); border: 1px solid var(--glass-border-light);
                border-radius: 15px; backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
                padding: 14px 16px;
            }
            .tmr-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
            .tmr-label { font-size: 10px; font-weight: 700; color: var(--td); letter-spacing: 0.9px; text-transform: uppercase; }
            .tmr-date { font-size: 11px; color: var(--td); }
            .tmr-body { display: flex; align-items: center; gap: 14px; }
            .tmr-icon { width: 44px; height: 44px; object-fit: contain; filter: brightness(0) invert(1); flex-shrink: 0; }
            .tmr-info { flex: 1; }
            .tmr-desc { font-size: 14px; font-weight: 600; color: var(--tw); margin-bottom: 4px; }
            .tmr-range { font-size: 12px; color: var(--tm); font-variant-numeric: tabular-nums; }
            .tmr-stats { display: flex; flex-direction: column; gap: 4px; align-items: flex-end; }
            .tmr-stat { display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--tm); }
            .tmr-stat svg { width: 12px; height: 12px; opacity: 0.7; }
            .tmr-stat-val { color: var(--tw); font-weight: 600; }
            .tmr-bar-wrap { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--glass-border-light); }
            .tmr-bar-label { display: flex; justify-content: space-between; font-size: 10px; color: var(--td); margin-bottom: 6px; }
            .tmr-bar-track { height: 4px; border-radius: 2px; background: var(--glass-light); position: relative; overflow: hidden; }
            .tmr-bar-fill { position: absolute; top: 0; bottom: 0; border-radius: 2px; background: linear-gradient(90deg, #60a5fa, #f97316); transition: left .9s ease, right .9s ease; }

            /* 工服卡 */
            .weather-uniform {
                background: var(--glass-mid); border: 1px solid var(--glass-border-light);
                border-radius: 15px; backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
                padding: 14px 16px;
            }
            .uniform-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
            .uniform-label { font-size: 10px; font-weight: 700; color: var(--td); letter-spacing: 0.9px; text-transform: uppercase; }
            .uniform-date { font-size: 11px; color: var(--td); }
            .uniform-body { display: flex; align-items: center; gap: 14px; }
            .uniform-swatch {
                flex-shrink: 0; width: 48px; height: 48px; border-radius: 50%;
                border: 2px solid rgba(255,255,255,0.35);
                box-shadow: 0 4px 16px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.2);
                transition: background .6s ease;
            }
            .uniform-info { flex: 1; }
            .uniform-color-name { font-size: 15px; font-weight: 700; color: var(--tw); margin-bottom: 4px; }
            .uniform-hint { font-size: 12px; color: var(--tm); line-height: 1.5; }
            .uniform-week { display: flex; gap: 5px; align-items: center; }
            .uniform-day-dot { display: flex; flex-direction: column; align-items: center; gap: 3px; }
            .uniform-day-label { font-size: 9px; color: var(--td); }
            .uniform-dot {
                width: 10px; height: 10px; border-radius: 50%;
                border: 1.5px solid rgba(255,255,255,0.15);
                transition: transform .2s;
            }
            .uniform-day-dot.today .uniform-dot {
                border-color: rgba(255,255,255,0.7);
                box-shadow: 0 0 6px rgba(255,255,255,0.4);
                transform: scale(1.25);
            }
            .uniform-day-dot.tomorrow .uniform-dot {
                border-color: rgba(255,255,255,0.5);
                transform: scale(1.1);
            }

            /* 城市+更新 */
            .wt-footer { display: flex; align-items: center; justify-content: space-between; padding: 0 4px; margin-top: 2px; }
            .wt-location { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--tm); }
            .wt-location svg { width: 12px; height: 12px; opacity: 0.65; }
            .wt-update { font-size: 11px; color: var(--td); }

            /* 骨架 */
            @keyframes shimmer { 0%, 100% { opacity: .3; } 50% { opacity: .65; } }
            .skeleton { animation: shimmer 1.6s ease-in-out infinite; background: var(--glass-mid); border-radius: 8px; }

            /* ===== 原有 Header 按钮及其他样式 ===== */
            .save-buttons { position: absolute; top: 16px; right: 16px; display: flex; gap: 8px; z-index: 10; }
            .save-btn-group { position: relative; display: flex; }
            .save-btn { background: rgba(255, 255, 255, 0.2); border: 1px solid rgba(255, 255, 255, 0.3); color: white; padding: 10px 18px; border-radius: 6px 0 0 6px; cursor: pointer; font-size: 13px; font-weight: 500; transition: all 0.2s ease; backdrop-filter: blur(10px); white-space: nowrap; min-height: 38px; border-right: none; }
            .save-btn:hover { background: rgba(255, 255, 255, 0.3); }
            .save-dropdown-trigger { background: rgba(255, 255, 255, 0.2); border: 1px solid rgba(255, 255, 255, 0.3); color: white; padding: 10px 10px; border-radius: 0 6px 6px 0; cursor: pointer; font-size: 11px; transition: all 0.2s ease; backdrop-filter: blur(10px); min-height: 38px; display: flex; align-items: center; }
            .save-dropdown-trigger:hover { background: rgba(255, 255, 255, 0.35); }
            .save-dropdown-menu { position: absolute; top: 100%; right: 0; margin-top: 4px; background: rgba(30, 30, 50, 0.92); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px; padding: 4px; min-width: 140px; opacity: 0; visibility: hidden; transform: translateY(-4px); transition: all 0.2s ease; box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
            .save-btn-group:hover .save-dropdown-menu, .save-dropdown-menu:hover { opacity: 1; visibility: visible; transform: translateY(0); }
            .save-dropdown-item { display: block; width: 100%; padding: 9px 14px; background: none; border: none; color: white; font-size: 13px; cursor: pointer; border-radius: 5px; text-align: left; transition: background 0.15s; white-space: nowrap; }
            .save-dropdown-item:hover { background: rgba(255, 255, 255, 0.15); }
            .dropdown-icon { width: 14px; height: 14px; margin-right: 8px; vertical-align: -2px; flex-shrink: 0; }

            .content { padding: 24px; }
            .word-group { margin-bottom: 40px; }
            .word-group:first-child { margin-top: 0; }
            .word-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; padding-bottom: 8px; border-bottom: 1px solid #f0f0f0; }
            .word-info { display: flex; align-items: center; gap: 12px; }
            .word-name { font-size: 17px; font-weight: 600; color: #1a1a1a; }
            .word-count { color: #666; font-size: 13px; font-weight: 500; }
            .word-count.hot { color: #dc2626; font-weight: 600; }
            .word-count.warm { color: #ea580c; font-weight: 600; }
            .word-index { color: #999; font-size: 12px; }

            .news-item { margin-bottom: 20px; padding: 16px 0; border-bottom: 1px solid #f5f5f5; position: relative; display: flex; gap: 12px; align-items: center; }
            .news-item:last-child { border-bottom: none; }
            .news-item.new::after { content: "NEW"; position: absolute; top: 12px; right: 0; background: #fbbf24; color: #92400e; font-size: 9px; font-weight: 700; padding: 3px 6px; border-radius: 4px; letter-spacing: 0.5px; }
            .news-number { color: #999; font-size: 13px; font-weight: 600; min-width: 20px; text-align: center; flex-shrink: 0; background: #f8f9fa; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; align-self: flex-start; margin-top: 8px; position: relative; cursor: pointer; transition: background 0.15s, color 0.15s; }
            .news-number .num-text { transition: opacity 0.15s; }
            .news-number .copy-icon { position: absolute; opacity: 0; transition: opacity 0.15s; }
            .news-item:hover .news-number .num-text { opacity: 0; }
            .news-item:hover .news-number .copy-icon { opacity: 1; }
            .news-item:hover .news-number { background: #eef2ff; color: #4f46e5; }
            .news-number.copied { background: #dcfce7 !important; }
            .news-number.copied .num-text { opacity: 0 !important; }
            .news-number.copied .copy-icon { opacity: 1 !important; }

            .news-content { flex: 1; min-width: 0; padding-right: 40px; }
            .news-item.new .news-content { padding-right: 50px; }
            .news-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
            .source-name { color: #666; font-size: 12px; font-weight: 500; }
            .keyword-tag { color: #2563eb; font-size: 12px; font-weight: 500; background: #eff6ff; padding: 2px 6px; border-radius: 4px; }
            .rank-num { color: #fff; background: #6b7280; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 10px; min-width: 18px; text-align: center; }
            .rank-num.top { background: #dc2626; }
            .rank-num.high { background: #ea580c; }
            .time-info { color: #999; font-size: 11px; }
            .count-info { color: #059669; font-size: 11px; font-weight: 500; }
            .news-title { font-size: 15px; line-height: 1.4; color: #1a1a1a; margin: 0; }
            .news-link { color: #2563eb; text-decoration: none; }
            .news-link:hover { text-decoration: underline; }
            .news-link:visited { color: #7c3aed; }

            .section-divider { margin-top: 32px; padding-top: 24px; border-top: 2px solid #e5e7eb; }
            .new-section { margin-top: 40px; padding-top: 24px; }
            .new-section-title { color: #1a1a1a; font-size: 16px; font-weight: 600; margin: 0 0 20px 0; }
            .new-source-group { margin-bottom: 24px; }
            .new-source-title { color: #666; font-size: 13px; font-weight: 500; margin: 0 0 12px 0; padding-bottom: 6px; border-bottom: 1px solid #f5f5f5; }
            .new-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #f9f9f9; }
            .new-item:last-child { border-bottom: none; }
            .new-item-number { color: #999; font-size: 12px; font-weight: 600; min-width: 18px; text-align: center; flex-shrink: 0; background: #f8f9fa; border-radius: 50%; width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; }
            .new-item-rank { color: #fff; background: #6b7280; font-size: 10px; font-weight: 700; padding: 3px 6px; border-radius: 8px; min-width: 20px; text-align: center; flex-shrink: 0; }
            .new-item-rank.top { background: #dc2626; }
            .new-item-rank.high { background: #ea580c; }
            .new-item-content { flex: 1; min-width: 0; }
            .new-item-title { font-size: 14px; line-height: 1.4; color: #1a1a1a; margin: 0; }

            .error-section { background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 16px; margin-bottom: 24px; }
            .error-title { color: #dc2626; font-size: 14px; font-weight: 600; margin: 0 0 8px 0; }
            .error-list { list-style: none; padding: 0; margin: 0; }
            .error-item { color: #991b1b; font-size: 13px; padding: 2px 0; font-family: 'SF Mono', Consolas, monospace; }

            .footer { margin-top: 32px; padding: 20px 24px; background: #f8f9fa; border-top: 1px solid #e5e7eb; text-align: center; }
            .footer-content { font-size: 13px; color: #6b7280; line-height: 1.6; }
            .footer-link { color: #4f46e5; text-decoration: none; font-weight: 500; transition: color 0.2s ease; }
            .footer-link:hover { color: #7c3aed; text-decoration: underline; }
            .project-name { font-weight: 600; color: #374151; }

            /* 其他组件样式 (RSS, Standalone, AI) */
            .rss-section { margin-top: 32px; padding-top: 24px; }
            .rss-section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
            .rss-section-title { font-size: 18px; font-weight: 600; color: #059669; }
            .rss-section-count { color: #6b7280; font-size: 14px; }
            .feed-group { margin-bottom: 24px; }
            .feed-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #10b981; }
            .feed-name { font-size: 15px; font-weight: 600; color: #059669; }
            .feed-count { color: #666; font-size: 13px; font-weight: 500; }
            .rss-item { margin-bottom: 12px; padding: 14px; background: #f0fdf4; border-radius: 8px; border-left: 3px solid #10b981; }
            .rss-meta { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; flex-wrap: wrap; }
            .rss-time { color: #6b7280; font-size: 12px; }
            .rss-author { color: #059669; font-size: 12px; font-weight: 500; }
            .rss-title { font-size: 14px; line-height: 1.5; margin-bottom: 6px; }
            .rss-link { color: #1f2937; text-decoration: none; font-weight: 500; }
            .rss-link:hover { color: #059669; text-decoration: underline; }

            .standalone-section { margin-top: 32px; padding-top: 24px; }
            .standalone-section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
            .standalone-section-title { font-size: 18px; font-weight: 600; color: #059669; }
            .standalone-section-count { color: #6b7280; font-size: 14px; }
            .standalone-group { margin-bottom: 40px; }
            .standalone-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; padding-bottom: 8px; border-bottom: 1px solid #f0f0f0; }
            .standalone-name { font-size: 17px; font-weight: 600; color: #1a1a1a; }
            .standalone-count { color: #666; font-size: 13px; font-weight: 500; }

            .ai-section { margin-top: 32px; padding: 24px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 12px; border: 1px solid #bae6fd; }
            .ai-section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
            .ai-section-title { font-size: 18px; font-weight: 600; color: #0369a1; }
            .ai-block { margin-bottom: 16px; padding: 16px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            .ai-block-title { font-size: 14px; font-weight: 600; color: #0369a1; margin-bottom: 8px; }
            .ai-block-content { font-size: 14px; line-height: 1.6; color: #334155; white-space: pre-wrap; }

            /* ===== 浏览器增强样式 ===== */
            body.wide-mode .container { max-width: 1200px; }
            body.wide-mode .content { padding: 32px 40px; }
            body.wide-mode .rss-feeds-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
            body.wide-mode .feed-group { margin-bottom: 0; }
            body.wide-mode .ai-section .ai-blocks-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
            body.wide-mode .new-section .new-sources-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
            body.wide-mode .standalone-section .standalone-groups-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }

            .tab-bar { display: none; overflow-x: auto; white-space: nowrap; padding: 8px 0 12px 0; margin-bottom: 20px; border-bottom: 2px solid #e5e7eb; -webkit-overflow-scrolling: touch; scrollbar-width: thin; position: sticky; top: 0; background: white; z-index: 10; gap: 4px; }
            body.wide-mode .tab-bar { display: flex; }
            body.wide-mode .tab-bar.tab-hidden { display: none; }
            .tab-btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border: none; background: #f3f4f6; color: #6b7280; border-radius: 8px 8px 0 0; cursor: pointer; font-size: 13px; font-weight: 500; white-space: nowrap; transition: all 0.2s ease; flex-shrink: 0; }
            .tab-btn:hover { background: #e5e7eb; color: #374151; }
            .tab-btn.active { background: #4f46e5; color: white; }
            .tab-count { font-size: 11px; background: rgba(0,0,0,0.1); padding: 1px 6px; border-radius: 10px; }
            .tab-btn.active .tab-count { background: rgba(255,255,255,0.3); }

            .search-bar { display: none; padding: 0 0 16px 0; }
            .search-input { width: 100%; padding: 10px 16px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 14px; outline: none; transition: border-color 0.2s; box-sizing: border-box; }
            .search-input:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79,70,229,0.1); }

            .fab-bar { position: fixed; bottom: 24px; right: 24px; display: flex; flex-direction: column; gap: 8px; z-index: 100; opacity: 0; transform: translateY(10px); transition: opacity 0.3s, transform 0.3s; pointer-events: none; }
            .fab-bar.visible { opacity: 1; transform: translateY(0); pointer-events: auto; }
            .fab-btn { width: 40px; height: 40px; border-radius: 50%; background: #4f46e5; color: white; border: none; cursor: pointer; font-size: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); transition: transform 0.2s, background 0.2s; display: flex; align-items: center; justify-content: center; position: relative; }
            .fab-btn:hover { transform: scale(1.1); background: #4338ca; }

            .fab-tooltip { position: absolute; bottom: 0; right: 52px; background: rgba(30, 30, 50, 0.92); backdrop-filter: blur(12px); color: white; border-radius: 10px; padding: 12px 16px; white-space: nowrap; font-size: 12px; line-height: 1.8; box-shadow: 0 8px 24px rgba(0,0,0,0.25); border: 1px solid rgba(255,255,255,0.1); opacity: 0; visibility: hidden; transform: translateY(6px); transition: all 0.2s ease; pointer-events: none; }
            .fab-btn:hover .fab-tooltip, .fab-btn.show-tip .fab-tooltip { opacity: 1; visibility: visible; transform: translateY(0); pointer-events: auto; }
            .fab-tooltip .tip-row { display: flex; justify-content: space-between; gap: 16px; align-items: center; }
            .fab-tooltip .tip-key { background: rgba(255,255,255,0.15); border-radius: 3px; padding: 1px 6px; font-family: monospace; font-size: 11px; margin-left: 8px; }

            .collapse-icon { display: none; margin-right: 6px; font-size: 12px; color: #9ca3af; transition: transform 0.2s; user-select: none; }
            .word-header.collapsible { cursor: pointer; }
            .word-header.collapsible .collapse-icon { display: inline; }
            .word-header.collapsible:hover { background: #f9fafb; border-radius: 6px; margin: 0 -8px 20px -8px; padding: 8px; }
            .word-group.collapsed .news-item { display: none; }
            .word-group.collapsed .collapse-icon { transform: rotate(-90deg); }

            .toggle-wide-btn { background: rgba(255, 255, 255, 0.2); border: 1px solid rgba(255, 255, 255, 0.3); color: white; padding: 10px 14px; border-radius: 6px; cursor: pointer; font-size: 15px; transition: all 0.2s ease; backdrop-filter: blur(10px); line-height: 1; min-height: 38px; }
            .toggle-wide-btn:hover { background: rgba(255, 255, 255, 0.3); border-color: rgba(255, 255, 255, 0.5); transform: translateY(-1px); }

            /* 暗色模式 */
            body.dark-mode { background: #1a1a2e; color: #e0e0e0; }
            body.dark-mode .container { background: #16213e; box-shadow: 0 2px 16px rgba(0,0,0,0.3); }
            body.dark-mode .content { background: #16213e; }
            body.dark-mode .word-header { border-bottom-color: #2a2a4a; }
            body.dark-mode .word-header.collapsible:hover { background: #1a1a3e; }
            body.dark-mode .news-item { border-bottom-color: #2a2a4a; }
            body.dark-mode .news-title a { color: #8ab4f8; }
            body.dark-mode .news-title a:visited { color: #c58af9; }
            body.dark-mode .tab-bar { background: #16213e; border-bottom-color: #2a2a4a; }
            body.dark-mode .tab-btn { color: #aaa; }
            body.dark-mode .tab-btn.active { color: #8ab4f8; border-bottom-color: #8ab4f8; }
            body.dark-mode .tab-btn:hover { color: #ccc; background: rgba(255,255,255,0.05); }
            body.dark-mode .search-input { background: #1a1a3e; border-color: #2a2a4a; color: #e0e0e0; }
            body.dark-mode .search-input:focus { border-color: #8ab4f8; }
            body.dark-mode .fab-btn { background: #533483; }
            body.dark-mode .fab-btn:hover { background: #6d28d9; }
            body.dark-mode .footer { background: #0f3460; color: rgba(255,255,255,0.7); }
            body.dark-mode .rss-item, body.dark-mode .new-item, body.dark-mode .standalone-item { border-bottom-color: #2a2a4a; }
            body.dark-mode .rss-title a, body.dark-mode .new-item a, body.dark-mode .standalone-item a { color: #8ab4f8; }
            body.dark-mode .ai-block { background: #1a1a3e; border-color: #2a2a4a; }

            .toggle-dark-btn { background: rgba(255, 255, 255, 0.2); border: 1px solid rgba(255, 255, 255, 0.3); color: white; padding: 10px 14px; border-radius: 6px; cursor: pointer; font-size: 15px; transition: all 0.2s ease; backdrop-filter: blur(10px); line-height: 1; min-height: 38px; }
            .toggle-dark-btn:hover { background: rgba(255, 255, 255, 0.3); border-color: rgba(255, 255, 255, 0.5); transform: translateY(-1px); }

            .reading-progress { position: fixed; top: 0; left: 0; width: 0; height: 3px; background: linear-gradient(90deg, #4f46e5, #7c3aed); z-index: 9999; transition: width 0.1s linear; }
            body.dark-mode .reading-progress { background: linear-gradient(90deg, #8ab4f8, #c58af9); }

            @media (max-width: 480px) {
                body { padding: 12px; }
                .content { padding: 20px; }
                .footer { padding: 16px 20px; }
                .news-header { gap: 6px; }
                .news-content { padding-right: 45px; }
                .news-item { gap: 8px; }
                .new-item { gap: 8px; }
                .news-number { width: 20px; height: 20px; font-size: 12px; }
                .save-buttons { position: static; margin-bottom: 16px; display: flex; gap: 8px; justify-content: center; width: 100%; }
                .save-btn-group { flex: 1; }
                .save-btn { width: 100%; border-radius: 6px 0 0 6px; }
                .wt-temp { font-size: 44px; }
                .wt-icon-wrap { width: 64px; height: 64px; }
                .wt-icon { width: 64px; height: 64px; }
                .wt-right { display: none; }
                .wt-center { border-right: none; }
                .hourly-item { min-width: 52px; padding: 6px 4px; }
                .hourly-icon { width: 24px; height: 24px; }
                .uniform-week { display: none; }
            }
        </style>
    </head>
    <body>
        <div class="reading-progress"></div>
        <div class="container">
            <div class="header" id="mainHeader">
                <div class="header-glow"></div>
                <div class="header-watermark" id="watermark">TrendRadar</div>

                <div class="save-buttons">
                    <button class="toggle-wide-btn" onclick="toggleWideMode()" title="切换宽屏/窄屏">⛶</button>
                    <button class="toggle-dark-btn" onclick="toggleDarkMode()" title="切换暗色/亮色">☽</button>
                    <div class="save-btn-group">
                        <button class="save-btn" onclick="saveAsImage()">导出</button>
                        <button class="save-dropdown-trigger">▾</button>
                        <div class="save-dropdown-menu">
                            <button class="save-dropdown-item" onclick="saveAsImage()"><svg class="dropdown-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="2" width="12" height="12" rx="2"/><circle cx="8" cy="7.5" r="2.5"/><path d="M12 4h.01"/></svg>整页截图</button>
                            <button class="save-dropdown-item" onclick="saveAsMultipleImages()"><svg class="dropdown-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="1" y="4" width="10" height="10" rx="1.5"/><path d="M5 4V2.5A1.5 1.5 0 016.5 1h7A1.5 1.5 0 0115 2.5v7a1.5 1.5 0 01-1.5 1.5H12"/></svg>分段截图</button>
                            <button class="save-dropdown-item" onclick="saveAsMarkdown()"><svg class="dropdown-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2.5 2h11A1.5 1.5 0 0115 3.5v9a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 011 12.5v-9A1.5 1.5 0 012.5 2z"/><path d="M4 11V5l2.5 3L9 5v6"/><path d="M11.5 8v3m0 0l-1.5-2m1.5 2l1.5-2"/></svg>Markdown</button>
                        </div>
                    </div>
                </div>

                <div class="header-top">
                    <div class="header-title">雷达简报</div>
                    <div class="gen-time-pill">
                        <div class="gen-dot"></div>
                        <span id="genTime">"""

    if get_time_func:
        now = get_time_func()
    else:
        now = datetime.now()
    html += now.strftime("%m-%d %H:%M")

    html += """</span>
                    </div>
                </div>

                <!-- 天气面板 -->
                <div class="weather-panel" id="weatherPanel">
                    
                    <!-- 今日主卡 -->
                    <div class="weather-today loading" id="wtToday">
                        <div class="skeleton" style="width:62px;height:62px;border-radius:50%;margin-right:16px;flex-shrink:0;"></div>
                        <div style="flex:1;display:flex;flex-direction:column;gap:9px;">
                            <div class="skeleton" style="width:110px;height:34px;border-radius:8px;"></div>
                            <div class="skeleton" style="width:75px;height:13px;border-radius:6px;"></div>
                        </div>
                    </div>

                    <!-- 逐小时 -->
                    <div class="weather-hourly" id="wtHourly" style="display:none;">
                        <div class="hourly-label">逐小时预报</div>
                        <div class="hourly-scroll" id="hourlyScroll"></div>
                    </div>

                    <!-- 明日预报 -->
                    <div class="weather-tomorrow" id="wtTomorrow" style="display:none;">
                        <div class="tmr-header">
                            <div class="tmr-label">明日天气</div>
                            <div class="tmr-date" id="tmrDate"></div>
                        </div>
                        <div class="tmr-body">
                            <img class="tmr-icon" id="tmrIcon" src="" alt="">
                            <div class="tmr-info">
                                <div class="tmr-desc" id="tmrDesc">—</div>
                                <div class="tmr-range" id="tmrRange">—</div>
                            </div>
                            <div class="tmr-stats" id="tmrStats"></div>
                        </div>
                        <div class="tmr-bar-wrap">
                            <div class="tmr-bar-label">
                                <span id="tmrBarMin">—</span>
                                <span style="color:var(--td);font-size:9px;">温度区间</span>
                                <span id="tmrBarMax">—</span>
                            </div>
                            <div class="tmr-bar-track">
                                <div class="tmr-bar-fill" id="tmrBarFill" style="left:0%;right:0%;"></div>
                            </div>
                        </div>
                    </div>

                    <!-- 工服卡 -->
                    <div class="weather-uniform" id="wtUniform" style="display:none;">
                        <div class="uniform-header">
                            <div class="uniform-label">明日工服</div>
                            <div class="uniform-date" id="uniformDate"></div>
                        </div>
                        <div class="uniform-body">
                            <div class="uniform-swatch" id="uniformSwatch"></div>
                            <div class="uniform-info">
                                <div class="uniform-color-name" id="uniformColorName">—</div>
                                <div class="uniform-hint" id="uniformHint">—</div>
                            </div>
                            <div class="uniform-week" id="uniformWeek"></div>
                        </div>
                    </div>

                    <!-- 城市+更新 -->
                    <div class="wt-footer" id="wtFooter" style="display:none;">
                        <div class="wt-location">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/>
                                <circle cx="12" cy="10" r="3"/>
                            </svg>
                            <span id="wtCity">—</span>
                        </div>
                        <div class="wt-update" id="wtUpdate">—</div>
                    </div>

                </div>
            </div>

            <div class="content">
                <div class="search-bar">
                    <input type="text" class="search-input" placeholder="搜索新闻标题..." oninput="handleSearch(this.value)">
                </div>"""

    # 处理失败ID错误信息
    if report_data["failed_ids"]:
        html += """
                <div class="error-section">
                    <div class="error-title">⚠️ 请求失败的平台</div>
                    <ul class="error-list">"""
        for id_value in report_data["failed_ids"]:
            html += f'<li class="error-item">{html_escape(id_value)}</li>'
        html += """
                    </ul>
                </div>"""

    # 生成热点词汇统计部分的HTML
    stats_html = ""
    tab_bar_html = ""
    if report_data["stats"]:
        total_count = len(report_data["stats"])

        tab_bar_html = '<div class="tab-bar">'
        for tab_i, tab_stat in enumerate(report_data["stats"]):
            escaped_tab_word = html_escape(tab_stat["word"])
            tab_count = tab_stat["count"]
            tab_bar_html += f'<button class="tab-btn" data-tab-index="{tab_i}">{escaped_tab_word}<span class="tab-count">{tab_count}</span></button>'
        tab_bar_html += '<button class="tab-btn" data-tab-index="all">全部</button>'
        tab_bar_html += '</div>'

        for i, stat in enumerate(report_data["stats"], 1):
            count = stat["count"]
            if count >= 10:
                count_class = "hot"
            elif count >= 5:
                count_class = "warm"
            else:
                count_class = ""

            escaped_word = html_escape(stat["word"])

            stats_html += f"""
                <div class="word-group" data-tab-index="{i - 1}">
                    <div class="word-header">
                        <div class="word-info">
                            <div class="word-name">{escaped_word}</div>
                            <div class="word-count {count_class}">{count} 条</div>
                        </div>
                        <div class="word-index"><span class="collapse-icon">▼</span>{i}/{total_count}</div>
                    </div>"""

            for j, title_data in enumerate(stat["titles"], 1):
                is_new = title_data.get("is_new", False)
                new_class = "new" if is_new else ""

                stats_html += f"""
                    <div class="news-item {new_class}">
                        <div class="news-number">{j}</div>
                        <div class="news-content">
                            <div class="news-header">"""

                if display_mode == "keyword":
                    stats_html += f'<span class="source-name">{html_escape(title_data["source_name"])}</span>'
                else:
                    matched_keyword = title_data.get("matched_keyword", "")
                    if matched_keyword:
                        stats_html += f'<span class="keyword-tag">[{html_escape(matched_keyword)}]</span>'

                ranks = title_data.get("ranks", [])
                if ranks:
                    min_rank = min(ranks)
                    max_rank = max(ranks)
                    rank_threshold = title_data.get("rank_threshold", 10)
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= rank_threshold:
                        rank_class = "high"
                    else:
                        rank_class = ""
                    if min_rank == max_rank:
                        rank_text = str(min_rank)
                    else:
                        rank_text = f"{min_rank}-{max_rank}"
                    stats_html += f'<span class="rank-num {rank_class}">{rank_text}</span>'

                time_display = title_data.get("time_display", "")
                if time_display:
                    simplified_time = time_display.replace(" ~ ", "~").replace("[", "").replace("]", "")
                    stats_html += f'<span class="time-info">{html_escape(simplified_time)}</span>'

                count_info = title_data.get("count", 1)
                if count_info > 1:
                    stats_html += f'<span class="count-info">{count_info}次</span>'

                stats_html += """
                            </div>
                            <div class="news-title">"""

                escaped_title = html_escape(title_data["title"])
                link_url = title_data.get("mobile_url") or title_data.get("url", "")

                if link_url:
                    escaped_url = html_escape(link_url)
                    stats_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    stats_html += escaped_title

                stats_html += """
                            </div>
                        </div>
                    </div>"""

            stats_html += """
                </div>"""

    if stats_html:
        stats_html = f"""
                <div class="hotlist-section">{tab_bar_html}{stats_html}
                </div>"""

    new_titles_html = ""
    if show_new_section and report_data["new_titles"]:
        new_titles_html += f"""
                <div class="new-section">
                    <div class="new-section-title">本次新增热点 (共 {report_data['total_new_count']} 条)</div>
                    <div class="new-sources-grid">"""

        for source_data in report_data["new_titles"]:
            escaped_source = html_escape(source_data["source_name"])
            titles_count = len(source_data["titles"])

            new_titles_html += f"""
                    <div class="new-source-group">
                        <div class="new-source-title">{escaped_source} · {titles_count}条</div>"""

            for idx, title_data in enumerate(source_data["titles"], 1):
                ranks = title_data.get("ranks", [])
                rank_class = ""
                if ranks:
                    min_rank = min(ranks)
                    if min_rank <= 3:
                        rank_class = "top"
                    elif min_rank <= title_data.get("rank_threshold", 10):
                        rank_class = "high"
                    if len(ranks) == 1:
                        rank_text = str(ranks[0])
                    else:
                        rank_text = f"{min(ranks)}-{max(ranks)}"
                else:
                    rank_text = "?"

                new_titles_html += f"""
                        <div class="new-item">
                            <div class="new-item-number">{idx}</div>
                            <div class="new-item-rank {rank_class}">{rank_text}</div>
                            <div class="new-item-content">
                                <div class="new-item-title">"""

                escaped_title = html_escape(title_data["title"])
                link_url = title_data.get("mobile_url") or title_data.get("url", "")

                if link_url:
                    escaped_url = html_escape(link_url)
                    new_titles_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    new_titles_html += escaped_title

                new_titles_html += """
                                </div>
                            </div>
                        </div>"""
            new_titles_html += """
                    </div>"""
        new_titles_html += """
                    </div>
                </div>"""

    def render_rss_stats_html(stats: List[Dict], title: str = "RSS 订阅更新") -> str:
        if not stats: return ""
        total_count = sum(stat.get("count", 0) for stat in stats)
        if total_count == 0: return ""

        rss_html = f"""
                <div class="rss-section">
                    <div class="rss-section-header">
                        <div class="rss-section-title">{title}</div>
                        <div class="rss-section-count">{total_count} 条</div>
                    </div>
                    <div class="rss-feeds-grid">"""

        for stat in stats:
            keyword = stat.get("word", "")
            titles = stat.get("titles", [])
            if not titles: continue
            keyword_count = len(titles)
            rss_html += f"""
                    <div class="feed-group">
                        <div class="feed-header">
                            <div class="feed-name">{html_escape(keyword)}</div>
                            <div class="feed-count">{keyword_count} 条</div>
                        </div>"""

            for title_data in titles:
                item_title = title_data.get("title", "")
                url = title_data.get("url", "")
                time_display = title_data.get("time_display", "")
                source_name = title_data.get("source_name", "")
                is_new = title_data.get("is_new", False)

                rss_html += """
                        <div class="rss-item">
                            <div class="rss-meta">"""

                if time_display: rss_html += f'<span class="rss-time">{html_escape(time_display)}</span>'
                if source_name: rss_html += f'<span class="rss-author">{html_escape(source_name)}</span>'
                if is_new: rss_html += '<span class="rss-author" style="color: #dc2626;">NEW</span>'

                rss_html += """
                            </div>
                            <div class="rss-title">"""

                escaped_title = html_escape(item_title)
                if url:
                    escaped_url = html_escape(url)
                    rss_html += f'<a href="{escaped_url}" target="_blank" class="rss-link">{escaped_title}</a>'
                else:
                    rss_html += escaped_title

                rss_html += """
                            </div>
                        </div>"""
            rss_html += """
                    </div>"""
        rss_html += """
                    </div>
                </div>"""
        return rss_html

    def render_standalone_html(data: Optional[Dict]) -> str:
        if not data: return ""
        platforms = data.get("platforms", [])
        rss_feeds = data.get("rss_feeds", [])
        if not platforms and not rss_feeds: return ""

        total_platform_items = sum(len(p.get("items", [])) for p in platforms)
        total_rss_items = sum(len(f.get("items", [])) for f in rss_feeds)
        total_count = total_platform_items + total_rss_items
        if total_count == 0: return ""

        all_groups = []
        for p in platforms:
            items = p.get("items", [])
            if items: all_groups.append({"name": p.get("name", p.get("id", "")), "count": len(items)})
        for f in rss_feeds:
            items = f.get("items", [])
            if items: all_groups.append({"name": f.get("name", f.get("id", "")), "count": len(items)})

        standalone_html = f"""
                <div class="standalone-section">
                    <div class="standalone-section-header">
                        <div class="standalone-section-title">独立展示区</div>
                        <div class="standalone-section-count">{total_count} 条</div>
                    </div>"""

        if len(all_groups) >= 2:
            standalone_html += """
                    <div class="tab-bar standalone-tab-bar">"""
            for idx, g in enumerate(all_groups):
                active = ' active' if idx == 0 else ''
                standalone_html += f"""
                        <button class="tab-btn{active}" data-standalone-tab="{idx}">{html_escape(g["name"])}<span class="tab-count">{g["count"]}</span></button>"""
            standalone_html += f"""
                        <button class="tab-btn" data-standalone-tab="all">全部<span class="tab-count">{total_count}</span></button>
                    </div>"""

        standalone_html += """
                    <div class="standalone-groups-grid">"""

        group_idx = 0
        for platform in platforms:
            platform_name = platform.get("name", platform.get("id", ""))
            items = platform.get("items", [])
            if not items: continue

            standalone_html += f"""
                    <div class="standalone-group" data-standalone-tab="{group_idx}">
                        <div class="standalone-header">
                            <div class="standalone-name">{html_escape(platform_name)}</div>
                            <div class="standalone-count">{len(items)} 条</div>
                        </div>"""

            for j, item in enumerate(items, 1):
                title = item.get("title", "")
                url = item.get("url", "") or item.get("mobileUrl", "")
                rank = item.get("rank", 0)
                ranks = item.get("ranks", [])
                first_time = item.get("first_time", "")
                last_time = item.get("last_time", "")
                count = item.get("count", 1)

                standalone_html += f"""
                        <div class="news-item">
                            <div class="news-number">{j}</div>
                            <div class="news-content">
                                <div class="news-header">"""

                if ranks:
                    min_rank = min(ranks)
                    max_rank = max(ranks)
                    if min_rank <= 3: rank_class = "top"
                    elif min_rank <= 10: rank_class = "high"
                    else: rank_class = ""
                    if min_rank == max_rank: rank_text = str(min_rank)
                    else: rank_text = f"{min_rank}-{max_rank}"
                    standalone_html += f'<span class="rank-num {rank_class}">{rank_text}</span>'
                elif rank > 0:
                    if rank <= 3: rank_class = "top"
                    elif rank <= 10: rank_class = "high"
                    else: rank_class = ""
                    standalone_html += f'<span class="rank-num {rank_class}">{rank}</span>'

                if first_time and last_time and first_time != last_time:
                    first_time_display = convert_time_for_display(first_time)
                    last_time_display = convert_time_for_display(last_time)
                    standalone_html += f'<span class="time-info">{html_escape(first_time_display)}~{html_escape(last_time_display)}</span>'
                elif first_time:
                    first_time_display = convert_time_for_display(first_time)
                    standalone_html += f'<span class="time-info">{html_escape(first_time_display)}</span>'

                if count > 1:
                    standalone_html += f'<span class="count-info">{count}次</span>'

                standalone_html += """
                                </div>
                                <div class="news-title">"""

                escaped_title = html_escape(title)
                if url:
                    escaped_url = html_escape(url)
                    standalone_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    standalone_html += escaped_title

                standalone_html += """
                                </div>
                            </div>
                        </div>"""
            standalone_html += """
                    </div>"""
            group_idx += 1

        for feed in rss_feeds:
            feed_name = feed.get("name", feed.get("id", ""))
            items = feed.get("items", [])
            if not items: continue

            standalone_html += f"""
                    <div class="standalone-group" data-standalone-tab="{group_idx}">
                        <div class="standalone-header">
                            <div class="standalone-name">{html_escape(feed_name)}</div>
                            <div class="standalone-count">{len(items)} 条</div>
                        </div>"""

            for j, item in enumerate(items, 1):
                title = item.get("title", "")
                url = item.get("url", "")
                published_at = item.get("published_at", "")
                author = item.get("author", "")

                standalone_html += f"""
                        <div class="news-item">
                            <div class="news-number">{j}</div>
                            <div class="news-content">
                                <div class="news-header">"""

                if published_at:
                    try:
                        from datetime import datetime as dt
                        if "T" in published_at:
                            dt_obj = dt.fromisoformat(published_at.replace("Z", "+00:00"))
                            time_display = dt_obj.strftime("%m-%d %H:%M")
                        else:
                            time_display = published_at
                    except:
                        time_display = published_at
                    standalone_html += f'<span class="time-info">{html_escape(time_display)}</span>'

                if author:
                    standalone_html += f'<span class="source-name">{html_escape(author)}</span>'

                standalone_html += """
                                </div>
                                <div class="news-title">"""

                escaped_title = html_escape(title)
                if url:
                    escaped_url = html_escape(url)
                    standalone_html += f'<a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
                else:
                    standalone_html += escaped_title

                standalone_html += """
                                </div>
                            </div>
                        </div>"""
            standalone_html += """
                    </div>"""
            group_idx += 1

        standalone_html += """
                    </div>
                </div>"""
        return standalone_html

    rss_stats_html = render_rss_stats_html(rss_items, "RSS 订阅更新") if rss_items else ""
    rss_new_html = render_rss_stats_html(rss_new_items, "RSS 新增更新") if rss_new_items else ""
    standalone_html = render_standalone_html(standalone_data)
    ai_html = render_ai_analysis_html_rich(ai_analysis) if ai_analysis else ""

    region_contents = {
        "hotlist": stats_html,
        "rss": rss_stats_html,
        "new_items": (new_titles_html, rss_new_html),
        "standalone": standalone_html,
        "ai_analysis": ai_html,
    }

    def add_section_divider(content: str) -> str:
        if not content or 'class="' not in content: return content
        first_class_pos = content.find('class="')
        if first_class_pos != -1:
            insert_pos = first_class_pos + len('class="')
            return content[:insert_pos] + "section-divider " + content[insert_pos:]
        return content

    has_previous_content = False
    for region in region_order:
        content = region_contents.get(region, "")
        if region == "new_items":
            new_html, rss_new = content
            if new_html:
                if has_previous_content: new_html = add_section_divider(new_html)
                html += new_html
                has_previous_content = True
            if rss_new:
                if has_previous_content: rss_new = add_section_divider(rss_new)
                html += rss_new
                has_previous_content = True
        elif content:
            if has_previous_content: content = add_section_divider(content)
            html += content
            has_previous_content = True

    html += """
            </div>

            <div class="footer">
                <div class="footer-content">
                    由 <span class="project-name">TrendRadar</span> 生成 ·
                    <a href="https://github.com/sansan0/TrendRadar" target="_blank" class="footer-link">
                        GitHub 开源项目
                    </a>"""

    if update_info:
        html += f"""
                    <br>
                    <span style="color: #ea580c; font-weight: 500;">
                        发现新版本 {update_info['remote_version']}，当前版本 {update_info['current_version']}
                    </span>"""

    html += """
                </div>
            </div>
        </div>

        <div class="fab-bar">
            <button class="fab-btn" onclick="window.scrollTo({top:0,behavior:'smooth'})" title="返回顶部">↑</button>
            <button class="fab-btn fab-help">
                <span>?</span>
                <div class="fab-tooltip">
                    <div class="tip-row"><span>切换宽屏</span><span class="tip-key">W</span></div>
                    <div class="tip-row"><span>暗色模式</span><span class="tip-key">D</span></div>
                    <div class="tip-row"><span>搜索</span><span class="tip-key">/</span></div>
                    <div class="tip-row"><span>上一个 Tab</span><span class="tip-key">←</span></div>
                    <div class="tip-row"><span>下一个 Tab</span><span class="tip-key">→</span></div>
                    <div class="tip-row"><span>序号可复制</span><span class="tip-key">点击</span></div>
                </div>
            </button>
        </div>

        <script>
            // ===== 浏览器增强功能 =====

            function toggleWideMode() {
                document.body.classList.toggle('wide-mode');
                var isWide = document.body.classList.contains('wide-mode');
                try { localStorage.setItem('trendradar-wide-mode', isWide ? '1' : '0'); } catch(e) {}
                var btn = document.querySelector('.toggle-wide-btn');
                if (btn) btn.textContent = isWide ? '⊡' : '⛶';
                initTabVisibility();
                initCollapseVisibility();
                initStandaloneTabVisibility();
            }

            function toggleDarkMode() {
                var isDark = document.body.classList.toggle('dark-mode');
                try { localStorage.setItem('trendradar-dark-mode', isDark ? '1' : '0'); } catch(e) {}
                var btn = document.querySelector('.toggle-dark-btn');
                if (btn) btn.textContent = isDark ? '☀' : '☽';
            }

            function initTabs() {
                var tabBar = document.querySelector('.tab-bar');
                if (!tabBar) return;
                var tabs = tabBar.querySelectorAll('.tab-btn');
                var groups = document.querySelectorAll('.word-group[data-tab-index]');
                initTabVisibility();

                function activateTab(index) {
                    tabs.forEach(function(t) { t.classList.remove('active'); });
                    if (index === 'all') {
                        var allBtn = tabBar.querySelector('[data-tab-index="all"]');
                        if (allBtn) allBtn.classList.add('active');
                        groups.forEach(function(g) { g.style.display = ''; });
                        try { history.replaceState(null, '', '#all'); } catch(e) {}
                        return;
                    }
                    var idx = parseInt(index);
                    tabs.forEach(function(t) {
                        if (parseInt(t.dataset.tabIndex) === idx) t.classList.add('active');
                    });
                    if (document.body.classList.contains('wide-mode') && !tabBar.classList.contains('tab-hidden')) {
                        groups.forEach(function(g) {
                            g.style.display = (parseInt(g.dataset.tabIndex) === idx) ? '' : 'none';
                        });
                    }
                    try { history.replaceState(null, '', '#tab-' + idx); } catch(e) {}
                }

                tabs.forEach(function(tab) {
                    tab.addEventListener('click', function() {
                        var idx = tab.dataset.tabIndex;
                        activateTab(idx === 'all' ? 'all' : parseInt(idx));
                    });
                });

                tabBar.addEventListener('keydown', function(e) {
                    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                        var tabsArr = Array.from(tabs);
                        var ci = tabsArr.findIndex(function(t) { return t.classList.contains('active'); });
                        var dir = e.key === 'ArrowRight' ? 1 : -1;
                        var ni = Math.max(0, Math.min(tabsArr.length - 1, ci + dir));
                        var nt = tabsArr[ni];
                        activateTab(nt.dataset.tabIndex === 'all' ? 'all' : parseInt(nt.dataset.tabIndex));
                        nt.focus();
                        e.preventDefault();
                    }
                });

                var hash = window.location.hash;
                if (hash === '#all') { activateTab('all'); }
                else if (hash.indexOf('#tab-') === 0) { activateTab(parseInt(hash.replace('#tab-', ''))); }
                else { activateTab(0); }
            }

            function initTabVisibility() {
                var tabBar = document.querySelector('.tab-bar');
                if (!tabBar) return;
                var groups = document.querySelectorAll('.word-group[data-tab-index]');
                var isWide = document.body.classList.contains('wide-mode');
                if (!isWide || groups.length <= 2) {
                    tabBar.classList.add('tab-hidden');
                    groups.forEach(function(g) { g.style.display = ''; });
                } else {
                    tabBar.classList.remove('tab-hidden');
                    var activeTab = tabBar.querySelector('.tab-btn.active');
                    if (activeTab) { activeTab.click(); }
                    else {
                        var firstTab = tabBar.querySelector('.tab-btn');
                        if (firstTab) firstTab.click();
                    }
                }
            }

            function handleSearch(query) {
                query = query.toLowerCase();
                document.querySelectorAll('.news-item').forEach(function(item) {
                    var title = (item.querySelector('.news-title') || {}).textContent || '';
                    item.style.display = (!query || title.toLowerCase().indexOf(query) !== -1) ? '' : 'none';
                });
                document.querySelectorAll('.rss-item').forEach(function(item) {
                    var title = (item.querySelector('.rss-title') || {}).textContent || '';
                    item.style.display = (!query || title.toLowerCase().indexOf(query) !== -1) ? '' : 'none';
                });
            }

            function initBackToTop() {
                var fabBar = document.querySelector('.fab-bar');
                if (!fabBar) return;
                window.addEventListener('scroll', function() {
                    fabBar.classList.toggle('visible', window.scrollY > 300);
                });
            }

            function initCollapse() {
                document.querySelectorAll('.word-header').forEach(function(header) {
                    header.addEventListener('click', function() {
                        var tabBar = document.querySelector('.tab-bar');
                        if (document.body.classList.contains('wide-mode') && tabBar && !tabBar.classList.contains('tab-hidden')) return;
                        var group = header.closest('.word-group');
                        if (group) group.classList.toggle('collapsed');
                    });
                });
                initCollapseVisibility();
            }

            function initCollapseVisibility() {
                var headers = document.querySelectorAll('.word-header');
                var tabBar = document.querySelector('.tab-bar');
                var isTabMode = document.body.classList.contains('wide-mode') && tabBar && !tabBar.classList.contains('tab-hidden');
                headers.forEach(function(h) {
                    if (isTabMode) { h.classList.remove('collapsible'); }
                    else { h.classList.add('collapsible'); }
                });
                if (isTabMode) {
                    document.querySelectorAll('.word-group.collapsed').forEach(function(g) {
                        g.classList.remove('collapsed');
                    });
                }
            }

            function initStandaloneTabs() {
                var tabBar = document.querySelector('.standalone-tab-bar');
                if (!tabBar) return;
                var groups = document.querySelectorAll('.standalone-group[data-standalone-tab]');
                var btns = tabBar.querySelectorAll('.tab-btn[data-standalone-tab]');

                function activateStandaloneTab(val) {
                    btns.forEach(function(b) {
                        var bVal = b.getAttribute('data-standalone-tab');
                        b.classList.toggle('active', bVal === String(val));
                    });
                    groups.forEach(function(g) {
                        var gVal = g.getAttribute('data-standalone-tab');
                        g.style.display = (val === 'all' || gVal === String(val)) ? '' : 'none';
                    });
                }

                btns.forEach(function(btn) {
                    btn.addEventListener('click', function() {
                        activateStandaloneTab(btn.getAttribute('data-standalone-tab'));
                    });
                });

                initStandaloneTabVisibility();
            }

            function initStandaloneTabVisibility() {
                var tabBar = document.querySelector('.standalone-tab-bar');
                if (!tabBar) return;
                var groups = document.querySelectorAll('.standalone-group[data-standalone-tab]');
                var isWide = document.body.classList.contains('wide-mode');
                if (!isWide || groups.length <= 1) {
                    tabBar.classList.add('tab-hidden');
                    groups.forEach(function(g) { g.style.display = ''; });
                } else {
                    tabBar.classList.remove('tab-hidden');
                    var activeBtn = tabBar.querySelector('.tab-btn.active');
                    if (activeBtn) activeBtn.click();
                    else { var first = tabBar.querySelector('.tab-btn'); if (first) first.click(); }
                }
            }

            function prepareForScreenshot() {
                var state = { wasWide: document.body.classList.contains('wide-mode'), hiddenGroups: [] };
                document.body.classList.remove('wide-mode');
                state.wasDark = document.body.classList.contains('dark-mode');
                document.body.classList.remove('dark-mode');
                document.querySelectorAll('.word-group[data-tab-index]').forEach(function(g, i) {
                    if (g.style.display === 'none') { state.hiddenGroups.push(i); g.style.display = ''; }
                });
                state.hiddenStandaloneGroups = [];
                document.querySelectorAll('.standalone-group[data-standalone-tab]').forEach(function(g, i) {
                    if (g.style.display === 'none') { state.hiddenStandaloneGroups.push(i); g.style.display = ''; }
                });
                document.querySelectorAll('.tab-bar, .standalone-tab-bar, .search-bar, .fab-bar, .toggle-wide-btn').forEach(function(el) {
                    el.dataset.prevDisplay = el.style.display || ''; el.style.display = 'none';
                });
                document.querySelectorAll('.toggle-dark-btn').forEach(function(el) {
                    el.dataset.prevDisplay = el.style.display || ''; el.style.display = 'none';
                });
                document.querySelectorAll('.reading-progress').forEach(function(el) { el.style.display = 'none'; });
                document.querySelectorAll('.header-watermark').forEach(function(el) { el.style.display = 'none'; });
                return state;
            }

            function restoreAfterScreenshot(state) {
                if (state.wasWide) document.body.classList.add('wide-mode');
                if (state.wasDark) document.body.classList.add('dark-mode');
                var groups = document.querySelectorAll('.word-group[data-tab-index]');
                state.hiddenGroups.forEach(function(i) { if (groups[i]) groups[i].style.display = 'none'; });
                var standaloneGroups = document.querySelectorAll('.standalone-group[data-standalone-tab]');
                if (state.hiddenStandaloneGroups) {
                    state.hiddenStandaloneGroups.forEach(function(i) { if (standaloneGroups[i]) standaloneGroups[i].style.display = 'none'; });
                }
                document.querySelectorAll('.tab-bar, .standalone-tab-bar, .search-bar, .fab-bar, .toggle-wide-btn').forEach(function(el) {
                    el.style.display = el.dataset.prevDisplay || ''; delete el.dataset.prevDisplay;
                });
                document.querySelectorAll('.toggle-dark-btn').forEach(function(el) {
                    el.style.display = el.dataset.prevDisplay || ''; delete el.dataset.prevDisplay;
                });
                document.querySelectorAll('.reading-progress').forEach(function(el) { el.style.display = ''; });
                document.querySelectorAll('.header-watermark').forEach(function(el) { el.style.display = ''; });
                initTabVisibility(); initCollapseVisibility(); initStandaloneTabVisibility();
                var fabBar = document.querySelector('.fab-bar');
                if (fabBar && window.scrollY > 300) fabBar.classList.add('visible');
            }

            async function saveAsImage() {
                const button = event.target; const originalText = button.textContent;
                try {
                    button.textContent = '生成中...'; button.disabled = true; window.scrollTo(0, 0);
                    await new Promise(resolve => setTimeout(resolve, 200));

                    var screenshotState = prepareForScreenshot();
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'hidden';
                    await new Promise(resolve => setTimeout(resolve, 100));

                    const container = document.querySelector('.container');
                    const canvas = await html2canvas(container, {
                        backgroundColor: '#ffffff', scale: 1.5, useCORS: true, allowTaint: false,
                        imageTimeout: 10000, removeContainer: false, foreignObjectRendering: false, logging: false,
                        width: container.offsetWidth, height: container.offsetHeight,
                        x: 0, y: 0, scrollX: 0, scrollY: 0, windowWidth: window.innerWidth, windowHeight: window.innerHeight
                    });

                    buttons.style.visibility = 'visible'; restoreAfterScreenshot(screenshotState);

                    const link = document.createElement('a'); const now = new Date();
                    const filename = `TrendRadar_雷达简报_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}$${String(now.getDate()).padStart(2, '0')}_$${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}.png`;

                    link.download = filename; link.href = canvas.toDataURL('image/png', 1.0);
                    document.body.appendChild(link); link.click(); document.body.removeChild(link);

                    button.textContent = '保存成功!';
                    setTimeout(() => { button.textContent = originalText; button.disabled = false; }, 2000);
                } catch (error) {
                    const buttons = document.querySelector('.save-buttons'); buttons.style.visibility = 'visible';
                    restoreAfterScreenshot(screenshotState); button.textContent = '保存失败';
                    setTimeout(() => { button.textContent = originalText; button.disabled = false; }, 2000);
                }
            }

            async function saveAsMultipleImages() {
                const button = event.target; const originalText = button.textContent;
                const container = document.querySelector('.container'); const scale = 1.5; const maxHeight = 5000 / scale;
                var screenshotState2 = prepareForScreenshot();

                try {
                    button.textContent = '分析中...'; button.disabled = true;
                    const newsItems = Array.from(container.querySelectorAll('.news-item'));
                    const wordGroups = Array.from(container.querySelectorAll('.word-group'));
                    const newSection = container.querySelector('.new-section');
                    const errorSection = container.querySelector('.error-section');
                    const header = container.querySelector('.header');
                    const footer = container.querySelector('.footer');

                    const containerRect = container.getBoundingClientRect(); const elements = [];
                    elements.push({ type: 'header', element: header, top: 0, bottom: header.offsetHeight, height: header.offsetHeight });

                    if (errorSection) {
                        const rect = errorSection.getBoundingClientRect();
                        elements.push({ type: 'error', element: errorSection, top: rect.top - containerRect.top, bottom: rect.bottom - containerRect.top, height: rect.height });
                    }

                    wordGroups.forEach(group => {
                        const groupRect = group.getBoundingClientRect();
                        const groupNewsItems = group.querySelectorAll('.news-item');
                        const wordHeader = group.querySelector('.word-header');
                        if (wordHeader) {
                            const headerRect = wordHeader.getBoundingClientRect();
                            elements.push({ type: 'word-header', element: wordHeader, parent: group, top: groupRect.top - containerRect.top, bottom: headerRect.bottom - containerRect.top, height: headerRect.height });
                        }
                        groupNewsItems.forEach(item => {
                            const rect = item.getBoundingClientRect();
                            elements.push({ type: 'news-item', element: item, parent: group, top: rect.top - containerRect.top, bottom: rect.bottom - containerRect.top, height: rect.height });
                        });
                    });

                    if (newSection) {
                        const rect = newSection.getBoundingClientRect();
                        elements.push({ type: 'new-section', element: newSection, top: rect.top - containerRect.top, bottom: rect.bottom - containerRect.top, height: rect.height });
                    }

                    const footerRect = footer.getBoundingClientRect();
                    elements.push({ type: 'footer', element: footer, top: footerRect.top - containerRect.top, bottom: footerRect.bottom - containerRect.top, height: footer.offsetHeight });

                    const segments = []; let currentSegment = { start: 0, end: 0, height: 0, includeHeader: true };
                    let headerHeight = header.offsetHeight; currentSegment.height = headerHeight;

                    for (let i = 1; i < elements.length; i++) {
                        const element = elements[i]; const potentialHeight = element.bottom - currentSegment.start;
                        if (potentialHeight > maxHeight && currentSegment.height > headerHeight) {
                            currentSegment.end = elements[i - 1].bottom; segments.push(currentSegment);
                            currentSegment = { start: currentSegment.end, end: 0, height: element.bottom - currentSegment.end, includeHeader: false };
                        } else {
                            currentSegment.height = potentialHeight; currentSegment.end = element.bottom;
                        }
                    }
                    if (currentSegment.height > 0) { currentSegment.end = container.offsetHeight; segments.push(currentSegment); }

                    button.textContent = `生成中 (0/${segments.length})...`;
                    const buttons = document.querySelector('.save-buttons'); buttons.style.visibility = 'hidden';

                    const images = [];
                    for (let i = 0; i < segments.length; i++) {
                        const segment = segments[i]; button.textContent = `生成中 ($${i + 1}/$${segments.length})...`;
                        const tempContainer = document.createElement('div');
                        tempContainer.style.cssText = `position: absolute; left: -9999px; top: 0; width: ${container.offsetWidth}px; background: white;`;
                        tempContainer.className = 'container';

                        const clonedContainer = container.cloneNode(true);
                        const clonedButtons = clonedContainer.querySelector('.save-buttons');
                        if (clonedButtons) { clonedButtons.style.display = 'none'; }

                        tempContainer.appendChild(clonedContainer); document.body.appendChild(tempContainer);
                        await new Promise(resolve => setTimeout(resolve, 100));

                        const canvas = await html2canvas(clonedContainer, {
                            backgroundColor: '#ffffff', scale: scale, useCORS: true, allowTaint: false,
                            imageTimeout: 10000, logging: false, width: container.offsetWidth, height: segment.end - segment.start,
                            x: 0, y: segment.start, windowWidth: window.innerWidth, windowHeight: window.innerHeight
                        });

                        images.push(canvas.toDataURL('image/png', 1.0)); document.body.removeChild(tempContainer);
                    }

                    buttons.style.visibility = 'visible';
                    const now = new Date();
                    const baseFilename = `TrendRadar_雷达简报_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}$${String(now.getDate()).padStart(2, '0')}_$${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;

                    for (let i = 0; i < images.length; i++) {
                        const link = document.createElement('a'); link.download = `$${baseFilename}_part$${i + 1}.png`;
                        link.href = images[i]; document.body.appendChild(link); link.click(); document.body.removeChild(link);
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }

                    button.textContent = `已保存 ${segments.length} 张图片!`;
                    restoreAfterScreenshot(screenshotState2);
                    setTimeout(() => { button.textContent = originalText; button.disabled = false; }, 2000);

                } catch (error) {
                    const buttons = document.querySelector('.save-buttons'); buttons.style.visibility = 'visible';
                    restoreAfterScreenshot(screenshotState2); button.textContent = '保存失败';
                    setTimeout(() => { button.textContent = originalText; button.disabled = false; }, 2000);
                }
            }

            function saveAsMarkdown() {
                var lines = []; var now = new Date();
                var dateStr = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
                var timeStr = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');

                var headerTitle = document.querySelector('.header-title');
                lines.push('# ' + (headerTitle ? headerTitle.textContent.trim() : '雷达简报')); lines.push('');

                function extractItem(item, idx) {
                    var titleEl = item.querySelector('.news-title a');
                    var titleText = ''; var url = '';
                    if (titleEl) { titleText = titleEl.textContent.trim(); url = titleEl.href || ''; }
                    else { var titleDiv = item.querySelector('.news-title') || item.querySelector('.new-item-title'); if (titleDiv) titleText = titleDiv.textContent.trim(); }
                    if (!titleText) return '';

                    var meta = [];
                    var rank = item.querySelector('.rank-num, .new-item-rank');
                    if (rank && rank.textContent.trim() && rank.textContent.trim() !== '?') meta.push('#' + rank.textContent.trim());
                    var source = item.querySelector('.source-name'); if (source) meta.push(source.textContent.trim());
                    var keyword = item.querySelector('.keyword-tag'); if (keyword) meta.push(keyword.textContent.trim());
                    var time = item.querySelector('.time-info'); if (time) meta.push(time.textContent.trim());
                    var count = item.querySelector('.count-info'); if (count) meta.push(count.textContent.trim());

                    var line = idx + '. ';
                    if (url) { line += '[' + titleText.replace(/[[\]]/g, '') + '](' + url + ')'; } else { line += titleText; }
                    if (meta.length) line += '  `' + meta.join(' | ') + '`';
                    return line;
                }

                var wordGroups = document.querySelectorAll('.hotlist-section > .word-group');
                if (wordGroups.length) {
                    lines.push('## 热点新闻'); lines.push('');
                    wordGroups.forEach(function(group) {
                        var wordName = group.querySelector('.word-name'); var wordCount = group.querySelector('.word-count');
                        if (wordName) { lines.push('### ' + wordName.textContent.trim() + (wordCount ? ' (' + wordCount.textContent.trim() + ')' : '')); lines.push(''); }
                        var items = group.querySelectorAll('.news-item');
                        items.forEach(function(item, i) { var line = extractItem(item, i + 1); if (line) lines.push(line); });
                        lines.push('');
                    });
                }

                var newSection = document.querySelector('.new-section');
                if (newSection) {
                    var newTitle = newSection.querySelector('.new-section-title');
                    lines.push('## ' + (newTitle ? newTitle.textContent.trim() : '本次新增热点')); lines.push('');
                    var sourceGroups = newSection.querySelectorAll('.new-source-group');
                    sourceGroups.forEach(function(sg) {
                        var srcTitle = sg.querySelector('.new-source-title');
                        if (srcTitle) { lines.push('### ' + srcTitle.textContent.trim()); lines.push(''); }
                        var items = sg.querySelectorAll('.new-item');
                        items.forEach(function(item, i) { var line = extractItem(item, i + 1); if (line) lines.push(line); });
                        lines.push('');
                    });
                }

                var standaloneSection = document.querySelector('.standalone-section');
                if (standaloneSection) {
                    var standaloneTitle = standaloneSection.querySelector('.standalone-section-title');
                    lines.push('## ' + (standaloneTitle ? standaloneTitle.textContent.trim() : '独立展示区')); lines.push('');
                    var groups = standaloneSection.querySelectorAll('.standalone-group');
                    groups.forEach(function(group) {
                        var name = group.querySelector('.standalone-name'); var cnt = group.querySelector('.standalone-count');
                        if (name) { lines.push('### ' + name.textContent.trim() + (cnt ? ' (' + cnt.textContent.trim() + ')' : '')); lines.push(''); }
                        var items = group.querySelectorAll('.news-item');
                        items.forEach(function(item, i) { var line = extractItem(item, i + 1); if (line) lines.push(line); });
                        lines.push('');
                    });
                }

                var errorSection = document.querySelector('.error-section');
                if (errorSection) {
                    var errorItems = errorSection.querySelectorAll('.error-item');
                    if (errorItems.length) {
                        lines.push('## 抓取异常'); lines.push('');
                        errorItems.forEach(function(item) { lines.push('- ' + item.textContent.trim()); });
                        lines.push('');
                    }
                }

                lines.push('---'); lines.push('*Generated by TrendRadar*');

                var md = lines.join('\\n');
                var blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
                var link = document.createElement('a'); var filename = 'TrendRadar_' + dateStr + '_' + timeStr.replace(':', '') + '.md';
                link.download = filename; link.href = URL.createObjectURL(blob);
                document.body.appendChild(link); link.click(); document.body.removeChild(link); URL.revokeObjectURL(link.href);
            }

            document.addEventListener('DOMContentLoaded', function() {
                window.scrollTo(0, 0);

                var savedMode = null;
                try { savedMode = localStorage.getItem('trendradar-wide-mode'); } catch(e) {}
                if (savedMode === '1' || (savedMode === null && window.innerWidth > 768)) {
                    document.body.classList.add('wide-mode');
                    var btn = document.querySelector('.toggle-wide-btn');
                    if (btn) btn.textContent = '⊡';
                }

                var savedDark = null;
                try { savedDark = localStorage.getItem('trendradar-dark-mode'); } catch(e) {}
                if (savedDark === '1') {
                    document.body.classList.add('dark-mode');
                    var darkBtn = document.querySelector('.toggle-dark-btn');
                    if (darkBtn) darkBtn.textContent = '☀';
                }

                var searchBar = document.querySelector('.search-bar');
                if (searchBar) searchBar.style.display = 'block';

                initTabs(); initBackToTop(); initCollapse(); initStandaloneTabs();

                document.addEventListener('keydown', function(e) {
                    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
                    var helpBtn = document.querySelector('.fab-help');
                    switch(e.key) {
                        case '?':
                            if (helpBtn) { helpBtn.classList.toggle('show-tip'); var fabBar = document.querySelector('.fab-bar'); if (fabBar) fabBar.classList.add('visible'); }
                            break;
                        case 'Escape': if (helpBtn) helpBtn.classList.remove('show-tip'); break;
                        case 'w': case 'W': toggleWideMode(); break;
                        case 'd': case 'D': toggleDarkMode(); break;
                        case '/': e.preventDefault(); var si = document.querySelector('.search-input'); if (si) si.focus(); break;
                    }
                });

                var progressBar = document.querySelector('.reading-progress');
                if (progressBar) {
                    window.addEventListener('scroll', function() {
                        var h = document.documentElement.scrollHeight - window.innerHeight;
                        progressBar.style.width = (h > 0 ? (window.scrollY / h * 100) : 0) + '%';
                    });
                }

                var copySvg = '<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="5" y="5" width="9" height="9" rx="1.5"/><path d="M5 11H3.5A1.5 1.5 0 012 9.5v-7A1.5 1.5 0 013.5 1h7A1.5 1.5 0 0112 2.5V5"/></svg>';
                var checkSvg = '<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="#22c55e" stroke-width="2"><path d="M3 8.5l3.5 3.5 7-7"/></svg>';
                document.querySelectorAll('.news-item .news-number').forEach(function(numEl) {
                    var item = numEl.closest('.news-item');
                    var titleEl = item ? item.querySelector('.news-title a') : null;
                    if (!titleEl) return;
                    var numText = numEl.textContent.trim();
                    numEl.innerHTML = '<span class="num-text">' + numText + '</span><span class="copy-icon">' + copySvg + '</span>';
                    numEl.title = '点击复制标题和链接';
                    numEl.addEventListener('click', function(e) {
                        e.stopPropagation();
                        var text = titleEl.textContent.trim() + ' ' + titleEl.href;
                        navigator.clipboard.writeText(text).then(function() {
                            numEl.classList.add('copied'); numEl.querySelector('.copy-icon').innerHTML = checkSvg;
                            setTimeout(function() { numEl.classList.remove('copied'); numEl.querySelector('.copy-icon').innerHTML = copySvg; }, 1500);
                        });
                    });
                });

                (function() {
                    var header = document.querySelector('.header');
                    var watermark = document.querySelector('.header-watermark');
                    if (!header || !watermark) return;

                    var radius = 120;
                    header.addEventListener('mousemove', function(e) {
                        var rect = watermark.getBoundingClientRect();
                        var x = e.clientX - rect.left; var y = e.clientY - rect.top;
                        var maskVal = 'radial-gradient(circle ' + radius + 'px at ' + x + 'px ' + y + 'px, rgba(0,0,0,1) 0%, rgba(0,0,0,0.12) 55%, transparent 100%)';
                        watermark.style.webkitMaskImage = maskVal; watermark.style.maskImage = maskVal;
                        watermark.style.color = 'rgba(255, 255, 255, 0.18)';
                    });

                    header.addEventListener('mouseleave', function() {
                        watermark.style.webkitMaskImage = 'radial-gradient(circle 0px at 50% 50%, rgba(0,0,0,1) 0%, transparent 100%)';
                        watermark.style.maskImage = 'radial-gradient(circle 0px at 50% 50%, rgba(0,0,0,1) 0%, transparent 100%)';
                        watermark.style.color = 'rgba(255, 255, 255, 0.055)';
                    });
                })();
            });

            // ===== 天气套件初始化逻辑 =====
            (function initWeatherSuite() {
                var pad = function(n) { return String(n).padStart(2, '0'); };
                var now = new Date();
                var tmr = new Date(now); tmr.setDate(tmr.getDate() + 1);
                var weekNames = ['周日','周一','周二','周三','周四','周五','周六'];

                document.getElementById('tmrDate').textContent = (tmr.getMonth() + 1) + '月' + tmr.getDate() + '日 · ' + weekNames[tmr.getDay()];

                // 使用 Meteocons 原生 Animated SVGs 代替 Lottie JS，100% 兼容性
                var CDN = 'https://cdn.jsdelivr.net/npm/@basmilius/weather-icons@2.0.1/production/line/all/';

                // WMO 映射表 (精确映射到已存在的 SVG)
                var WMO = {
                    0:  {d:'clear-day', n:'clear-night', t:'晴'},
                    1:  {d:'partly-cloudy-day', n:'partly-cloudy-night', t:'大部晴'},
                    2:  {d:'partly-cloudy-day', n:'partly-cloudy-night', t:'多云'},
                    3:  {d:'overcast-day', n:'overcast-night', t:'阴'},
                    45: {d:'fog-day', n:'fog-night', t:'雾'},
                    48: {d:'fog-day', n:'fog-night', t:'雾凇'},
                    51: {d:'partly-cloudy-day-drizzle', n:'partly-cloudy-night-drizzle', t:'毛毛雨'},
                    53: {d:'partly-cloudy-day-drizzle', n:'partly-cloudy-night-drizzle', t:'毛毛雨'},
                    55: {d:'partly-cloudy-day-drizzle', n:'partly-cloudy-night-drizzle', t:'大毛毛雨'},
                    61: {d:'partly-cloudy-day-rain', n:'partly-cloudy-night-rain', t:'小雨'},
                    63: {d:'rain', n:'rain', t:'中雨'},
                    65: {d:'extreme-rain', n:'extreme-rain', t:'大雨'},
                    71: {d:'partly-cloudy-day-snow', n:'partly-cloudy-night-snow', t:'小雪'},
                    73: {d:'snow', n:'snow', t:'中雪'},
                    75: {d:'extreme-snow', n:'extreme-snow', t:'大雪'},
                    77: {d:'sleet', n:'sleet', t:'冰粒'},
                    80: {d:'partly-cloudy-day-rain', n:'partly-cloudy-night-rain', t:'阵雨'},
                    81: {d:'rain', n:'rain', t:'中阵雨'},
                    82: {d:'extreme-rain', n:'extreme-rain', t:'强阵雨'},
                    85: {d:'snow', n:'snow', t:'阵雪'},
                    86: {d:'extreme-snow', n:'extreme-snow', t:'强阵雪'},
                    95: {d:'thunderstorms-day', n:'thunderstorms-night', t:'雷暴'},
                    96: {d:'thunderstorms-day-overcast-rain', n:'thunderstorms-night-overcast-rain', t:'雷暴冰雹'},
                    99: {d:'thunderstorms-day-overcast-rain', n:'thunderstorms-night-overcast-rain', t:'强雷暴'},
                };

                function wmoGet(c) { return WMO[c] || WMO[3]; }
                function iconUrl(c, isDay) { var e = wmoGet(c); return CDN + (isDay ? e.d : e.n) + '.svg'; }
                function wmoDesc(c) { return wmoGet(c).t; }

                var SKY = {
                    0:  {d:'linear-gradient(160deg,#1565c0 0%,#1e88e5 35%,#42a5f5 70%,#81d4fa 100%)',
                         n:'linear-gradient(160deg,#050d1f 0%,#0a1628 40%,#0d2040 100%)'},
                    1:  {d:'linear-gradient(160deg,#1565c0 0%,#1e88e5 35%,#42a5f5 70%,#81d4fa 100%)',
                         n:'linear-gradient(160deg,#050d1f 0%,#0a1628 40%,#0d2040 100%)'},
                    2:  {d:'linear-gradient(160deg,#546e7a 0%,#78909c 50%,#90a4ae 100%)',
                         n:'linear-gradient(160deg,#1a2535 0%,#263040 50%,#2e3d50 100%)'},
                    3:  {d:'linear-gradient(160deg,#546e7a 0%,#607d8b 50%,#78909c 100%)',
                         n:'linear-gradient(160deg,#1a2535 0%,#263040 50%,#2e3d50 100%)'},
                };
                function getSky(code, isDay) {
                    var s = SKY[code] || (code <= 3 ? SKY[code] : null);
                    if (!s) {
                        if (code >= 45 && code <= 48) return isDay ? 'linear-gradient(160deg,#6b7280 0%,#9ca3af 100%)' : 'linear-gradient(160deg,#1f2937 0%,#374151 100%)';
                        if (code >= 51 && code <= 67 || code >= 80 && code <= 82) return 'linear-gradient(160deg,#263238 0%,#37474f 50%,#455a64 100%)';
                        if (code >= 71 && code <= 77 || code >= 85 && code <= 86) return 'linear-gradient(160deg,#4a5568 0%,#718096 50%,#a0aec0 100%)';
                        if (code >= 95) return 'linear-gradient(160deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)';
                        return isDay ? 'linear-gradient(160deg,#1565c0 0%,#42a5f5 100%)' : 'linear-gradient(160deg,#050d1f 0%,#0d2040 100%)';
                    }
                    return isDay ? s.d : s.n;
                }

                var svgDrop = '<svg class="wt-detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2C12 2 5 10 5 15a7 7 0 0014 0C19 10 12 2 12 2z"/></svg>';
                var svgTherm = '<svg class="wt-detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 14.76V3.5a2.5 2.5 0 00-5 0v11.26a4.5 4.5 0 105 0z"/></svg>';
                var svgWind = '<svg class="wt-detail-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.59 4.59A2 2 0 1111 8H2m10.59 11.41A2 2 0 1014 16H2m15.73-8.27A2.5 2.5 0 1119.5 12H2"/></svg>';

                var UNIFORMS = [
                    null,
                    {name:'黑色工服', color:'#1a1a1a'},
                    {name:'金色工服', color:'#c9a227'},
                    {name:'红色工服', color:'#c0392b'},
                    {name:'黑色工服', color:'#1a1a1a'},
                    {name:'金色工服', color:'#c9a227'},
                    {name:'红色工服', color:'#c0392b'},
                    {name:'红色工服', color:'#c0392b'},
                ];
                function dayToIdx(d) { return d === 0 ? 7 : d; }

                function genClothingHint(tmax, tmin, pop, windKmh, wmoCode) {
                    var hints = [];
                    if (tmax <= 5) hints.push('气温较低，建议厚外套加保暖内搭');
                    else if (tmax <= 12) hints.push('天气偏凉，外套不可少');
                    else if (tmax <= 20) hints.push('温度适中，薄外套或卫衣即可');
                    else if (tmax <= 28) hints.push('气温舒适，轻薄穿搭为主');
                    else hints.push('天气较热，透气轻薄为主');

                    if (tmax - tmin >= 10) hints.push('早晚温差大，备一件外套');

                    if (wmoCode >= 71 && wmoCode <= 77 || wmoCode >= 85 && wmoCode <= 86) hints.push('有降雪，注意防滑保暖');
                    else if (pop >= 50) hints.push('降水概率高，记得带伞');
                    else if (pop >= 30) hints.push('可能有雨，备好雨具');

                    if (windKmh >= 40) hints.push('注意防风');
                    return hints.slice(0, 2).join('，');
                }

                function renderUniform(tmrWeatherData) {
                    var tmrDow = tmr.getDay();
                    var todayDow = now.getDay();
                    var u = UNIFORMS[dayToIdx(tmrDow)];

                    document.getElementById('uniformSwatch').style.background = u.color;
                    document.getElementById('uniformColorName').textContent = u.name;
                    document.getElementById('uniformDate').textContent = weekNames[tmrDow];

                    var hint = '';
                    if (tmrWeatherData) {
                        var daily = tmrWeatherData.daily;
                        var tmax = daily ? Math.round(daily.temperature_2m_max[1]) : 20;
                        var tmin = daily ? Math.round(daily.temperature_2m_min[1]) : 10;
                        var pop = daily && daily.precipitation_probability_max ? daily.precipitation_probability_max[1] : 0;
                        var wind = daily && daily.wind_speed_10m_max ? Math.round(daily.wind_speed_10m_max[1]) : 0;
                        var code = daily ? daily.weather_code[1] : 0;
                        hint = genClothingHint(tmax, tmin, pop, wind, code);
                    }
                    document.getElementById('uniformHint').textContent = hint || '—';

                    var weekEl = document.getElementById('uniformWeek');
                    weekEl.innerHTML = '';
                    var dayLabels = ['日','一','二','三','四','五','六'];
                    var order = [1,2,3,4,5,6,0];
                    order.forEach(function(d) {
                        var uu = UNIFORMS[dayToIdx(d)];
                        var isToday = (d === todayDow), isTmr = (d === tmrDow);
                        var dot = document.createElement('div');
                        dot.className = 'uniform-day-dot' + (isToday ? ' today' : '') + (isTmr ? ' tomorrow' : '');
                        dot.innerHTML =
                            '<div class="uniform-dot" style="background:' + uu.color + ';"></div>' +
                            '<div class="uniform-day-label">' + dayLabels[d] + '</div>';
                        weekEl.appendChild(dot);
                    });

                    document.getElementById('wtUniform').style.display = 'block';
                }

                function renderToday(data, city) {
                    var c = data.current, code = c.weather_code, isDay = !!c.is_day;
                    var temp = Math.round(c.temperature_2m), feel = Math.round(c.apparent_temperature);
                    var hum = c.relative_humidity_2m, wind = Math.round(c.wind_speed_10m);
                    var tmax = data.daily ? Math.round(data.daily.temperature_2m_max[0]) : null;
                    var tmin = data.daily ? Math.round(data.daily.temperature_2m_min[0]) : null;

                    document.getElementById('mainHeader').style.background = getSky(code, isDay);

                    var el = document.getElementById('wtToday');
                    el.classList.remove('loading');
                    // 使用原生 img 标签加载 Animated SVG，加入 fallback
                    var fallbackSrc = CDN + 'partly-cloudy-day.svg';
                    var imgHtml = '<img class="wt-icon" src="' + iconUrl(code, isDay) + '" alt="' + wmoDesc(code) + '" onerror="if(this.src.indexOf(\'rain.svg\')===-1){this.src=\'' + CDN + 'rain.svg\';}else{this.style.display=\'none\';}">';

                    el.innerHTML =
                        '<div class="wt-icon-wrap">' + imgHtml + '</div>' +
                        '<div class="wt-center">' +
                            '<div class="wt-temp-row"><span class="wt-temp">' + temp + '</span><span class="wt-unit">°C</span></div>' +
                            '<div class="wt-desc">' + wmoDesc(code) + '</div>' +
                            (tmax !== null ? '<div class="wt-range">最高 ' + tmax + '° · 最低 ' + tmin + '°</div>' : '') +
                        '</div>' +
                        '<div class="wt-right">' +
                            '<div class="wt-detail">' + svgDrop + '<span>湿度</span><span class="wt-detail-val">' + hum + '%</span></div>' +
                            '<div class="wt-detail">' + svgTherm + '<span>体感</span><span class="wt-detail-val">' + feel + '°</span></div>' +
                            '<div class="wt-detail">' + svgWind + '<span>风速</span><span class="wt-detail-val">' + wind + ' km/h</span></div>' +
                            '<div class="wt-detail">' + svgWind + '<span>风况</span><span class="wt-detail-val">' + windLabel(wind) + '</span></div>' +
                        '</div>';

                    document.getElementById('wtCity').textContent = city;
                    var t = new Date();
                    document.getElementById('wtUpdate').textContent = '更新于 ' + pad(t.getHours()) + ':' + pad(t.getMinutes());
                    document.getElementById('wtFooter').style.display = 'flex';
                }

                function windLabel(k) {
                    if(k < 1) return '静风'; if(k < 6) return '软风'; if(k < 12) return '轻风';
                    if(k < 20) return '微风'; if(k < 29) return '和风'; if(k < 39) return '清风';
                    if(k < 50) return '强风'; return '大风';
                }

                function renderHourly(data) {
                    var hourly = data.hourly; if (!hourly) return;
                    var times = hourly.time, temps = hourly.temperature_2m;
                    var codes = hourly.weather_code, pops = hourly.precipitation_probability;
                    var nowH = new Date(); nowH.setMinutes(0, 0, 0);
                    var nowTs = nowH.toISOString().slice(0, 13);
                    var startIdx = 0;
                    for (var i = 0; i < times.length; i++) { if (times[i].slice(0, 13) === nowTs) { startIdx = i; break; } }
                    var scroll = document.getElementById('hourlyScroll'); scroll.innerHTML = '';
                    for (var j = startIdx; j < Math.min(startIdx + 13, times.length); j++) {
                        var dt = new Date(times[j]), isNow = (j === startIdx);
                        var isD = dt.getHours() >= 6 && dt.getHours() < 19;
                        var pop = pops ? pops[j] : 0;
                        var item = document.createElement('div');
                        item.className = 'hourly-item' + (isNow ? ' now' : '');
                        
                        var imgHtml = '<img class="hourly-icon" src="' + iconUrl(codes[j], isD) + '" onerror="if(this.src.indexOf(\'rain.svg\')===-1){this.src=\'' + CDN + 'rain.svg\';}else{this.style.opacity=0;}">';
                        
                        item.innerHTML =
                            '<div class="hourly-time">' + (isNow ? '现在' : pad(dt.getHours()) + ':00') + '</div>' +
                            imgHtml +
                            '<div class="hourly-temp">' + Math.round(temps[j]) + '°</div>' +
                            (pop > 20 ? '<div class="hourly-pop">' + pop + '%</div>' : '<div class="hourly-pop" style="opacity:0">·</div>');
                        scroll.appendChild(item);
                    }
                    document.getElementById('wtHourly').style.display = 'block';
                }

                function renderTomorrow(data) {
                    var daily = data.daily; if (!daily || daily.time.length < 2) return;
                    var code = daily.weather_code[1];
                    var tmax = Math.round(daily.temperature_2m_max[1]);
                    var tmin = Math.round(daily.temperature_2m_min[1]);
                    var pop = daily.precipitation_probability_max ? daily.precipitation_probability_max[1] : null;
                    var wind = daily.wind_speed_10m_max ? Math.round(daily.wind_speed_10m_max[1]) : null;

                    document.getElementById('tmrDesc').textContent = wmoDesc(code);
                    document.getElementById('tmrRange').textContent = '最高 ' + tmax + '°  /  最低 ' + tmin + '°';

                    var tmrIcon = document.getElementById('tmrIcon');
                    tmrIcon.src = iconUrl(code, true);
                    tmrIcon.onerror = function() { if(this.src.indexOf('rain.svg')===-1) this.src = CDN + 'rain.svg'; else this.style.display = 'none'; };

                    var statsHtml = '';
                    if (pop !== null) statsHtml += '<div class="tmr-stat">' + svgDrop.replace('class="wt-detail-icon"', 'style="width:11px;height:11px;opacity:.7;"') + '<span class="tmr-stat-val">' + pop + '%</span><span>降水</span></div>';
                    if (wind !== null) statsHtml += '<div class="tmr-stat">' + svgWind.replace('class="wt-detail-icon"', 'style="width:11px;height:11px;opacity:.7;"') + '<span class="tmr-stat-val">' + wind + '</span><span>km/h</span></div>';
                    document.getElementById('tmrStats').innerHTML = statsHtml;

                    var refMin = Math.min(daily.temperature_2m_min[0], tmin) - 2;
                    var refMax = Math.max(daily.temperature_2m_max[0], tmax) + 2;
                    var range = refMax - refMin || 1;
                    document.getElementById('tmrBarMin').textContent = tmin + '°';
                    document.getElementById('tmrBarMax').textContent = tmax + '°';
                    document.getElementById('tmrBarFill').style.left = ((tmin - refMin) / range * 100).toFixed(1) + '%';
                    document.getElementById('tmrBarFill').style.right = (100 - (tmax - refMin) / range * 100).toFixed(1) + '%';
                    document.getElementById('wtTomorrow').style.display = 'block';
                }

                function fetchWeather(lat, lon, city) {
                    var url = 'https://api.open-meteo.com/v1/forecast' +
                        '?latitude=' + lat + '&longitude=' + lon +
                        '&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,is_day' +
                        '&hourly=temperature_2m,weather_code,precipitation_probability' +
                        '&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max' +
                        '&wind_speed_unit=kmh&timezone=auto&forecast_days=2';
                    fetch(url)
                        .then(function(r) { return r.json(); })
                        .then(function(d) {
                            renderToday(d, city);
                            renderHourly(d);
                            renderTomorrow(d);
                            renderUniform(d);
                        })
                        .catch(function() {
                            var el = document.getElementById('wtToday');
                            el.classList.remove('loading');
                            el.innerHTML = '<span style="font-size:12px;color:var(--tm);">天气数据暂时不可用</span>';
                            renderUniform(null);
                        });
                }

                // IP 定位
                fetch('https://ipapi.co/json/')
                    .then(function(r) { return r.json(); })
                    .then(function(g) {
                        fetchWeather(g.latitude || 39.9042, g.longitude || 116.4074, g.city || g.region || '当前位置');
                    })
                    .catch(function() {
                        fetchWeather(39.9042, 116.4074, '北京');
                    });
            })();
        </script>
    </body>
    </html>
    """

    return html
