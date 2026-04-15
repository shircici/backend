from django.conf import settings
from django.db import models


def default_algorithm_thresholds():
    return {"min_roas": 3, "ideal_roas": 5}


def default_empty_dict():
    return {}


class AlgorithmConfig(models.Model):
    """
    算法阈值配置；阈值存于 JSONField，便于后续扩展（如 max_cpa、目标毛利率等）。
    """

    code = models.CharField(
        max_length=64,
        unique=True,
        default="default",
        db_index=True,
        help_text="配置编码，用于缓存键与多环境切换",
    )
    name = models.CharField(max_length=128, blank=True, default="")
    thresholds = models.JSONField(default=default_algorithm_thresholds, help_text="如 min_roas、ideal_roas 等")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "selection_algorithm_config"
        indexes = [
            models.Index(fields=["is_active", "code"], name="idx_sel_algo_act_code"),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({'active' if self.is_active else 'inactive'})"


class DecisionLog(models.Model):
    """单次选品决策审计：输入快照、ROAS 结果与决策标签。"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="selection_decision_logs",
        db_index=True,
    )
    product_id = models.BigIntegerField(db_index=True, help_text="业务侧商品主键")
    input_params = models.JSONField(default=default_empty_dict, help_text="前端/WMS 等参与计算的原始入参")
    roas = models.DecimalField(max_digits=20, decimal_places=6, help_text="计算得到的 ROAS")
    decision_label = models.CharField(max_length=64, db_index=True, help_text="决策标签，如 PASS / HOLD / REJECT")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "selection_decision_log"
        indexes = [
            models.Index(fields=["user", "created_at"], name="idx_sel_dlog_user_ct"),
            models.Index(fields=["product_id", "created_at"], name="idx_sel_dlog_prod_ct"),
        ]

    def __str__(self) -> str:
        return f"DecisionLog(user={self.user_id}, product={self.product_id}, label={self.decision_label})"


class InfluencerMatchPreview(models.Model):
    """
    批量「商品 × 达人」测算的临时预览结果（可按 batch_id 列表查询后定期清理）。
    """

    batch_id = models.CharField(max_length=40, db_index=True, help_text="一次批量任务 ID，可与 Redis 进度键对应")
    product_id = models.BigIntegerField(db_index=True)
    influencer_id = models.CharField(max_length=64, db_index=True, help_text="达人侧主键（字符串兼容各平台）")
    roas = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    grade = models.CharField(max_length=1, db_index=True, help_text="建议等级 A / B / C")
    detail = models.JSONField(default=default_empty_dict, blank=True, help_text="测算入参快照或错误信息")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "selection_influencer_match_preview"
        indexes = [
            models.Index(fields=["batch_id", "product_id"], name="idx_sel_prev_batch_prod"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["batch_id", "influencer_id"], name="uniq_sel_prev_batch_inf"),
        ]

    def __str__(self) -> str:
        return f"InfluencerMatchPreview(batch={self.batch_id}, inf={self.influencer_id}, grade={self.grade})"
