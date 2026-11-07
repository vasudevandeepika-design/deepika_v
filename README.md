# discount-rules-2

EC サイトのクーポン割引計算 API（Python）。カートの明細と適用クーポンコードを受け取り、最終金額を返します。

## API

`POST /carts/price` は、信頼済みのカート明細とクーポンコードを受け取り、クーポン・カート・明細単位の割引結果を返します。

確認済みのルールと実装上の判断は `docs/decisions.md` に記録しています。

## 必要な実行環境

Python が利用できます（`python --version` で確認）。外部依存は不要です（標準ライブラリのみ）。

## 起動

```sh
python main.py
```

`listening on :8080` と表示されれば起動しています。

## スコープ

カート明細はカートサービスから渡される信頼済みスナップショットです。在庫、クーポン利用回数・予算、有効期限、認証、支払い、返金、データベースは対象外です。migration と初期データはありません。

## テスト

```sh
python -m unittest
```

## 動作確認

サーバーを起動したまま、別のターミナルから次を実行します。

```sh
curl -s -w '\n%{http_code}\n' localhost:8080/carts/price \
  -H 'content-type: application/json' \
  -d '{"items":[{"line_id":"L1","sku":"TSHIRT-BLK-M","category":"APPAREL","unit_price":1000,"quantity":2},{"line_id":"L2","sku":"BOOK-0042","category":"BOOK","unit_price":1200,"quantity":1}],"coupons":["SAVE10","OFF500"]}'
```

HTTP 200 と整合した計算結果が返れば、サーバーは動作しています。

```
{"subtotal": 3200, "applied": [{"code": "SAVE10", "type": "PERCENTAGE", "amount": 120}], "rejected": [{"code": "OFF500", "reason": "NO_ELIGIBLE_ITEMS"}], "total_discount": 120, "total": 3080, "items": [...]}
200
```

## 提出物

- API 実装（このディレクトリ配下）
- 設計メモ `docs/decisions.md`（確認した受け入れ条件・迷った論点・置いた前提とその理由）
