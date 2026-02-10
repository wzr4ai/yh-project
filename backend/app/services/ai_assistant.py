import json
import textwrap
from typing import Any, Dict, List, Tuple

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import schemas
from app.models.entities import Product, ProductAlias
from app.services import logic
from app.services.llm import LLMService, ModelTier, Protocol


ALLOWED_ACTIONS = {"list_products_costs", "update_retail_price", "generate_bundles"}


async def _fetch_product_brief(session: AsyncSession, limit: int = 200) -> list[dict[str, Any]]:
    stmt = sa.select(Product).order_by(Product.updated_at.desc()).limit(max(1, limit))
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "spec": p.spec or "",
            "base_cost_price": float(p.base_cost_price or 0),
            "box_cost_price": float(p.box_cost_price or 0),
            "units_per_box": int(p.units_per_box or 1),
        }
        for p in rows
    ]


async def _list_all_products_costs(session: AsyncSession, page_size: int = 200) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    offset = 0
    total = 0
    while True:
        page, total, _ = await logic.list_products_with_inventory(
            session,
            offset=offset,
            limit=page_size,
        )
        if not page:
            break
        for item in page:
            items.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "spec": item.spec,
                    "base_cost_price": float(item.base_cost_price or 0),
                    "box_cost_price": float(item.box_cost_price or 0),
                    "units_per_box": int(item.units_per_box or 1),
                    "standard_price": float(item.standard_price or 0),
                    "stock": int(item.stock or 0),
                }
            )
        offset += page_size
        if offset >= total:
            break
    return {"total": total, "items": items}


async def _find_products_by_name(session: AsyncSession, name: str, limit: int = 5) -> list[Product]:
    term = (name or "").strip()
    if not term:
        return []
    exact = (
        await session.execute(sa.select(Product).where(Product.name == term))
    ).scalars().all()
    if exact:
        return exact
    alias_exact = (
        await session.execute(
            sa.select(Product)
            .join(ProductAlias, ProductAlias.product_id == Product.id)
            .where(ProductAlias.alias_name == term)
        )
    ).scalars().all()
    if alias_exact:
        return alias_exact

    like = f"%{term}%"
    fuzzy = (
        await session.execute(
            sa.select(Product).where(Product.name.ilike(like)).limit(limit)
        )
    ).scalars().all()
    if fuzzy:
        return fuzzy
    alias_fuzzy = (
        await session.execute(
            sa.select(Product)
            .join(ProductAlias, ProductAlias.product_id == Product.id)
            .where(ProductAlias.alias_name.ilike(like))
            .limit(limit)
        )
    ).scalars().all()
    return alias_fuzzy


async def _resolve_price_updates(
    session: AsyncSession, items: list[dict[str, Any]]
) -> Tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        new_price = item.get("new_price")
        try:
            price_val = float(new_price) if new_price is not None else None
        except Exception:
            price_val = None
        product_id = item.get("product_id")
        product_name = item.get("product_name") or item.get("name") or ""

        product = None
        if product_id:
            product = await session.get(Product, product_id)
        elif product_name:
            matches = await _find_products_by_name(session, product_name)
            if len(matches) == 1:
                product = matches[0]
            else:
                unresolved.append(
                    {
                        "query": product_name,
                        "candidates": [
                            {"id": p.id, "name": p.name, "spec": p.spec or ""}
                            for p in matches
                        ],
                    }
                )
                continue

        if not product:
            unresolved.append({"query": product_id or product_name, "candidates": []})
            continue

        resolved.append(
            {
                "product_id": product.id,
                "product_name": product.name,
                "spec": product.spec or "",
                "new_price": price_val,
                "current_fixed_price": product.fixed_retail_price,
            }
        )
    return resolved, unresolved


