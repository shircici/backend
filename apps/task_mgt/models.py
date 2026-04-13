from django.conf import settings
from django.db import models


class Task(models.Model):
    STATUS_TODO = "todo"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CHOICES = (
        (STATUS_TODO, "待办"),
        (STATUS_IN_PROGRESS, "进行中"),
        (STATUS_DONE, "已完成"),
    )

    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"
    PRIORITY_CHOICES = (
        (PRIORITY_LOW, "低"),
        (PRIORITY_MEDIUM, "中"),
        (PRIORITY_HIGH, "高"),
    )

    title = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO, db_index=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM, db_index=True)
    due_date = models.DateField(null=True, blank=True, db_index=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        db_table = "task"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["creator", "status", "created_at"], name="idx_task_user_st_ct"),
            models.Index(fields=["creator", "priority", "due_date"], name="idx_task_user_pr_dd"),
        ]
