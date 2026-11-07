# Coupon Pricing Decisions

## Confirmed scope

`POST /carts/price` receives cart lines that are a trusted snapshot from the cart service. The API does not look up or reserve inventory and does not manage coupon redemption counts, campaign budgets, expiry, authentication, payments, refunds, or databases.

All monetary values are integer yen. A line's original amount is `unit_price * quantity`.

## Coupon catalog

| Code | Eligible items | Discount | Minimum eligible subtotal | Cap | Combinable |
| --- | --- | --- | ---: | ---: | --- |
| `VIP30` | All items | 30% | None | 3000 | No |
| `SAVE10` | `BOOK` | 10% | None | None | Yes |
| `SAVE20` | `APPAREL` | 20% | 5000 | 1000 | Yes |
| `OFF500` | `GIFT-BOX` | 500 | 3000 | 500 | Yes |
| `OFF1000` | `HOME` | 1000 | 8000 | 1000 | Yes |

Minimums and percentage bases use the coupon's eligible pre-discount subtotal, not the cart subtotal.

## Eligibility and selection

- Only the first occurrence of a code is considered. Later occurrences are rejected as `DUPLICATE`.
- Other eligibility failures are `UNKNOWN_CODE`, `NO_ELIGIBLE_ITEMS`, and `MINIMUM_NOT_MET`.
- Usable coupons are ordered `VIP30`, `SAVE10`, `SAVE20`, `OFF500`, `OFF1000`, independent of request order.
- A usable `VIP30` is selected alone; other usable coupons are rejected as `NOT_COMBINABLE`.
- Without `VIP30`, the first three usable coupons are selected; later usable coupons are rejected as `LIMIT_EXCEEDED`.
- The engine does not search for the combination with the highest discount.

Rejected coupon occurrences are returned in request order. Applied coupons are returned in calculation order.

## Calculation and allocation

Percentage coupons are calculated before fixed coupons. A percentage discount is floored to integer yen before its cap is applied. Every coupon is also capped by the amount currently remaining on its eligible lines. A selected coupon remains in `applied` when its resulting amount is zero.

Each coupon is allocated proportionally over the remaining amounts of eligible lines. Per-line fractions are floored, and leftover yen are assigned by SKU (product code), with original cart order breaking ties for identical SKUs. An allocation never exceeds a line's remaining amount.

The implementation checks these invariants:

- every line has `payable = amount - discount`;
- no line payable is negative;
- sum of line discounts equals sum of applied-coupon amounts;
- cart `total_discount` equals both sums;
- cart `total = subtotal - total_discount`.

## API decisions

The response includes the original cart-level fields and an `items` array so allocation and reconciliation are explainable. Invalid negative prices or quantities are request errors; valid but unusable coupons are returned in `rejected`, not raised as errors.

The implementation uses only the Python standard library and keeps pricing logic pure in `pricing/engine.py`.