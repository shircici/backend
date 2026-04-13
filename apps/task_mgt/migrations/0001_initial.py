from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(db_index=True, max_length=200)),
                ("description", models.TextField(blank=True, default="")),
                ("status", models.CharField(choices=[("todo", "待办"), ("in_progress", "进行中"), ("done", "已完成")], db_index=True, default="todo", max_length=20)),
                ("priority", models.CharField(choices=[("low", "低"), ("medium", "中"), ("high", "高")], db_index=True, default="medium", max_length=20)),
                ("due_date", models.DateField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("creator", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name="tasks", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "task", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["creator", "status", "created_at"], name="idx_task_user_st_ct")),
        migrations.AddIndex(model_name="task", index=models.Index(fields=["creator", "priority", "due_date"], name="idx_task_user_pr_dd")),
    ]
