# 短信登录与风控 API 示例

本文档用于前端联调与测试验收，覆盖新增接口的请求/响应示例。

## 1. 发送验证码

- 方法与路径：`POST /api/auth/sms/send-code`
- 请求头（可选）：`X-Device-ID: qa-device-001`

请求体：

```json
{
  "phone": "13800138000",
  "country_code": "86",
  "voice": false
}
```

成功响应（200）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "phone": "+8613800138000",
    "expires_in": 300,
    "provider": "mock",
    "biz_id": "mock-sms-+8613800138000-123456",
    "message_type": "sms",
    "code": "123456"
  }
}
```

失败响应（429，限流）：

```json
{
  "code": 429,
  "message": "发送过于频繁，请稍后再试",
  "data": null
}
```

## 2. 验证码登录/注册（合并）

- 方法与路径：`POST /api/auth/mobile/login`
- 请求头（建议）：`X-Device-ID: qa-device-001`

请求体：

```json
{
  "mobile": "13800138000",
  "country_code": "86",
  "code": "123456",
  "agreed_privacy": true
}
```

成功响应（200）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "created": true,
    "access": "<JWT_ACCESS_TOKEN>",
    "refresh": "<JWT_REFRESH_TOKEN>",
    "user": {
      "id": 123,
      "username": "u_86_13800138000_1713090000",
      "mobile": "138****8000",
      "country_code": "86"
    }
  }
}
```

失败响应（400，未同意隐私协议）：

```json
{
  "code": 400,
  "message": "必须同意隐私协议",
  "data": null
}
```

失败响应（403，设备黑名单）：

```json
{
  "code": 403,
  "message": "设备已被风控拦截",
  "data": null
}
```

## 3. 账号注销（软删除）

- 方法与路径：`DELETE /api/user/account/`
- 认证：`Authorization: Bearer <ACCESS_TOKEN>`

请求体：

```json
{
  "code": "654321",
  "reason": "用户主动注销"
}
```

成功响应（200）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "deleted": true
  }
}
```

失败响应（400，未绑定手机号）：

```json
{
  "code": 400,
  "message": "未绑定手机号",
  "data": null
}
```

## 4. 手机号换绑申诉

- 方法与路径：`POST /api/user/phone-rebind-appeals`
- 认证：`Authorization: Bearer <ACCESS_TOKEN>`

请求体示例：

```json
{
  "current_country_code": "86",
  "current_phone_number": "13800138000",
  "requested_country_code": "86",
  "requested_phone_number": "13900139000",
  "proof_material_urls": [
    "https://cdn.example.com/proof/id-front.jpg",
    "https://cdn.example.com/proof/id-back.jpg"
  ]
}
```

成功响应（201）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "user": 123,
    "status": "pending",
    "created_at": "2026-04-14T12:00:00+08:00",
    "updated_at": "2026-04-14T12:00:00+08:00",
    "current_country_code": "86",
    "current_phone_number": "13800138000",
    "requested_country_code": "86",
    "requested_phone_number": "13900139000",
    "proof_material_urls": [
      "https://cdn.example.com/proof/id-front.jpg",
      "https://cdn.example.com/proof/id-back.jpg"
    ],
    "reviewer": "",
    "review_note": ""
  }
}
```

## 5. 短信通道到达率统计

- 方法与路径：`GET /api/ops/sms/channel-stats?days=7`
- 认证：`Authorization: Bearer <OPS_ADMIN_ACCESS_TOKEN>`

