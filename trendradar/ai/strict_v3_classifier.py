# coding=utf-8
"""
V3 严格分类器（TrendRadar 专用）

实现用户定义的 V3.1 严格规则：
- 仅处理两日内条目
- 硬块一票否决
- Class 1: 具体品牌+车型+整车事件（竞品整车动态）
- Class 2/3: 新能源 + AI 行业非整车赛道（不再强制要求 Tesla 相关）
- 纯语义判断 + 完整可追溯理由
- 直接输出可用于 Guizang 简报的干净结果

设计目标：每天对 TrendRadar 当日报 JSON（尤其是用户自己的 daily-json feed）做精确筛选。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from trendradar.ai.client import AIClient
from trendradar.ai.prompt_loader import load_prompt_template


@dataclass
class StrictV3Item:
    """严格分类后的单条结果"""
    id: int
    published_at: str
    title: str
    category: int  # 1, 2 或 3
    reason: str    # 详细语义理由，必须引用规则 + 原文证据


@dataclass
class StrictV3Result:
    """V3 严格分类完整结果"""
    class1: List[StrictV3Item] = field(default_factory=list)
    class2: List[StrictV3Item] = field(default_factory=list)
    class3: List[StrictV3Item] = field(default_factory=list)
    total_input: int = 0
    total_after_date_filter: int = 0
    total_after_hardblock: int = 0
    success: bool = False
    error: str = ""
    raw_response: str = ""


class StrictV3Classifier:
    """
    V3 严格分类器

    用法示例：
        classifier = StrictV3Classifier(ai_config, get_time_func=...)
        result = classifier.classify(raw_items_from_daily_json)
    """

    # 硬块列表（与用户反复确认的完整版一致）
    HARD_BLOCKS = [
        "事故", "伤亡", "火灾", "爆炸", "股价", "股票", "跌停",
        "拉踩", "超越 tesla", "超越Tesla",
        "工信部", "宏观", "渗透率", "国补", "补贴", "国标", "监管升级",
        "安全排查", "电池回收", "质保到期", "退役电池",
        "新闻联播", "官员任免", "国际局势"
    ]

    def __init__(
        self,
        ai_config: Dict[str, Any],
        get_time_func=None,
        debug: bool = False,
    ):
        self.client = AIClient(ai_config)
        self.get_time_func = get_time_func or (lambda: datetime.now())
        self.debug = debug

        # 加载专用 prompt（config/strict_v3_prompt.txt）
        self.system_prompt, self.user_prompt_template = load_prompt_template(
            "strict_v3_prompt.txt",
            label="StrictV3",
        )

    def _is_hard_blocked(self, text: str) -> bool:
        """硬块过滤"""
        t = text.lower()
        for block in self.HARD_BLOCKS:
            if block.lower() in t:
                return True
        return False

    def _filter_two_days(self, items: List[Dict], reference_date: Optional[datetime] = None) -> List[Dict]:
        """
        严格两日过滤。
        如果 reference_date 为 None，则使用当天日期往前推两天。
        """
        if not items:
            return []

        if reference_date is None:
            reference_date = self.get_time_func()

        # 简单策略：保留 published_at 以最近两个日期字符串开头的条目
        # 更精确的实现可解析 datetime，这里先用字符串前缀匹配（用户实际使用中可靠）
        today_str = reference_date.strftime("%Y-%m-%d")
        yesterday = reference_date - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y-%m-%d")

        filtered = []
        for item in items:
            pub = str(item.get("published_at", ""))
            if pub.startswith(today_str) or pub.startswith(yesterday_str):
                filtered.append(item)
        return filtered

    def classify(
        self,
        raw_items: List[Dict],
        reference_date: Optional[datetime] = None,
    ) -> StrictV3Result:
        """
        主入口：对原始 TrendRadar JSON 条目列表执行 V3 严格分类。

        Args:
            raw_items: 原始条目列表（包含 id, title, summary, published_at, feed_id 等）
            reference_date: 参考日期（用于两日过滤）

        Returns:
            StrictV3Result
        """
        result = StrictV3Result(total_input=len(raw_items))

        if not raw_items:
            result.success = True
            return result

        # 1. 两日过滤
        two_day_items = self._filter_two_days(raw_items, reference_date)
        result.total_after_date_filter = len(two_day_items)

        if not two_day_items:
            result.success = True
            return result

        # 2. 硬块预过滤（Python 层，节省 token）
        candidates = []
        for item in two_day_items:
            title = item.get("title", "")
            summary = item.get("summary", "")
            full_text = f"{title} {summary}"
            if not self._is_hard_blocked(full_text):
                candidates.append(item)

        result.total_after_hardblock = len(candidates)

        if not candidates:
            result.success = True
            return result

        # 3. 构造发给 LLM 的精简 payload（只保留关键字段，控制 token）
        payload = []
        for item in candidates:
            payload.append({
                "id": item.get("id"),
                "published_at": item.get("published_at"),
                "title": item.get("title", "")[:120],
                "summary": (item.get("summary") or "")[:300],
                "feed_id": item.get("feed_id", ""),
            })

        items_json = json.dumps(payload, ensure_ascii=False, indent=2)

        # 4. 填充 prompt
        user_prompt = self.user_prompt_template.replace("{items_json}", items_json)

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        if self.debug:
            print("[StrictV3] 发送给 AI 的候选条目数:", len(payload))

        # 5. 调用 LLM
        try:
            response = self.client.chat(messages)
            result.raw_response = response

            parsed = self._parse_response(response)
            if parsed:
                result.class1 = parsed.get("class1", [])
                result.class2 = parsed.get("class2", [])
                result.class3 = parsed.get("class3", [])
                result.success = True
            else:
                result.error = "AI 返回内容解析失败"
                result.success = False

        except Exception as e:
            result.error = f"AI 调用失败: {type(e).__name__}: {str(e)[:200]}"
            result.success = False

        return result

    def _parse_response(self, response: str) -> Optional[Dict]:
        """从 AI 响应中提取并校验 JSON"""
        if not response:
            return None

        json_str = response.strip()

        # 去掉可能的 markdown 代码块
        if "```json" in json_str:
            json_str = json_str.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            data = json.loads(json_str)
            # 基本结构校验
            if not isinstance(data, dict):
                return None

            def parse_list(key: str) -> List[StrictV3Item]:
                lst = data.get(key, [])
                out = []
                for x in lst:
                    if isinstance(x, dict) and "id" in x and "category" in x:
                        out.append(StrictV3Item(
                            id=int(x["id"]),
                            published_at=str(x.get("published_at", "")),
                            title=str(x.get("title", ""))[:60],
                            category=int(x.get("category", 0)),
                            reason=str(x.get("reason", "")),
                        ))
                return out

            return {
                "class1": parse_list("class1"),
                "class2": parse_list("class2"),
                "class3": parse_list("class3"),
            }
        except Exception:
            return None


# 便捷函数（推荐在 report 流程中直接调用）
def run_strict_v3_on_daily_json(
    raw_items: List[Dict],
    ai_config: Dict[str, Any],
    reference_date: Optional[datetime] = None,
    debug: bool = False,
) -> StrictV3Result:
    """
    一行代码调用 V3 严格分类（最常用入口）
    """
    classifier = StrictV3Classifier(ai_config, debug=debug)
    return classifier.classify(raw_items, reference_date=reference_date)
