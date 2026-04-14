from celery import shared_task

from .models import Creator
from .services import build_multilingual_pitch


@shared_task(name="creator_mgt.generate_multilingual_pitch")
def generate_multilingual_pitch(creator_id: int, target_language: str):
    creator = Creator.objects.get(pk=creator_id)
    return build_multilingual_pitch(creator=creator, target_language=target_language)
