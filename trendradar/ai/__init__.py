# coding=utf-8
"""
TrendRadar AI 模块

提供 AI 大模型对热点新闻的深度分析和翻译功能
"""

from .analyzer import AIAnalyzer, AIAnalysisResult
from .filter import AIFilter, AIFilterResult
from .strict_v3_classifier import StrictV3Classifier, StrictV3Result, StrictV3Item, run_strict_v3_on_daily_json
from .translator import AITranslator, TranslationResult, BatchTranslationResult
from .formatter import (
    get_ai_analysis_renderer,
    render_ai_analysis_markdown,
    render_ai_analysis_feishu,
    render_ai_analysis_dingtalk,
    render_ai_analysis_html,
    render_ai_analysis_html_rich,
    render_ai_analysis_plain,
)

__all__ = [
    # 分析器
    "AIAnalyzer",
    "AIAnalysisResult",
    # 智能筛选
    "AIFilter",
    "AIFilterResult",
    # V3 严格分类器（用户自定义竞品整车 + 新能源/AI非整车赛道）
    "StrictV3Classifier",
    "StrictV3Result",
    "StrictV3Item",
    "run_strict_v3_on_daily_json",
    # 翻译器
    "AITranslator",
    "TranslationResult",
    "BatchTranslationResult",
    # 格式化
    "get_ai_analysis_renderer",
    "render_ai_analysis_markdown",
    "render_ai_analysis_feishu",
    "render_ai_analysis_dingtalk",
    "render_ai_analysis_html",
    "render_ai_analysis_html_rich",
    "render_ai_analysis_plain",
]
