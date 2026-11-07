import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer

from pricing.engine import Item, Request, quote


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/carts/price":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.send_error(400, "invalid request body")
            return

        req = Request(
            items=[
                Item(
                    line_id=it.get("line_id", ""),
                    sku=it.get("sku", ""),
                    category=it.get("category", ""),
                    unit_price=it.get("unit_price", 0),
                    quantity=it.get("quantity", 0),
                )
                for it in body.get("items", [])
            ],
            coupons=body.get("coupons", []),
        )
        resp = quote(req)

        payload = json.dumps(asdict(resp)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def main():
    addr = ("", 8080)
    print("listening on :8080")
    HTTPServer(addr, Handler).serve_forever()


if __name__ == "__main__":
    main()
