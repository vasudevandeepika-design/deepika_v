"""Pricing engine for the coupon discount API."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Item:
    """A single cart line using trusted catalog price and category data."""

    line_id: str
    sku: str
    category: str
    unit_price: int
    quantity: int


@dataclass(frozen=True)
class Request:
    """Input to the pricing API."""

    items: list[Item]
    coupons: list[str]


@dataclass(frozen=True)
class Applied:
    """A coupon that was selected, including zero-value applications."""

    code: str
    type: str
    amount: int


@dataclass(frozen=True)
class Rejected:
    """A coupon occurrence that was not applied, with a stable reason code."""

    code: str
    reason: str


@dataclass(frozen=True)
class LineResult:
    """Reconciled pricing result for one cart line."""

    line_id: str
    sku: str
    category: str
    unit_price: int
    quantity: int
    amount: int
    discount: int
    payable: int


@dataclass(frozen=True)
class Response:
    """Result of pricing a cart."""

    subtotal: int
    applied: list[Applied]
    rejected: list[Rejected]
    total_discount: int
    total: int
    items: list[LineResult] = field(default_factory=list)


@dataclass(frozen=True)
class _Coupon:
    code: str
    category: Optional[str]
    percent: Optional[int] = None
    fixed: Optional[int] = None
    minimum: int = 0
    cap: Optional[int] = None
    combinable: bool = True


_COUPONS = {
    coupon.code: coupon
    for coupon in (
        _Coupon("VIP30", None, percent=30, cap=3000, combinable=False),
        _Coupon("SAVE10", "BOOK", percent=10),
        _Coupon("SAVE20", "APPAREL", percent=20, minimum=5000, cap=1000),
        _Coupon("OFF500", "GIFT-BOX", fixed=500, minimum=3000),
        _Coupon("OFF1000", "HOME", fixed=1000, minimum=8000),
    )
}
_SELECTION_ORDER = tuple(_COUPONS)


def _eligible_indexes(coupon: _Coupon, items: list[Item]) -> list[int]:
    return [
        index
        for index, item in enumerate(items)
        if coupon.category is None or item.category == coupon.category
    ]


def _allocate(
    discount: int,
    indexes: list[int],
    items: list[Item],
    remaining: list[int],
) -> list[int]:
    allocations = [0] * len(items)
    eligible_total = sum(remaining[index] for index in indexes)
    if discount <= 0 or eligible_total <= 0:
        return allocations

    for index in indexes:
        allocations[index] = discount * remaining[index] // eligible_total

    leftover = discount - sum(allocations)
    ordered = sorted(indexes, key=lambda index: (items[index].sku, index))
    while leftover:
        progressed = False
        for index in ordered:
            if allocations[index] < remaining[index]:
                allocations[index] += 1
                leftover -= 1
                progressed = True
                if not leftover:
                    break
        if not progressed:
            raise AssertionError("discount allocation exceeded eligible amount")
    return allocations


def quote(req: Request) -> Response:
    """Price a cart according to the registered coupon rules."""

    for item in req.items:
        if item.unit_price < 0 or item.quantity < 0:
            raise ValueError("unit_price and quantity must be non-negative")

    amounts = [item.unit_price * item.quantity for item in req.items]
    remaining = amounts.copy()
    occurrence_rejections: dict[int, str] = {}
    first_indexes: dict[str, int] = {}
    usable: set[str] = set()

    for request_index, code in enumerate(req.coupons):
        if code in first_indexes:
            occurrence_rejections[request_index] = "DUPLICATE"
            continue
        first_indexes[code] = request_index
        coupon = _COUPONS.get(code)
        if coupon is None:
            occurrence_rejections[request_index] = "UNKNOWN_CODE"
            continue
        indexes = _eligible_indexes(coupon, req.items)
        eligible_subtotal = sum(amounts[index] for index in indexes)
        if eligible_subtotal == 0:
            occurrence_rejections[request_index] = "NO_ELIGIBLE_ITEMS"
        elif eligible_subtotal < coupon.minimum:
            occurrence_rejections[request_index] = "MINIMUM_NOT_MET"
        else:
            usable.add(code)

    selected: list[str] = []
    if "VIP30" in usable:
        selected.append("VIP30")
        for code in usable - {"VIP30"}:
            occurrence_rejections[first_indexes[code]] = "NOT_COMBINABLE"
    else:
        ordered_usable = [code for code in _SELECTION_ORDER if code in usable]
        selected = ordered_usable[:3]
        for code in ordered_usable[3:]:
            occurrence_rejections[first_indexes[code]] = "LIMIT_EXCEEDED"

    line_discounts = [0] * len(req.items)
    applied: list[Applied] = []
    for code in selected:
        coupon = _COUPONS[code]
        indexes = _eligible_indexes(coupon, req.items)
        pre_discount_subtotal = sum(amounts[index] for index in indexes)
        available = sum(remaining[index] for index in indexes)
        if coupon.percent is not None:
            discount = pre_discount_subtotal * coupon.percent // 100
            coupon_type = "PERCENTAGE"
        else:
            discount = coupon.fixed or 0
            coupon_type = "FIXED"
        if coupon.cap is not None:
            discount = min(discount, coupon.cap)
        discount = min(discount, available)

        allocations = _allocate(discount, indexes, req.items, remaining)
        for index, allocation in enumerate(allocations):
            remaining[index] -= allocation
            line_discounts[index] += allocation
        applied.append(Applied(code=code, type=coupon_type, amount=discount))

    rejected = [
        Rejected(code=code, reason=occurrence_rejections[index])
        for index, code in enumerate(req.coupons)
        if index in occurrence_rejections
    ]
    line_results = [
        LineResult(
            line_id=item.line_id,
            sku=item.sku,
            category=item.category,
            unit_price=item.unit_price,
            quantity=item.quantity,
            amount=amounts[index],
            discount=line_discounts[index],
            payable=remaining[index],
        )
        for index, item in enumerate(req.items)
    ]
    subtotal = sum(amounts)
    total_discount = sum(line_discounts)
    assert total_discount == sum(coupon.amount for coupon in applied)
    assert total_discount == sum(item.discount for item in line_results)
    return Response(
        subtotal=subtotal,
        applied=applied,
        rejected=rejected,
        total_discount=total_discount,
        total=subtotal - total_discount,
        items=line_results,
    )
