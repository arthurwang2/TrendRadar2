# coding=utf-8
"""
V3 严格分类器（TrendRadar 专用）

实现用户定义的 V3.1 严格规则：
- 仅处理两日内条目
- 硬块一票否决（Python 层，非语义）
- 全量分批语义扫描：小模型按 batch 逐批判断，避免单次上下文撑爆
- Class 1: 具体品牌+车型+整车事件（竞品整车动态）
- Class 2/3: 新能源 + AI 行业非整车赛道（不再强制要求 Tesla 相关）
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from trendradar.ai.client import AIClient
from trendradar.ai.json_utils import parse_json_from_llm
from trendradar.ai.prompt_loader import load_prompt_template


@dataclass
class StrictV3Item:
    """严格分类后的单条结果"""
    id: int
    published_at: str
    title: str
    category: int  # 1, 2 或 3
    reason: str


@dataclass
class StrictV3Result:
    """V3 严格分类完整结果"""
    class1: List[StrictV3Item] = field(default_factory=list)
    class2: List[StrictV3Item] = field(default_factory=list)
    class3: List[StrictV3Item] = field(default_factory=list)
    total_input: int = 0
    total_after_date_filter: int = 0
    total_after_hardblock: int = 0
    batches_processed: int = 0
    success: bool = False
    error: str = ""
    raw_response: str = ""


class StrictV3Classifier:
    """V3 严格分类器（支持全量分批语义扫描）"""

    HARD_BLOCKS = [
        "事故", "伤亡", "火灾", "爆炸", "股价", "股票", "跌停",
        "拉踩", "超越 tesla", "超越Tesla",
        "工信部", "宏观", "渗透率", "国补", "补贴", "国标", "监管升级",
        "安全排查", "电池回收", "质保到期", "退役电池",
        "新闻联播", "官员任免", "国际局势",
    ]

    def __init__(
        self,
        ai_config: Dict[str, Any],
        get_time_func=None,
        debug: bool = False,
        batch_size: int = 10,
        batch_interval: float = 8.0,
        max_candidates: int = 0,
        batch_timeout: int = 240,
        batch_retries: int = 2,
    ):
        self.client = AIClient(ai_config)
        self.get_time_func = get_time_func or (lambda: datetime.now())
        self.debug = debug
        self.batch_size = max(5, min(batch_size, 12))
        self.batch_interval = max(0, batch_interval)
        self.max_candidates = max(0, max_candidates)
        self.batch_timeout = max(60, batch_timeout)
        self.batch_retries = max(1, batch_retries)

        self.system_prompt, self.user_prompt_template = load_prompt_template(
            "strict_v3_prompt.txt",
            label="StrictV3",
        )

    def _is_hard_blocked(self, text: str) -> bool:
        t = text.lower()
        for block in self.HARD_BLOCKS:
            if block.lower() in t:
                return True
        return False

    def _filter_two_days(self, items: List[Dict], reference_date: Optional[datetime] = None) -> List[Dict]:
        if not items:
            return []
        if reference_date is None:
            reference_date = self.get_time_func()
        today_str = reference_date.strftime("%Y-%m-%d")
        yesterday_str = (reference_date - timedelta(days=1)).strftime("%Y-%m-%d")
        filtered = []
        for item in items:
            pub = str(item.get("published_at", ""))
            if pub.startswith(today_str) or pub.startswith(yesterday_str):
                filtered.append(item)
        return filtered

    def _to_payload_item(self, item: Dict) -> Dict:
        return {
            "id": item.get("id"),
            "published_at": item.get("published_at"),
            "title": str(item.get("title", ""))[:120],
            "summary": str(item.get("summary") or "")[:300],
            "feed_id": item.get("feed_id", ""),
        }

    def _parse_response(self, response: str) -> Optional[Dict]:
        if not response:
            return None
        data = parse_json_from_llm(response, expect_type=dict)
        if not data:
            try:
                from json_repair import repair_json
                from trendradar.ai.json_utils import extract_json_text

                repaired = repair_json(extract_json_text(response), return_objects=True)
                if isinstance(repaired, dict):
                    data = repaired
                    print("[StrictV3] 批次 JSON 本地修复成功（json_repair）")
            except Exception:
                return None

        def parse_list(key: str) -> List[StrictV3Item]:
            out = []
            for x in data.get(key, []):
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

    def _merge_parsed(self, target: StrictV3Result, parsed: Dict) -> None:
        seen = {x.id for x in target.class1 + target.class2 + target.class3}

        def add_items(items: List[StrictV3Item], bucket: List[StrictV3Item]) -> None:
            for it in items:
                if it.id in seen:
                    continue
                seen.add(it.id)
                bucket.append(it)

        add_items(parsed.get("class1", []), target.class1)
        add_items(parsed.get("class2", []), target.class2)
        add_items(parsed.get("class3", []), target.class3)

    def _classify_one_batch(self, batch: List[Dict], batch_no: int, total_batches: int) -> Optional[Dict]:
        payload = [self._to_payload_item(x) for x in batch]
        items_json = json.dumps(payload, ensure_ascii=False, indent=2)
        user_prompt = self.user_prompt_template.replace("{items_json}", items_json)
        if total_batches > 1:
            user_prompt += (
                f"\n\n（本批为第 {batch_no}/{total_batches} 批，共 {len(batch)} 条。"
                "请对本批每一条独立做语义判断；不合格的不写入 class 列表。）"
            )

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        if self.debug:
            print(f"[StrictV3] 批次 {batch_no}/{total_batches}，条目 {len(batch)}")

        last_err = None
        for attempt in range(1, self.batch_retries + 1):
            try:
                response = self.client.chat(
                    messages,
                    temperature=0.1,
                    max_tokens=4000,
                    timeout=self.batch_timeout,
                )
                parsed = self._parse_response(response)
                if parsed:
                    return parsed
                if attempt < self.batch_retries:
                    messages = messages + [
                        {"role": "assistant", "content": response or ""},
                        {
                            "role": "user",
                            "content": (
                                "请仅输出合法 JSON："
                                '{"class1":[{"id":1,"category":1,"title":"","reason":""}],'
                                '"class2":[],"class3":[]}，不要 markdown。'
                            ),
                        },
                    ]
                    print(f"[StrictV3] 批次 {batch_no} 解析失败，重试 {attempt + 1}/{self.batch_retries}")
            except Exception as e:
                last_err = e
                if attempt < self.batch_retries:
                    print(
                        f"[StrictV3] 批次 {batch_no} 请求失败 ({type(e).__name__})，"
                        f"重试 {attempt + 1}/{self.batch_retries}"
                    )
                    time.sleep(min(15, self.batch_interval * 2))
                else:
                    raise
        if last_err:
            raise last_err
        return None

    def classify(
        self,
        raw_items: List[Dict],
        reference_date: Optional[datetime] = None,
    ) -> StrictV3Result:
        result = StrictV3Result(total_input=len(raw_items))
        if not raw_items:
            result.success = True
            return result

        two_day_items = self._filter_two_days(raw_items, reference_date)
        result.total_after_date_filter = len(two_day_items)
        if not two_day_items:
            result.success = True
            return result

        candidates = []
        for item in two_day_items:
            title = item.get("title", "")
            summary = item.get("summary", "")
            if not self._is_hard_blocked(f"{title} {summary}"):
                candidates.append(item)

        result.total_after_hardblock = len(candidates)
        if not candidates:
            result.success = True
            return result

        if self.max_candidates > 0 and len(candidates) > self.max_candidates:
            candidates = candidates[: self.max_candidates]
            print(f"[StrictV3] 候选截断至 {self.max_candidates} 条（可在 strict_v3.max_candidates_per_day 调整）")

        batches = [
            candidates[i : i + self.batch_size]
            for i in range(0, len(candidates), self.batch_size)
        ]
        total_batches = len(batches)
        print(
            f"[StrictV3] 全量语义扫描：{len(candidates)} 条候选 → {total_batches} 批 "
            f"(每批≤{self.batch_size}，小模型可承载)"
        )

        raw_chunks: List[str] = []
        failed_batches = 0

        for idx, batch in enumerate(batches, start=1):
            try:
                parsed = self._classify_one_batch(batch, idx, total_batches)
                if parsed:
                    self._merge_parsed(result, parsed)
                    result.batches_processed += 1
                else:
                    failed_batches += 1
                    print(f"[StrictV3] 批次 {idx} 解析失败")
            except Exception as e:
                failed_batches += 1
                print(f"[StrictV3] 批次 {idx} 失败: {type(e).__name__}: {str(e)[:120]}")

            if idx < total_batches and self.batch_interval > 0:
                time.sleep(self.batch_interval)

        result.raw_response = "\n---\n".join(raw_chunks)
        result.success = result.batches_processed > 0
        if failed_batches and result.batches_processed:
            result.error = f"部分批次失败: {failed_batches}/{total_batches}"
        elif failed_batches:
            result.error = f"全部批次失败: {failed_batches}/{total_batches}"
            result.success = False

        print(
            f"[StrictV3] 扫描完成: 合格 Class1={len(result.class1)} "
            f"Class2={len(result.class2)} Class3={len(result.class3)} "
            f"(已处理批次 {result.batches_processed}/{total_batches})"
        )
        return result


def run_strict_v3_on_daily_json(
    raw_items: List[Dict],
    ai_config: Dict[str, Any],
    reference_date: Optional[datetime] = None,
    debug: bool = False,
    strict_v3_config: Optional[Dict[str, Any]] = None,
) -> StrictV3Result:
    cfg = strict_v3_config or {}
    classifier = StrictV3Classifier(
        ai_config,
        debug=debug,
        batch_size=cfg.get("BATCH_SIZE", 10),
        batch_interval=cfg.get("BATCH_INTERVAL", 8),
        max_candidates=cfg.get("MAX_CANDIDATES_PER_DAY", 0),
        batch_timeout=cfg.get("BATCH_TIMEOUT", 240),
        batch_retries=cfg.get("BATCH_RETRIES", 2),
    )
    return classifier.classify(raw_items, reference_date=reference_date)
