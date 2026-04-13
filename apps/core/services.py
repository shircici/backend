from datetime import timedelta

from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone


class TokenCipherService:
    @staticmethod
    def _get_cipher():
        key = settings.FERNET_KEY
        if not key:
            raise ValueError("FERNET_KEY is required in environment variables")
        return Fernet(key.encode())

    @classmethod
    def encrypt(cls, plain_text: str) -> str:
        return cls._get_cipher().encrypt(plain_text.encode()).decode()

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        return cls._get_cipher().decrypt(encrypted_text.encode()).decode()


def build_expire_time(seconds: int):
    return timezone.now() + timedelta(seconds=seconds)