async def _generate_bundles_with_llm(
    session: AsyncSession,
    *,
    count: int = 5,
    protocol: Protocol | None = None,
    model_tier: ModelTier = "mid",
    model: str | None = None,
) -> dict[str, Any]:
    data = await _list_all_products_costs(session)
    items = sorted(data["items"], key=lambda x: x.get("stock", 0), reverse=True)
    items = [item for item in items if item.get("stock", 0) > 0][:120]
    product_context = json.dumps(
        [
            {
                "id": item["id"],
                "name": item["name"],
                "spec": item.get("spec") or "",
                "standard_price": item.get("standard_price") or 0,
                "base_cost_price": item.get("base_cost_price") or 0,
                "box_cost_price": item.get("box_cost_price") or 0,
                "units_per_box": item.get("units_per_box") or 1,
                "stock": item.get("stock") or 0,
            }
            for item in items
        ],
        ensure_ascii=False,
    )

    system_prompt = textwrap.dedent(
        """
        你是烟花爆竹门店的套餐设计助手，需要基于给定商品列表生成套餐方案。
        目标：提升客单价、加快动销、兼顾库存。
        规则：
        - 只能使用提供列表中的商品，必须给出 product_id。
        - 每个套餐包含 2-4 个商品，数量为整数。
        - 给出套餐建议售价（bundle_price）和推荐理由（reason）。
        - 注意对比单件成本(base_cost_price)、箱成本(box_cost_price)和每箱件数(units_per_box)。
        - 尽量覆盖不同价位（低/中/高）。
        输出严格 JSON，格式：
        {"bundles":[{"title":"", "items":[{"product_id":"","name":"","qty":1}], "bundle_price":0, "reason":""}]}
        """
    ).strip()

    user_prompt = f"商品列表 JSON：{product_context}\n\n请生成 {max(1, count)} 个套餐："

    service = LLMService()
    response = await service.chat(
        messages=[
            schemas.LLMMessage(role="system", content=system_prompt),
            schemas.LLMMessage(role="user", content=user_prompt),
        ],
        protocol=protocol or "gemini",
        model_tier=model_tier,
        model=model,
        temperature=0.5,
        max_output_tokens=2048,
        response_mime_type="application/json",
    )

    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        raise ValueError("套餐生成失败，模型未返回有效 JSON")

    bundles = data.get("bundles") if isinstance(data, dict) else []
    if not isinstance(bundles, list):
        bundles = []

    price_lookup = {item["id"]: item for item in items}
    cleaned: list[dict[str, Any]] = []
    for bundle in bundles[: max(1, count)]:
        if not isinstance(bundle, dict):
            continue
        raw_items = bundle.get("items") or []
        if not isinstance(raw_items, list):
            continue
        bundle_items = []
        cost_total = 0.0
        standard_total = 0.0
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            pid = raw.get("product_id")
            if not pid or pid not in price_lookup:
                continue
            qty = raw.get("qty") or 1
            try:
                qty_val = int(qty)
            except Exception:
                qty_val = 1
            qty_val = max(1, qty_val)
            product = price_lookup[pid]
            bundle_items.append(
                {
                    "product_id": pid,
                    "name": product["name"],
                    "spec": product.get("spec") or "",
                    "qty": qty_val,
                    "standard_price": product.get("standard_price") or 0,
                    "base_cost_price": product.get("base_cost_price") or 0,
                }
            )
            cost_total += float(product.get("base_cost_price") or 0) * qty_val
            standard_total += float(product.get("standard_price") or 0) * qty_val
        if not bundle_items:
            continue
        bundle_price = bundle.get("bundle_price")
        try:
            price_val = float(bundle_price) if bundle_price is not None else None
        except Exception:
            price_val = None
        if price_val is None or price_val <= 0:
            price_val = max(standard_total * 0.9, cost_total)
        margin = 0.0 if price_val <= 0 else max(0.0, (price_val - cost_total) / price_val)
        cleaned.append(
            {
                "title": bundle.get("title") or "套餐",
                "items": bundle_items,
                "bundle_price": round(price_val, 2),
                "cost_total": round(cost_total, 2),
                "margin_pct": round(margin * 100, 1),
                "reason": bundle.get("reason") or "",
            }
        )

    return {"bundles": cleaned}


