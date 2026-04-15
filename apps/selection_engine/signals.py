from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AlgorithmConfig
from .services.algorithm_config import invalidate_threshold_cache


@receiver(post_save, sender=AlgorithmConfig)
def _clear_algo_threshold_cache(sender, **kwargs):
    invalidate_threshold_cache()
