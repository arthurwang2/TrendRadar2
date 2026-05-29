# coding=utf-8
"""LLM 返回 JSON 的提取与容错解析（json_repair + 兜底）"""

import json
import re
from typing import Any, Optional, Union


def extract_json_text(response: str) -> str:
    """从模型响应中提取 JSON 字符串（去 markdown 围栏）"""
    if not response:
        return ""
    text = response.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        parts = text.split("```", 2)
        if len(parts) >= 2:
            text = parts[1].strip()
    return text


def parse_json_loose(
    json_str: str,
    expect_type: type = dict,
) -> Optional[Union[dict, list]]:
    """
    先 json.loads，失败则用 json_repair 修复。
    expect_type: dict 或 list，用于校验顶层类型。
    """
    if not json_str or not json_str.strip():
        return None

    data = None
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        pass

    if data is None:
        try:
            from json_repair import repair_json

            repaired = repair_json(json_str, return_objects=True)
            if isinstance(repaired, expect_type):
                data = repaired
        except Exception:
            pass

    if data is None or not isinstance(data, expect_type):
        return None
    return data


def parse_json_from_llm(
    response: str,
    expect_type: type = dict,
    label: str = "JSON",
) -> Optional[Union[dict, list]]:
    """提取 + 容错解析；成功时可选打印修复日志（由调用方打印）"""
    json_str = extract_json_text(response)
    if not json_str:
        return None
    return parse_json_loose(json_str, expect_type=expect_type)


def fallback_tags_from_interests(interests_content: str) -> list:
    """
    标签提取失败时的静态回退（与 ai_interests_tesla_delivery.txt 结构对齐）
    保证 AI 筛选仍可走语义分类，不因 7B JSON 格式错误回退频率词。
    """
    tags = []
    for m in re.finditer(r"^\d+\.\s*(.+?)(?:\s*（|\s*$)", interests_content, re.MULTILINE):
        title = m.group(1).strip()
        if len(title) < 2:
            continue
        short = title.split("·")[-1].strip() if "·" in title else title
        tags.append({
            "tag": short[:32],
            "description": title[:200],
        })
    if tags:
        return tags
    return [
        {"tag": "竞品整车", "description": "具体品牌+车型+整车事件（上市/交付/改款等）"},
        {"tag": "储能", "description": "独立储能、电网调节、Megapack 类具体项目"},
        {"tag": "人形机器人", "description": "机器人量产、具身智能、供应链落地"},
        {"tag": "补能生态", "description": "超充、充电桩、补能基础设施布局"},
        {"tag": "电池与芯片", "description": "固态电池、车规芯片、供应链合作"},
        {"tag": "制造智能化", "description": "产线升级、自动化、质量检测进展"},
    ]
