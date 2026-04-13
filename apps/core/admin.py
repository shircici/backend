from django.contrib import admin

from .models import (
    ApiIdempotencyRecord,
    CollectionTask,
    DeadLetterTask,
    InventorySyncLog,
    PlatformToken,
    Shop,
    Product,
    ProductVariant,
    ReplayAuditLog,
    Order,
    LogisticsShipment,
    SyncRule,
)

admin.site.register(PlatformToken)
admin.site.register(Product)
admin.site.register(ProductVariant)
admin.site.register(InventorySyncLog)
admin.site.register(CollectionTask)
admin.site.register(SyncRule)
admin.site.register(DeadLetterTask)
admin.site.register(ApiIdempotencyRecord)
admin.site.register(ReplayAuditLog)
admin.site.register(Shop)
admin.site.register(Order)
admin.site.register(LogisticsShipment)
