import csv
from pathlib import Path

from celery import shared_task
from django.conf import settings

from .models import Sku


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def export_sku_to_csv(self, output_file: str = ""):
    output_dir = Path(settings.BASE_DIR) / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = Path(output_file) if output_file else output_dir / "sku_export.csv"

    queryset = Sku.objects.filter(is_deleted=False).values(
        "id", "sku_code", "product_name", "category_id", "price", "stock", "status", "updated_at"
    )
    with file_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "sku_code", "product_name", "category_id", "price", "stock", "status", "updated_at"])
        for row in queryset.iterator(chunk_size=2000):
            writer.writerow(
                [
                    row["id"],
                    row["sku_code"],
                    row["product_name"],
                    row["category_id"],
                    row["price"],
                    row["stock"],
                    row["status"],
                    row["updated_at"],
                ]
            )
    return {"file_path": str(file_path), "count": queryset.count()}