成功响应（200）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "days": 7,
    "channels": {
      "aliyun": {
        "total": 1200,
        "delivered": 1160,
        "failed": 40,
        "reach_rate": 0.9667
      },
      "tencent": {
        "total": 80,
        "delivered": 70,
        "failed": 10,
        "reach_rate": 0.875
      }
    }
  }
}
```

## 6. 常见错误码

- `400`：参数错误、验证码错误、隐私协议未勾选
- `401`：未登录或 Token 无效
- `403`：设备触发风控黑名单
- `429`：频控或全局熔断触发
- `500`：服务内部错误
# 短信登录与风控 API 示例

本文档用于前端联调与测试验收，覆盖新增接口的请求/响应示例。

## 1. 发送验证码

- 方法与路径：`POST /api/auth/sms/send-code`
- 请求头（可选）：`X-Device-ID: qa-device-001`

请求体：

```json
{
  "phone": "13800138000",
  "country_code": "86",
  "voice": false
}
```

成功响应（200）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "phone": "+8613800138000",
    "expires_in": 300,
    "provider": "mock",
    "biz_id": "mock-sms-+8613800138000-123456",
    "message_type": "sms",
    "code": "123456"
  }
}
```

失败响应（429，限流）：

```json
{
  "code": 429,
  "message": "发送过于频繁，请稍后再试",
  "data": null
}
```

## 2. 验证码登录/注册（合并）

- 方法与路径：`POST /api/auth/mobile/login`
- 请求头（建议）：`X-Device-ID: qa-device-001`

请求体：

```json
{
  "mobile": "13800138000",
  "country_code": "86",
  "code": "123456",
  "agreed_privacy": true
}
```

成功响应（200）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "created": true,
    "access": "<JWT_ACCESS_TOKEN>",
    "refresh": "<JWT_REFRESH_TOKEN>",
    "user": {
      "id": 123,
      "username": "u_86_13800138000_1713090000",
      "mobile": "138****8000",
      "country_code": "86"
    }
  }
}
```

失败响应（400，未同意隐私协议）：

```json
{
  "code": 400,
  "message": "必须同意隐私协议",
  "data": null
}
```

失败响应（403，设备黑名单）：

```json
{
  "code": 403,
  "message": "设备已被风控拦截",
  "data": null
}
```

## 3. 账号注销（软删除）

- 方法与路径：`DELETE /api/user/account/`
- 认证：`Authorization: Bearer <ACCESS_TOKEN>`

请求体：

```json
{
  "code": "654321",
  "reason": "用户主动注销"
}
```

成功响应（200）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "deleted": true
  }
}
```

失败响应（400，未绑定手机号）：

```json
{
  "code": 400,
  "message": "未绑定手机号",
  "data": null
}
```

## 4. 手机号换绑申诉

- 方法与路径：`POST /api/user/phone-rebind-appeals`
- 认证：`Authorization: Bearer <ACCESS_TOKEN>`

请求体示例：

```json
{
  "current_country_code": "86",
  "current_phone_number": "13800138000",
  "requested_country_code": "86",
  "requested_phone_number": "13900139000",
  "proof_material_urls": [
    "https://cdn.example.com/proof/id-front.jpg",
    "https://cdn.example.com/proof/id-back.jpg"
  ]
}
```

成功响应（201）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "user": 123,
    "status": "pending",
    "created_at": "2026-04-14T12:00:00+08:00",
    "updated_at": "2026-04-14T12:00:00+08:00",
    "current_country_code": "86",
    "current_phone_number": "13800138000",
    "requested_country_code": "86",
    "requested_phone_number": "13900139000",
    "proof_material_urls": [
      "https://cdn.example.com/proof/id-front.jpg",
      "https://cdn.example.com/proof/id-back.jpg"
    ],
    "reviewer": "",
    "review_note": ""
  }
}
```

## 5. 短信通道到达率统计

- 方法与路径：`GET /api/ops/sms/channel-stats?days=7`
- 认证：`Authorization: Bearer <OPS_ADMIN_ACCESS_TOKEN>`

成功响应（200）：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "days": 7,
    "channels": {
      "aliyun": {
        "total": 1200,
        "delivered": 1160,
        "failed": 40,
        "reach_rate": 0.9667
      },
      "tencent": {
        "total": 80,
        "delivered": 70,
        "failed": 10,
        "reach_rate": 0.875
      }
    }
  }
}
```

## 6. 常见错误码

- `400`：参数错误、验证码错误、隐私协议未勾选
- `401`：未登录或 Token 无效
- `403`：设备触发风控黑名单
- `429`：频控或全局熔断触发
- `500`：服务内部错误
