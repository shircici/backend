import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings_test")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.db import connection  # noqa: E402
from django.core.management import call_command  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402


SHEET_PATH = ROOT / "docs" / "前端联调表.csv"
REPORT_PATH = ROOT / "docs" / "前端联调测试报告.json"


@dataclass
class ApiCase:
    module: str
    name: str
    method: str
    path: str


def _normalize_path(path: str) -> str:
    # 把联调表中的占位符替换为可执行路径
    rep = {
        r"\{platform\}": "tiktok",
        r"\{goods_id\}": "1",
        r"\{order_id\}": "1",
        r"\{waybill\}": "WB001",
        r"\{task_id\}": "1",
        r"\{dead_letter_id\}": "1",
        r"\{sku_code\}": "SKU001",
        r"\{id\}": "1",
        r"\{batch_id\}": "batch001",
        r"\{job_id\}": "1",
        r"\{creator_id\}": "1",
        r"\{asset_id\}": "1",
    }
    out = path
    for patt, value in rep.items():
        out = re.sub(patt, value, out)
    if not out.startswith("/"):
        out = "/" + out
    return out


def load_cases() -> List[ApiCase]:
    rows: List[ApiCase] = []
    with SHEET_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            methods = [m.strip().upper() for m in row["方法"].split(",") if m.strip()]
            for method in methods:
                path = _normalize_path(row["路径"].strip())
                if not path.startswith("/api/"):
                    continue
                rows.append(
                    ApiCase(
                        module=row["模块"].strip(),
                        name=row["接口名称"].strip(),
                        method=method,
                        path=path,
                    )
                )
    return rows


def _request(client: APIClient, method: str, path: str):
    payload = {"smoke_test": True}
    if method == "GET":
        return client.get(path)
    if method == "POST":
        return client.post(path, payload, format="json")
    if method == "PUT":
        return client.put(path, payload, format="json")
    if method == "PATCH":
        return client.patch(path, payload, format="json")
    if method == "DELETE":
        return client.delete(path)
    return client.generic(method, path)


def main():
    # settings_test 使用内存库，脚本启动后需先迁移
    call_command("migrate", interactive=False, verbosity=0)

    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(
        username="api_smoke_user",
        defaults={"is_staff": True, "is_superuser": True, "email": "smoke@example.com"},
    )
    client = APIClient()
    client.force_authenticate(user=user)

    cases = load_cases()
    results = []
    ok_count = 0
    err5xx_count = 0
    exc_count = 0
    db_vendor = connection.vendor

    for c in cases:
        try:
            resp = _request(client, c.method, c.path)
            status = int(resp.status_code)
            callable_ok = status < 500
            if callable_ok:
                ok_count += 1
            else:
                err5xx_count += 1
            results.append(
                {
                    "module": c.module,
                    "name": c.name,
                    "method": c.method,
                    "path": c.path,
                    "status_code": status,
                    "callable": callable_ok,
                }
            )
        except Exception as ex:  # noqa: BLE001
            exc_count += 1
            results.append(
                {
                    "module": c.module,
                    "name": c.name,
                    "method": c.method,
                    "path": c.path,
                    "status_code": None,
                    "callable": False,
                    "exception": str(ex),
                }
            )

    summary = {
        "database_vendor": db_vendor,
        "total_cases": len(cases),
        "callable_cases": ok_count,
        "server_error_cases": err5xx_count,
        "exception_cases": exc_count,
        "callable_rate": round(ok_count / len(cases) * 100, 2) if cases else 0,
    }
    report = {"summary": summary, "results": results}
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