async def chat_with_ai(
    session: AsyncSession,
    payload: schemas.AIChatRequest,
) -> schemas.AIChatResponse:
    messages = payload.messages or []
    if not messages:
        return schemas.AIChatResponse(reply="请先描述你的问题。")

    product_brief = await _fetch_product_brief(session, limit=200)
    context = json.dumps(product_brief, ensure_ascii=False)
    system_prompt = textwrap.dedent(
        """
        你是烟花爆竹门店的 AI 助理，仅对老板可用。你可以发起以下动作：
        1) list_products_costs: 查询商品进价/成本清单（只读）。
        2) update_retail_price: 调整商品零售价（需人工确认）。
        3) generate_bundles: 生成智能套餐方案（只读）。

        规则：
        - 严格输出 JSON，格式：{"reply":"...", "actions":[...]}。
        - 如需动作，请填 actions；不需要动作则 actions 为空数组。
        - update_retail_price 的 payload 格式：
          {"items":[{"product_id":"","product_name":"","new_price":0}]}
          如果无法唯一匹配，请在 reply 中提醒用户补充商品名称或编号。
        - 不要臆造商品或价格。
        """
    ).strip()

    user_prompt = f"商品简表 JSON：{context}\n\n请基于对话给出回复与动作。"

    protocol_val: Protocol | None = None
    if payload.protocol in {"gemini", "openai", "open"}:
        protocol_val = payload.protocol  # type: ignore[assignment]
    model_tier: ModelTier = payload.model_tier

    service = LLMService()
    response = await service.chat(
        messages=[
            schemas.LLMMessage(role="system", content=system_prompt),
            *messages,
            schemas.LLMMessage(role="user", content=user_prompt),
        ],
        protocol=protocol_val,
        model_tier=model_tier,
        model=payload.model,
        temperature=payload.temperature,
        max_output_tokens=payload.max_output_tokens,
        response_mime_type="application/json",
    )

    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        return schemas.AIChatResponse(reply=response.content or "抱歉，未能理解你的请求。")

    reply = data.get("reply") if isinstance(data, dict) else None
    reply_text = reply if isinstance(reply, str) and reply else "好的。"
    raw_actions = data.get("actions") if isinstance(data, dict) else []
    actions: list[schemas.AIAction] = []

    if isinstance(raw_actions, list):
        for raw in raw_actions:
            if not isinstance(raw, dict):
                continue
            action_type = raw.get("type")
            if action_type not in ALLOWED_ACTIONS:
                continue
            title = raw.get("title") or action_type
            payload_data = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
            requires_confirmation = bool(raw.get("requires_confirmation"))

            action = schemas.AIAction(
                type=action_type,
                title=title,
                payload=payload_data,
                requires_confirmation=requires_confirmation,
            )

            if action_type == "list_products_costs":
                action.result = await _list_all_products_costs(session)
                action.requires_confirmation = False
            elif action_type == "generate_bundles":
                count = int(payload_data.get("count") or 5)
                action.result = await _generate_bundles_with_llm(
                    session,
                    count=max(1, min(8, count)),
                    protocol=protocol_val,
                    model_tier=model_tier,
                    model=payload.model,
                )
                action.requires_confirmation = False
            elif action_type == "update_retail_price":
                items = payload_data.get("items") or []
                if not isinstance(items, list):
                    items = []
                resolved, unresolved = await _resolve_price_updates(session, items)
                if unresolved:
                    reply_text = (
                        "需要确认商品：\n"
                        + "\n".join(
                            [
                                f"- {u['query']}（候选数 {len(u.get('candidates') or [])}）"
                                for u in unresolved
                            ]
                        )
                        + "\n请回复更精确的商品名称或编号。"
                    )
                    continue
                preview_items = []
                for item in resolved:
                    product = await session.get(Product, item["product_id"])
                    price_info = None
                    if product:
                        price_info = await logic.calculate_price_for_product(session, product)
                    preview_items.append(
                        {
                            "product_id": item["product_id"],
                            "name": item["product_name"],
                            "spec": item["spec"],
                            "new_price": item["new_price"],
                            "current_fixed_price": item["current_fixed_price"],
                            "standard_price": price_info.price if price_info else None,
                        }
                    )
                action.payload = {"items": [{"product_id": i["product_id"], "new_price": i["new_price"]} for i in resolved]}
                action.preview = {"items": preview_items}
                action.requires_confirmation = True

            actions.append(action)

    return schemas.AIChatResponse(reply=reply_text, actions=actions)


async def execute_action(
    session: AsyncSession, payload: schemas.AIActionRequest
) -> schemas.AIActionResponse:
    action_type = payload.type
    data = payload.payload or {}

    if action_type == "update_retail_price":
        items = data.get("items") or []
        if not isinstance(items, list) or not items:
            return schemas.AIActionResponse(reply="未找到要调整的商品。")
        updated = []
        for item in items:
            if not isinstance(item, dict):
                continue
            product_id = item.get("product_id")
            new_price = item.get("new_price")
            if not product_id:
                continue
            try:
                price_val = float(new_price) if new_price is not None else None
            except Exception:
                price_val = None
            product = await logic.update_product_retail_price(session, product_id, price_val)
            price_info = await logic.calculate_price_for_product(session, product)
            updated.append(
                {
                    "product_id": product.id,
                    "name": product.name,
                    "spec": product.spec or "",
                    "fixed_retail_price": product.fixed_retail_price,
                    "standard_price": price_info.price,
                }
            )
        await session.commit()
        return schemas.AIActionResponse(reply="已更新零售价。", result={"items": updated})

    raise ValueError("unsupported action")
