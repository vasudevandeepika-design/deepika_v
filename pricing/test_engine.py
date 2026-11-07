import unittest

from pricing.engine import Item, Request, quote


def item(line_id, sku, category, amount):
    return Item(line_id, sku, category, amount, 1)


class TestQuote(unittest.TestCase):
    def test_vip_is_exclusive_and_capped(self):
        response = quote(Request(
            [item("1", "B", "BOOK", 12000)],
            ["SAVE10", "VIP30"],
        ))

        self.assertEqual([("VIP30", 3000)], [(it.code, it.amount) for it in response.applied])
        self.assertEqual([("SAVE10", "NOT_COMBINABLE")], [(it.code, it.reason) for it in response.rejected])

    def test_invalid_duplicate_and_minimum_reasons(self):
        response = quote(Request(
            [item("1", "BOOK-1", "BOOK", 1000), item("2", "A", "APPAREL", 4999)],
            ["BAD", "SAVE10", "SAVE10", "SAVE20", "OFF500"],
        ))

        self.assertEqual(
            [("BAD", "UNKNOWN_CODE"), ("SAVE10", "DUPLICATE"),
             ("SAVE20", "MINIMUM_NOT_MET"), ("OFF500", "NO_ELIGIBLE_ITEMS")],
            [(it.code, it.reason) for it in response.rejected],
        )

    def test_selection_is_fixed_and_limited_to_three(self):
        items = [
            item("1", "BOOK", "BOOK", 1000),
            item("2", "SHIRT", "APPAREL", 5000),
            item("3", "GIFT", "GIFT-BOX", 3000),
            item("4", "HOME", "HOME", 8000),
        ]
        response = quote(Request(items, ["OFF1000", "OFF500", "SAVE20", "SAVE10"]))

        self.assertEqual(["SAVE10", "SAVE20", "OFF500"], [it.code for it in response.applied])
        self.assertEqual([("OFF1000", "LIMIT_EXCEEDED")], [(it.code, it.reason) for it in response.rejected])

    def test_percentage_then_fixed_and_reconciliation(self):
        response = quote(Request(
            [item("1", "BOOK", "BOOK", 1000), item("2", "BOOK", "BOOK", 1000)],
            ["SAVE10"],
        ))

        self.assertEqual([100, 100], [it.discount for it in response.items])
        self.assertEqual(200, response.total_discount)
        self.assertEqual(response.total_discount, sum(it.amount for it in response.applied))
        self.assertEqual(response.total_discount, sum(it.discount for it in response.items))
        self.assertEqual(response.subtotal, response.total + response.total_discount)

    def test_fractional_allocation_uses_sku_then_cart_order(self):
        response = quote(Request(
            [item("first-z", "Z", "BOOK", 1), item("first-a", "A", "BOOK", 4),
             item("second-a", "A", "BOOK", 5)],
            ["SAVE10"],
        ))

        self.assertEqual([0, 1, 0], [it.discount for it in response.items])

    def test_zero_quantity_has_no_eligible_items(self):
        response = quote(Request([Item("1", "B", "BOOK", 100, 0)], ["SAVE10"]))
        self.assertEqual("NO_ELIGIBLE_ITEMS", response.rejected[0].reason)

    def test_percentage_minimum_and_cap_boundary(self):
        response = quote(Request(
            [item("1", "SHIRT", "APPAREL", 5000)],
            ["SAVE20"],
        ))

        self.assertEqual(1000, response.applied[0].amount)
        self.assertEqual(4000, response.items[0].payable)

    def test_fixed_coupons_apply_to_their_categories(self):
        response = quote(Request(
            [item("1", "GIFT", "GIFT-BOX", 3000), item("2", "HOME", "HOME", 8000)],
            ["OFF1000", "OFF500"],
        ))

        self.assertEqual(
            [("OFF500", 500), ("OFF1000", 1000)],
            [(coupon.code, coupon.amount) for coupon in response.applied],
        )
        self.assertEqual([500, 1000], [line.discount for line in response.items])

    def test_coupon_request_order_does_not_change_selection(self):
        items = [
            item("1", "BOOK", "BOOK", 1000),
            item("2", "SHIRT", "APPAREL", 5000),
            item("3", "GIFT", "GIFT-BOX", 3000),
            item("4", "HOME", "HOME", 8000),
        ]

        first = quote(Request(items, ["OFF1000", "SAVE10", "OFF500", "SAVE20"]))
        second = quote(Request(items, ["SAVE20", "OFF500", "SAVE10", "OFF1000"]))

        self.assertEqual(first.applied, second.applied)
        self.assertEqual([line.discount for line in first.items], [line.discount for line in second.items])

    def test_negative_values_are_rejected(self):
        with self.assertRaises(ValueError):
            quote(Request([Item("1", "B", "BOOK", -1, 1)], []))


if __name__ == "__main__":
    unittest.main()
