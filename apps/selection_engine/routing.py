from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/selection/batch/<str:batch_id>/", consumers.SelectionBatchProgressConsumer.as_asgi()),
]
