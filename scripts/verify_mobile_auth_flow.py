"""
本地联调脚本：覆盖短信发送、验证码登录、账号注销主流程。

用法：
python scripts/verify_mobile_auth_flow.py --base-url http://127.0.0.1:8000 --mobile 13800138000
"""
from __future__ import annotations

import argparse
import json
import sys

import requests


def pretty(resp: requests.Response) -> str:
    try:
        return json.dumps(resp.json(), ensure_ascii=False, indent=2)
    except Exception:
        return resp.text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--mobile", required=True)
    parser.add_argument("--country-code", default="86")
    parser.add_argument("--device-id", default="qa-device-001")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    mobile = args.mobile
    cc = args.country_code
    headers = {"X-Device-ID": args.device_id}

    print("1) 发送验证码")
    send_resp = requests.post(
        f"{base}/api/auth/sms/send-code",
        json={"phone": mobile, "country_code": cc},
        headers=headers,
        timeout=20,
    )
    print(pretty(send_resp))
    if send_resp.status_code != 200:
        return 1
    payload = send_resp.json().get("data", {})
    code = payload.get("code")
    full_phone = payload.get("phone")
    if not code:
        print("未拿到验证码（请在 DEBUG=True 下运行）")
        return 1

    print("\n2) 验证码登录/注册")
    login_resp = requests.post(
        f"{base}/api/auth/mobile/login",
        json={
            "mobile": mobile,
            "country_code": cc,
            "code": code,
            "agreed_privacy": True,
        },
        headers=headers,
        timeout=20,
    )
    print(pretty(login_resp))
    if login_resp.status_code != 200:
        return 1
    access = login_resp.json().get("data", {}).get("access")
    if not access:
        return 1

    print("\n3) 再发验证码用于注销")
    send2_resp = requests.post(
        f"{base}/api/auth/sms/send-code",
        json={"phone": mobile, "country_code": cc},
        headers=headers,
        timeout=20,
    )
    print(pretty(send2_resp))
    if send2_resp.status_code != 200:
        return 1
    code2 = send2_resp.json().get("data", {}).get("code")
    if not code2:
        return 1

    print("\n4) 账号注销（软删除）")
    delete_resp = requests.delete(
        f"{base}/api/user/account/",
        json={"code": code2, "reason": "qa-flow"},
        headers={"Authorization": f"Bearer {access}"},
        timeout=20,
    )
    print(pretty(delete_resp))
    if delete_resp.status_code != 200:
        return 1

    print("\n流程完成。full_phone =", full_phone)
    return 0


if __name__ == "__main__":
    sys.exit(main())
