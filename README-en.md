# discount-rules-2

A coupon discount calculation API (Python) for an e-commerce site. It takes the cart line items and applied coupon codes and returns the final amount.

## API

`POST /carts/price` accepts trusted cart lines and coupon codes and returns coupon, cart, and line-level discount results.

Confirmed rules and implementation decisions are recorded in `docs/decisions.md`.

## Requirements

Python is available (check with `python --version`). No external dependencies are required (standard library only).

## Run

```sh
python main.py
```

The server is up when it prints `listening on :8080`.

## Scope

Cart lines are trusted snapshots from the cart service. Inventory, coupon redemption counts and budgets, expiry, authentication, payments, refunds, and databases are out of scope. No migrations or seed data are required.

## Test

```sh
python -m unittest
```

## Check

With the server running, run this from another terminal.

```sh
curl -s -w '\n%{http_code}\n' localhost:8080/carts/price \
  -H 'content-type: application/json' \
  -d '{"items":[{"line_id":"L1","sku":"TSHIRT-BLK-M","category":"APPAREL","unit_price":1000,"quantity":2},{"line_id":"L2","sku":"BOOK-0042","category":"BOOK","unit_price":1200,"quantity":1}],"coupons":["SAVE10","OFF500"]}'
```

The server is working if it returns HTTP 200 with a reconciled pricing result.

```
{"subtotal": 3200, "applied": [{"code": "SAVE10", "type": "PERCENTAGE", "amount": 120}], "rejected": [{"code": "OFF500", "reason": "NO_ELIGIBLE_ITEMS"}], "total_discount": 120, "total": 3080, "items": [...]}
200
```

## Deliverables

- The API implementation (under this directory)
- Design notes `docs/decisions.md` (confirmed acceptance criteria, scope, assumptions, and rationale)
