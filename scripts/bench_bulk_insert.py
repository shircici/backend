import random
import string
import time
import os

import requests


BASE_URL = os.getenv("API_BASE_URL", "http://replace_me_api_host:8000").rstrip("/") + "/api/sku/bulk-create/"
TOTAL = 100000
BATCH = 5000


def rand_code(n=16):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def make_item(i: int):
    return {
        "sku_code": f"SKU{int(time.time())}{i}{rand_code(6)}",
        "product_id": 1,
        "product_name": f"Product-{i}",
        "category_id": (i % 100) + 1,
        "price": "19.99",
        "stock": i % 1000,
        "status": 1,
    }


def main():
    start = time.time()
    for offset in range(0, TOTAL, BATCH):
        items = [make_item(i) for i in range(offset, offset + BATCH)]
        resp = requests.post(BASE_URL, json={"items": items}, timeout=120)
        resp.raise_for_status()
        print(f"batch {offset // BATCH + 1}: {resp.json()}")
    elapsed = time.time() - start
    print(f"inserted={TOTAL}, elapsed={elapsed:.2f}s")


if __name__ == "__main__":
    main()
