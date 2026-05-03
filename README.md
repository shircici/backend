# 千万级 SKU 管理后端（Django + MySQL）

本项目提供可运行的 SKU 管理后端，重点覆盖千万级数据场景下的索引、分页、批量写入、缓存与异步导出。

## 0. 技术准则（与项目规范对齐）

| 项 | 说明 |
|----|------|
| API 契约 | 由 DRF 定义；**OpenAPI 为唯一契约来源**，见 `/swagger/`、`/redoc/`、`/api/schema/`；禁止仅靠口头/微信传 JSON |
| 后端服务 | 开发默认 **8000**（`DJANGO_RUNSERVER_PORT`）；前端通过该端口调用 API |
| MySQL | 默认端口 **3306**（`MYSQL_PORT`） |
| Redis | 默认端口 **6379**（写在 `REDIS_URL` 中） |
| 技术栈 | Python + **Django** + **DRF** + **RBAC（Django Group）** + **Celery** + Django Admin |

详细说明见 `docs/API契约与RBAC.md`。初始化 RBAC 组：`python manage.py create_rbac_groups` 或 `task rbac:groups`。

## 1. 环境要求
- Python 3.10+
- MySQL 8.0+
- Redis 6+（缓存 + Celery broker/result）

## 2. 安装依赖
```bash
pip install -r requirements.txt
```

## 3. 环境变量
复制 `.env.example` 并按需修改：
```bash
copy .env.example .env
```

关键变量：
- `BACKEND_PUBLIC_URL`（OpenAPI servers，供前端配置 baseURL；生产拓岳示例 `https://api.tuoyue-tech.com`，17Track Webhook 填 `https://api.tuoyue-tech.com/v1/logistics/webhook`）
- `TRACK17_API_KEY` / `LOGISTICS_WEBHOOK_TOKEN`（17Track 出站与 Webhook 验签，见 `.env.example`）
- `RBAC_ENFORCE` / `RBAC_API_INTEGRATOR_GROUPS`（生产建议 `RBAC_ENFORCE=true`）
- `MYSQL_DATABASE` / `MYSQL_HOST` / `MYSQL_USER` / `MYSQL_PASSWORD`
- `MYSQL_REPLICA_*`（读库，可先与主库一致）
- `REDIS_URL`
- `DB_CONN_MAX_AGE`

## 4. 数据库初始化
```bash
python manage.py migrate
python manage.py createsuperuser
```

## 5. 启动项目
```bash
python manage.py runserver 0.0.0.0:8000
```

## 6. 启动 Celery
```bash
celery -A myproject worker -l info -P solo
celery -A myproject beat -l info
```

## 7. 核心 API（SKU）
- `GET /api/sku/detail/{sku_code}/`：单条详情（Redis 缓存 + 防击穿）
- `GET /api/sku/list/`：游标分页列表（过滤 + 排序）
- `POST /api/sku/bulk-create/`：批量创建（`bulk_create` 分批）
- `POST /api/sku/bulk-update/`：批量更新（`update` + 版本自增）
- `POST /api/sku/bulk-delete/`：批量软删除（`update`）
- `GET /api/sku/search/?keyword=xxx`：SKU 搜索（当前 `icontains`）
- `POST /api/sku/export/`：异步导出 CSV（Celery）

## 8. Swagger
- Swagger：`/swagger/`
- Redoc：`/redoc/`
- OpenAPI Schema：`/api/schema/`
- 健康检查：`/api/health/`

## 9. 核心优化说明
- 复合索引：`category_id + status + is_deleted + id` 等，覆盖高频条件。
- 软删除：`is_deleted` 避免高并发物理删除带来的锁开销。
- Keyset 分页：DRF CursorPagination，避免大 offset 扫描。
- 批量操作：`bulk_create` + `update` 避免逐行 ORM 调用。
- 缓存策略：详情缓存 + 锁（`cache.add`）防缓存击穿。
- 读写分离：`DATABASE_ROUTERS` 示例（写主库，读从库）。
- 分区建议：生产使用 MySQL RANGE/HASH 分区（在模型注释中给出策略）。

## 10. API 快速测试
```bash
curl "$API_BASE_URL/api/sku/detail/SKU001/"
curl "$API_BASE_URL/api/sku/list/?category_id=1&order_by=-id"
curl "$API_BASE_URL/api/sku/search/?keyword=SKU"
```

## 11. 10万条批量写入测试
```bash
python scripts/bench_bulk_insert.py
```

## 12. 稳定性增强
- 幂等：写接口可传 `X-Idempotency-Key`
- 请求追踪：支持 `X-Request-ID`
- 限流：写接口自动按 IP + 路径限流

压测示例：
```bash
k6 run scripts/k6_sku_detail.js
```

## 13. 运维权限
- 运维接口默认要求 JWT 登录
- 赋权方式三选一：
  - superuser
  - 环境变量 `OPS_ADMIN_USERNAMES` 白名单
  - 用户加入 Django 组 `ops_admin`
- 自检接口：`GET /api/ops/whoami/`

授权命令示例：
```bash
python manage.py set_ops_admin --username admin --action grant
python manage.py set_ops_admin --username admin --action revoke
python manage.py list_ops_admin
python manage.py sync_ops_admin_from_settings --dry-run
python manage.py sync_ops_admin_from_settings
python manage.py prune_ops_admin --dry-run
python manage.py prune_ops_admin --keep-superuser
```

## 14. 关键测试
```bash
python manage.py test apps.core.tests.test_ops_permissions
```

不依赖 MySQL 的测试运行方式（推荐）：
```bash
python manage.py test apps.core.tests.test_ops_permissions --settings=myproject.settings_test
```

使用 pytest 运行：
```bash
pytest
pytest apps/core/tests/test_ops_permissions_pytest.py
```

## 14.1 在 Docker 里跑测试（Windows/PowerShell 友好）
不依赖 MySQL/Redis（复刻 CI 的 `settings_test`，SQLite in-memory）：
```powershell
.\scripts\test_in_docker.ps1
.\scripts\test_in_docker.ps1 -Runner django
.\scripts\test_in_docker.ps1 -- -k ops_permissions
```

需要连 MySQL/Redis 的集成测试（docker compose）：
```bash
docker compose up -d mysql redis
docker compose run --rm backend-test
```

## 15. 一键任务命令（Taskfile）
安装 [go-task](https://taskfile.dev/) 后可使用：
```bash
task install
task migrate
task run
task test
task pytest
task preflight
task worker
task beat
task ops:list
task ops:sync
task ops:prune
```

## 16. CI 持续集成
- 已提供 GitHub Actions：`.github/workflows/ci.yml`
- 触发条件：`push` 到 `main/master` 或 `pull_request`
- 执行内容：
  - `python manage.py test --settings=myproject.settings_test`
  - `pytest`

## 17. 发布前自检
```bash
python manage.py preflight_check
```
检查项：
- 必需环境变量
- 数据库连通性
- Redis 缓存可读写

## 18. 上线清单
- 参考 `docs/上线检查清单.md`

## 19. 故障应急
- 参考 `docs/故障应急手册.md`

## 20. SLA 与告警阈值
- 参考 `docs/SLA与告警阈值建议.md`

## 21. 容量规划
- 参考 `docs/容量规划建议.md`
# backend
