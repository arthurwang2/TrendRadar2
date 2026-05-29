# coding=utf-8
"""全量语义筛选结果导出：供 Cursor/简报只读「匹配项」小文件，而非整库 daily-json"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from trendradar.ai import AIFilterResult


def _flatten_ai_filter_items(ai_filter_result: AIFilterResult) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for group in ai_filter_result.tags or []:
        tag_name = group.get("tag", "")
        tag_desc = group.get("description", "")
        for it in group.get("items", []):
            items.append({
                "semantic_source": "ai_filter",
                "tag": tag_name,
                "tag_description": tag_desc,
                "relevance_score": it.get("relevance_score", 0),
                "title": it.get("title", ""),
                "url": it.get("url", ""),
                "source_name": it.get("source_name", ""),
                "source_type": it.get("source_type", ""),
            })
    return items


def _enrich_v3(
    strict_payload: Dict[str, Any],
    raw_rss_items: Optional[List[Dict]],
) -> Dict[str, List[Dict]]:
    by_id = {}
    if raw_rss_items:
        for row in raw_rss_items:
            rid = row.get("id")
            if rid is not None:
                by_id[int(rid)] = row

    def enrich(class_key: str) -> List[Dict]:
        out = []
        for x in strict_payload.get(class_key, []):
            if not isinstance(x, dict):
                continue
            rid = x.get("id")
            base = by_id.get(int(rid), {}) if rid is not None else {}
            out.append({
                "semantic_source": "strict_v3",
                "v3_category": x.get("category"),
                "v3_reason": x.get("reason", ""),
                "id": rid,
                "title": x.get("title") or base.get("title", ""),
                "published_at": x.get("published_at") or base.get("published_at", ""),
                "url": base.get("url", ""),
                "summary": (base.get("summary") or "")[:500],
                "feed_id": base.get("feed_id", ""),
            })
        return out

    return {
        "class1": enrich("class1"),
        "class2": enrich("class2"),
        "class3": enrich("class3"),
    }


def build_semantic_payload(
    date_str: str,
    ai_filter_result: Optional[AIFilterResult],
    filter_method: str,
    used_keyword_fallback: bool,
    raw_rss_items: Optional[List[Dict]],
    strict_v3_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    matched = []
    scan = {
        "date": date_str,
        "filter_method": filter_method,
        "used_keyword_fallback": used_keyword_fallback,
        "ai_filter_success": bool(ai_filter_result and ai_filter_result.success),
        "ai_filter_processed": getattr(ai_filter_result, "total_processed", 0) if ai_filter_result else 0,
        "ai_filter_matched": getattr(ai_filter_result, "total_matched", 0) if ai_filter_result else 0,
        "raw_rss_pool": len(raw_rss_items or []),
        "note": (
            "全量语义扫描在 GitHub Actions 内按批完成；本文件仅含匹配项，"
            "Cursor/简报应读本文件而非截断 daily-json 前几行。"
        ),
    }

    if ai_filter_result and ai_filter_result.success:
        matched = _flatten_ai_filter_items(ai_filter_result)

    v3_block = {}
    if strict_v3_payload:
        scan["v3_success"] = strict_v3_payload.get("success", False)
        scan["v3_input"] = strict_v3_payload.get("total_input", 0)
        scan["v3_after_hardblock"] = strict_v3_payload.get("total_after_hardblock", 0)
        scan["v3_batches"] = strict_v3_payload.get("batches_processed", 0)
        v3_block = _enrich_v3(strict_v3_payload, raw_rss_items)

    return {
        "date": date_str,
        "scan": scan,
        "matched_items": matched,
        "v3": v3_block,
        "matched_count": len(matched),
        "v3_count": sum(len(v3_block.get(k, [])) for k in ("class1", "class2", "class3")),
    }


def persist_semantic_filtered(
    date_str: str,
    ai_filter_result: Optional[AIFilterResult],
    filter_method: str,
    used_keyword_fallback: bool,
    raw_rss_items: Optional[List[Dict]],
    strict_v3_path: Optional[Path] = None,
    out_dir: Optional[Path] = None,
) -> Path:
    out_dir = out_dir or Path("output") / "meta"
    out_dir.mkdir(parents=True, exist_ok=True)

    strict_payload = None
    if strict_v3_path and strict_v3_path.exists():
        try:
            strict_payload = json.loads(strict_v3_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    payload = build_semantic_payload(
        date_str,
        ai_filter_result,
        filter_method,
        used_keyword_fallback,
        raw_rss_items,
        strict_payload,
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    latest = out_dir / "semantic_filtered_latest.json"
    dated = out_dir / f"semantic_filtered_{date_str}.json"
    latest.write_text(text, encoding="utf-8")
    dated.write_text(text, encoding="utf-8")
    print(
        f"[语义导出] 全量扫描统计已写入 {dated} "
        f"(AI匹配 {payload['matched_count']} 条, V3合计 {payload['v3_count']} 条)"
    )
    return dated
