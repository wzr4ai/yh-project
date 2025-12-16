import json
import textwrap
from typing import Dict, List, Tuple, Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import schemas
from app.models.entities import Product, ProductAlias
from app.services import logic
from app.services.llm import LLMService, LLMServiceError


async def build_product_context(session: AsyncSession) -> Tuple[str, Dict[str, Any]]:
    """Build a compact JSON context of products and aliases for prompting."""
    products = (await session.execute(sa.select(Product))).scalars().all()
    alias_rows = (await session.execute(sa.select(ProductAlias.product_id, ProductAlias.alias_name))).all()
    alias_map: Dict[str, List[str]] = {}
    for pid, alias_name in alias_rows:
        alias_map.setdefault(pid, []).append(alias_name)

    context_items: list[dict[str, Any]] = []
    product_lookup: Dict[str, Any] = {}
    for prod in products:
        price_info = await logic.calculate_price_for_product(session, prod)
        context_items.append(
            {
                "id": prod.id,
                "name": prod.name,
                "spec": prod.spec,
                "standard_price": price_info.price,
                "aliases": alias_map.get(prod.id, []),
            }
        )
        product_lookup[prod.id] = {
            "name": prod.name,
            "spec": prod.spec,
            "standard_price": price_info.price,
        }

    context_str = json.dumps(context_items, ensure_ascii=False)
    return context_str, product_lookup


async def analyze_order_text(text: str, context: str, protocol: str | None = None) -> schemas.LLMChatResponse:
    """Call LLM to map raw order text to structured items."""
    system_prompt = textwrap.dedent(
        """
        你是一个订单预处理助手，根据门店商品清单把“脏”的订单文本整理成结构化 JSON。
        请严格输出 JSON，不要包含多余说明。
        规则：
        - 使用给定的商品上下文进行匹配，名称或别名模糊匹配，并比较规格(spec)与标准单价(standard_price)。
        - 当规格和标准单价都匹配且名称近似时，可将 confidence 提升为 high。
        - 为每个出现的商品输出：raw_name, suggested_product_id, suggested_product_name, quantity, detected_price(若能识别), confidence(high/low/new), candidates(最多3个，包含 product_id、product_name、score)。
        - 当不确定或上下文不存在时，confidence 设置为 new，product_id 置空。
        - 只返回 JSON 对象：{"items":[...]}
        """
    ).strip()
    user_prompt = f"商品上下文：{context}\n\n原始订单文本：{text}\n\n请输出 JSON："

    service = LLMService()
    return await service.chat(
        messages=[
            schemas.LLMMessage(role="system", content=system_prompt),
            schemas.LLMMessage(role="user", content=user_prompt),
        ],
        protocol=protocol,
        model_tier="low",
        temperature=0.2,
        max_output_tokens=16384,
        response_mime_type="application/json",
    )


async def parse_and_validate(
    raw_content: str, product_lookup: Dict[str, Any]
) -> schemas.OrderAnalyzeResponse:
    """Ensure LLM JSON is clean and product IDs exist."""
    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError:
        raise ValueError("LLM response is not valid JSON")

    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("LLM response JSON missing items list")

    product_ids = set(product_lookup.keys())
    cleaned: list[schemas.OrderAnalyzeItem] = []

    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        raw_name = str(raw_item.get("raw_name") or "").strip()
        if not raw_name:
            continue
        quantity = raw_item.get("quantity")
        try:
            quantity_val = int(quantity) if quantity is not None else 1
        except Exception:
            quantity_val = 1
        quantity_val = max(1, quantity_val)

        suggested_id = raw_item.get("suggested_product_id")
        suggested_name = raw_item.get("suggested_product_name")
        confidence = str(raw_item.get("confidence") or "low").lower()
        if confidence not in {"high", "low", "new"}:
            confidence = "low"

        if suggested_id and suggested_id not in product_ids:
            suggested_id = None
            confidence = "low"

        if suggested_id and not suggested_name:
            suggested_name = (product_lookup.get(suggested_id) or {}).get("name")

        detected_price = raw_item.get("detected_price") or raw_item.get("unit_price")
        try:
            detected_price_val = float(detected_price) if detected_price is not None else None
        except Exception:
            detected_price_val = None

        candidates_input = raw_item.get("candidates") or []
        candidates: list[schemas.OrderAnalyzeCandidate] = []
        if isinstance(candidates_input, list):
            for cand in candidates_input[:3]:
                if not isinstance(cand, dict):
                    continue
                pid = cand.get("product_id")
                pname = cand.get("product_name")
                score_raw = cand.get("score")
                try:
                    score = float(score_raw) if score_raw is not None else None
                except Exception:
                    score = None
                if pid and pid not in product_ids:
                    pid = None
                if pid and not pname:
                    pname = product_lookup.get(pid)
                candidates.append(
                    schemas.OrderAnalyzeCandidate(product_id=pid, product_name=pname, score=score)
                )

        cleaned.append(
            schemas.OrderAnalyzeItem(
                raw_name=raw_name,
                suggested_product_id=suggested_id,
                suggested_product_name=suggested_name,
                quantity=quantity_val,
                confidence=confidence,  # type: ignore[arg-type]
                candidates=candidates,
                detected_price=detected_price_val,
            )
        )

    return schemas.OrderAnalyzeResponse(items=cleaned)
