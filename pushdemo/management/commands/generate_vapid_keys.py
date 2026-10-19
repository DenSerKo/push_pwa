import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from django.core.management.base import BaseCommand


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class Command(BaseCommand):
    help = "Generate a VAPID key pair and print environment variable values."

    def handle(self, *args, **options):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_bytes = private_key.public_key().public_bytes(
            encoding=Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        # pywebpush/py-vapid expects the private key as base64-encoded DER,
        # not merely the 32-byte EC scalar.
        private_der = private_key.private_bytes(
            encoding=Encoding.DER,
            format=PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=NoEncryption(),
        )
        private_b64 = base64.b64encode(private_der).decode("ascii")

        self.stdout.write("Скопируй эти значения в переменные окружения (приватный ключ не публикуй):")
        self.stdout.write(f"VAPID_PUBLIC_KEY={b64url(public_bytes)}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={private_b64}")
        self.stdout.write("VAPID_SUBJECT=mailto:you@example.com")
