from openpyxl import Workbook


def build_rows():
    rows = [
        ("system", "GET", "/api/schema/", "OpenAPI Schema", "否"),
        ("system", "GET", "/swagger/", "Swagger 文档页", "否"),
        ("system", "GET", "/redoc/", "Redoc 文档页", "否"),
        ("system", "GET", "/metrics", "监控指标", "视部署策略"),
        ("core-auth", "GET", "/api/auth/me", "当前用户信息", "是"),
        ("core-auth", "GET", "/api/auth/{platform}/login/", "第三方登录入口", "是"),
        ("core-auth", "GET", "/api/auth/{platform}/callback/", "第三方回调处理", "是"),
        ("core-auth", "POST", "/api/auth/{platform}/refresh/", "平台 token 刷新", "是"),
        ("core-goods", "GET", "/api/goods/", "商品列表", "是"),
        ("core-goods", "POST", "/api/goods/", "创建商品", "是"),
        ("core-goods", "GET", "/api/goods/{goods_id}", "商品详情", "是"),
        ("core-goods", "PUT", "/api/goods/{goods_id}", "更新商品", "是"),
        ("core-goods", "DELETE", "/api/goods/{goods_id}", "删除商品", "是"),
        ("core-shop", "GET", "/api/shops/", "店铺列表", "是"),
        ("core-inventory", "GET", "/api/inventory/alerts", "库存预警", "是"),
        ("core-inventory", "GET", "/api/inventory/logs", "库存日志", "是"),
        ("core-inventory", "POST", "/api/inventory/sync", "触发库存同步", "是"),
        ("core-orders", "GET", "/api/orders/", "订单列表", "是"),
        ("core-orders", "PUT", "/api/orders/{order_id}/status", "更新订单状态", "是"),
        ("core-orders", "GET", "/api/orders/export", "订单导出", "是"),
        ("core-logistics", "GET", "/api/logistics/shipments/", "发货单列表", "是"),
        ("core-logistics", "GET", "/api/logistics/track/{waybill}", "运单跟踪", "是"),
        ("core-task", "POST", "/api/tasks/collect/", "创建采集任务", "是"),
        ("core-task", "GET", "/api/tasks/{task_id}/status/", "查询采集任务状态", "是"),
        ("core-sync", "POST", "/api/sync/trigger/", "触发同步任务", "是"),
        ("core-sync", "GET", "/api/sync/log/", "同步日志", "是"),
        ("core-ops", "GET", "/api/ops/dead-letter/", "死信列表", "是"),
        ("core-ops", "POST", "/api/ops/dead-letter/{dead_letter_id}/replay/", "死信重放", "是"),
        ("core-ops", "GET", "/api/ops/replay-audit/", "重放审计日志", "是"),
        ("core-ops", "GET", "/api/ops/whoami/", "运维身份信息", "是"),
        ("core-health", "GET", "/api/health/", "健康检查", "否/弱鉴权可配置"),
        ("sku", "GET", "/api/sku/detail/{sku_code}/", "SKU 详情", "是"),
        ("sku", "GET", "/api/sku/list/", "SKU 列表", "是"),
        ("sku", "POST", "/api/sku/bulk-create/", "批量创建 SKU", "是"),
        ("sku", "POST", "/api/sku/bulk-update/", "批量更新 SKU", "是"),
        ("sku", "POST", "/api/sku/bulk-delete/", "批量删除 SKU", "是"),
        ("sku", "GET", "/api/sku/search/", "SKU 搜索", "是"),
        ("sku", "POST", "/api/sku/export/", "导出 SKU", "是"),
        ("task-auth", "POST", "/api/auth/register/", "注册", "否"),
        ("task-auth", "POST", "/api/auth/login/", "JWT 登录", "否"),
        ("task-auth", "POST", "/api/auth/refresh/", "JWT 刷新", "否"),
        ("task", "GET", "/api/tasks/", "任务列表", "是"),
        ("task", "POST", "/api/tasks/", "创建任务", "是"),
        ("task", "GET", "/api/tasks/{pk}/", "任务详情", "是"),
        ("task", "PUT", "/api/tasks/{pk}/", "全量更新任务", "是"),
        ("task", "PATCH", "/api/tasks/{pk}/", "部分更新任务", "是"),
        ("task", "DELETE", "/api/tasks/{pk}/", "删除任务", "是"),
        ("creator", "GET", "/api/creators/", "达人列表", "是"),
        ("creator", "POST", "/api/creators/", "创建达人", "是"),
        ("creator", "GET", "/api/creators/{id}/", "达人详情", "是"),
        ("creator", "PUT", "/api/creators/{id}/", "全量更新达人", "是"),
        ("creator", "PATCH", "/api/creators/{id}/", "部分更新达人", "是"),
        ("creator", "DELETE", "/api/creators/{id}/", "删除达人", "是"),
        ("creator-ecom", "GET", "/api/creator-ecom-profiles/", "电商画像列表", "是"),
        ("creator-ecom", "POST", "/api/creator-ecom-profiles/", "创建电商画像", "是"),
        ("creator-ecom", "GET", "/api/creator-ecom-profiles/{id}/", "电商画像详情", "是"),
        ("creator-ecom", "PUT", "/api/creator-ecom-profiles/{id}/", "全量更新电商画像", "是"),
        ("creator-ecom", "PATCH", "/api/creator-ecom-profiles/{id}/", "部分更新电商画像", "是"),
        ("creator-ecom", "DELETE", "/api/creator-ecom-profiles/{id}/", "删除电商画像", "是"),
        ("creator-ai", "GET", "/api/creator-ai-insights/", "AI 洞察列表", "是"),
        ("creator-ai", "POST", "/api/creator-ai-insights/", "创建 AI 洞察", "是"),
        ("creator-ai", "GET", "/api/creator-ai-insights/{id}/", "AI 洞察详情", "是"),
        ("creator-ai", "PUT", "/api/creator-ai-insights/{id}/", "全量更新 AI 洞察", "是"),
        ("creator-ai", "PATCH", "/api/creator-ai-insights/{id}/", "部分更新 AI 洞察", "是"),
        ("creator-ai", "DELETE", "/api/creator-ai-insights/{id}/", "删除 AI 洞察", "是"),
        ("creator-asset", "GET", "/api/fulfillment-assets/", "素材资产列表", "是"),
        ("creator-asset", "POST", "/api/fulfillment-assets/", "创建素材资产", "是"),
        ("creator-asset", "GET", "/api/fulfillment-assets/{id}/", "素材资产详情", "是"),
        ("creator-asset", "PUT", "/api/fulfillment-assets/{id}/", "全量更新素材资产", "是"),
        ("creator-asset", "PATCH", "/api/fulfillment-assets/{id}/", "部分更新素材资产", "是"),
        ("creator-asset", "DELETE", "/api/fulfillment-assets/{id}/", "删除素材资产", "是"),
        ("creator-fulfillment", "GET", "/api/fulfillment-orders/", "履约单列表", "是"),
        ("creator-fulfillment", "POST", "/api/fulfillment-orders/", "创建履约单", "是"),
        ("creator-fulfillment", "GET", "/api/fulfillment-orders/{id}/", "履约单详情", "是"),
        ("creator-fulfillment", "PUT", "/api/fulfillment-orders/{id}/", "全量更新履约单", "是"),
        ("creator-fulfillment", "PATCH", "/api/fulfillment-orders/{id}/", "部分更新履约单", "是"),
        ("creator-fulfillment", "DELETE", "/api/fulfillment-orders/{id}/", "删除履约单", "是"),
        ("creator-ai", "POST", "/api/ai/multilingual-pitch/", "生成多语种邀约文案", "是"),
        ("creator-ai", "POST", "/api/ai/content-analysis/jobs/", "创建内容识别任务", "是"),
        ("creator-ai", "POST", "/api/ai/review-mining/jobs/", "创建评论挖掘任务", "是"),
        ("creator-ai", "GET", "/api/ai/jobs/{job_id}/", "查询 AI 任务状态/结果", "是"),
        ("creator-sync", "POST", "/api/creators/import/platform/", "平台导入达人", "是"),
        ("creator-sync", "GET", "/api/creators/search/", "达人复合检索", "是"),
        ("creator-sync", "POST", "/api/creators/{creator_id}/sync-audience/", "同步粉丝画像", "是"),
        ("creator-sync", "POST", "/api/creators/{creator_id}/sync-ecom/", "同步电商数据", "是"),
        ("creator-invite", "POST", "/api/invitations/{creator_id}/send/", "发送邀约", "是"),
        ("creator-invite", "GET", "/api/invitations/{creator_id}/history/", "邀约历史", "是"),
        ("creator-fulfillment", "POST", "/api/fulfillment-orders/{order_id}/dispatch/", "发货并回写运单", "是"),
        ("creator-fulfillment", "GET", "/api/fulfillment-orders/{order_id}/tracking/", "查询物流轨迹", "是"),
        ("creator-asset", "POST", "/api/fulfillment-assets/{asset_id}/authorize/", "保存广告授权码", "是"),
        ("creator-asset", "POST", "/api/assets/upload-url/", "获取素材上传 URL", "是"),
        ("creator-asset", "POST", "/api/assets/callback/", "素材上传回调入库", "是"),
        ("creator-webhook", "POST", "/api/webhooks/logistics/", "物流状态回调", "建议签名鉴权"),
        ("creator-dashboard", "GET", "/api/dashboard/creator-board/", "达人看板聚合", "是"),
    ]
    return rows


def main():
    wb = Workbook()
    ws = wb.active
    ws.title = "API联调清单"
    ws.append(["模块", "方法", "路径", "功能", "鉴权"])
    for row in build_rows():
        ws.append(list(row))
    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 52
    ws.column_dimensions["D"].width = 36
    ws.column_dimensions["E"].width = 16
    wb.save("docs/frontend_api_integration_list.xlsx")
    print("ok")


if __name__ == "__main__":
    main()
