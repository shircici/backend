# API 契约与 RBAC

## 一、API 契约（前后端协作）

1. **唯一事实来源**：接口路径、HTTP 方法、请求/响应 JSON 结构以 **OpenAPI 3** 为准。
2. **文档入口**（由 DRF + drf-spectacular 自动生成）：
   - Swagger UI：`/swagger/`
   - ReDoc：`/redoc/`
   - 原始 Schema：`/api/schema/`
3. **禁止**：仅通过微信/口头传递接口 JSON 作为契约；变更须先更新 Schema 并通知前端拉取新版本。
4. **基地址配置**：在 `.env` 中设置 `BACKEND_PUBLIC_URL`（含协议与端口），OpenAPI `servers` 将展示该地址，便于前端 B 配置 `baseURL`。
5. **生产拓岳域名（约定）**：`BACKEND_PUBLIC_URL=https://api.tuoyue-tech.com`。第三方 **Webhook**（如 17Track 小包跟踪推送）回调地址为：`https://api.tuoyue-tech.com/v1/logistics/webhook`（与路由 `v1/logistics/webhook` 一致；可选请求头 `X-Webhook-Token` 与 `LOGISTICS_WEBHOOK_TOKEN` 对齐）。

## 二、端口与环境约定（不写死在业务代码）

| 组件 | 默认端口 | 配置方式 |
|------|----------|----------|
| Django 开发服务 | 8000 | `DJANGO_RUNSERVER_PORT`（文档/约定）；启动：`python manage.py runserver 0.0.0.0:8000` |
| MySQL | 3306 | `MYSQL_PORT` / 连接串 |
| Redis | 6379 | `REDIS_URL`（如 `redis://主机:6379/1`） |

主机与密钥一律来自 `.env`，禁止在代码中写死具体 IP。

## 三、技术栈（与准则对齐）

- 语言：Python
- Web：Django
- 接口：Django REST Framework（DRF）
- 权限：**RBAC**（Django `Group` 角色 + DRF `permission_classes`；运维另配合 `IsOpsAdmin`）
- 异步：Celery + Redis
- 管理后台：Django Admin

## 四、RBAC 角色说明

| Group 名称 | 用途 |
|------------|------|
| `api_integrator` | 调用采集、库存同步、平台 Token 刷新等业务 API（`RBAC_ENFORCE=true` 时强制校验） |
| `ops_admin` | 运维接口（dead-letter、重放审计等），与 `IsOpsAdmin` 一致 |

- 生产建议：`RBAC_ENFORCE=true`，并为业务账号加入 `api_integrator`。
- 联调阶段：`RBAC_ENFORCE=false`（默认）时，业务接口仅需 **已登录** 即可。

初始化组：

```bash
python manage.py create_rbac_groups
```

将用户加入业务角色（示例）：

```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; from django.contrib.auth.models import Group; u=get_user_model().objects.get(username='dev'); u.groups.add(Group.objects.get(name='api_integrator'))"
```
