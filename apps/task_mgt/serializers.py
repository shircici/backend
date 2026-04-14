from django.contrib.auth.models import User
from rest_framework import serializers

from apps.core.sms_service import verify_sms_code_and_consume

from .models import Task


class PhoneRegisterSerializer(serializers.Serializer):
    """手机号注册：username 使用手机号，需与短信验证码一致且服务端校验通过。"""

    phone = serializers.RegexField(regex=r"^1\d{10}$")
    password = serializers.CharField(write_only=True, min_length=6)
    sms_code = serializers.RegexField(regex=r"^\d{4,6}$")

    def validate_phone(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("该手机号已注册")
        return value

    def create(self, validated_data):
        phone = validated_data["phone"]
        ok, err_msg, _status_code = verify_sms_code_and_consume(phone, validated_data["sms_code"])
        if not ok:
            raise serializers.ValidationError({"sms_code": err_msg or "验证码无效"})
        return User.objects.create_user(
            username=phone,
            email="",
            password=validated_data["password"],
        )


class TaskSerializer(serializers.ModelSerializer):
    creator = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "due_date",
            "creator",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "creator", "created_at", "updated_at"]
