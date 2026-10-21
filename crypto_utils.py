"""
ابزارهای رمزنگاری برای چت امن
RSA-2048 برای تبادل کلید + AES-256-GCM برای رمزنگاری پیام‌ها
"""

import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_keypair():
    """یک جفت کلید RSA-2048 (خصوصی، عمومی) تولید می‌کند"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


def public_key_to_pem(public_key):
    """کلید عمومی را به فرمت PEM (bytes) تبدیل می‌کند"""
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def load_public_key(pem_bytes):
    """کلید عمومی را از فرمت PEM بارگذاری می‌کند"""
    return serialization.load_pem_public_key(pem_bytes)


def encrypt_message(plaintext: str, recipient_public_key) -> bytes:
    """
    پیام را با AES-256-GCM رمزنگاری می‌کند و کلید AES را با RSA رمزنگاری می‌کند.
    خروجی: کلید رمزشده (۲۵۶ بایت) + nonce (۱۲ بایت) + متن رمزشده
    """
    aes_key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(aes_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

    encrypted_key = recipient_public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return encrypted_key + nonce + ciphertext


def decrypt_message(data: bytes, private_key) -> str:
    """پیام رمزشده را رمزگشایی می‌کند"""
    encrypted_key = data[:256]
    nonce = data[256:268]
    ciphertext = data[268:]

    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    aesgcm = AESGCM(aes_key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


# ---------- password-based encryption (encrypted exports / backups) ----------
# scrypt(password) -> AES-256-GCM key. File layout: MAGIC + salt(16) + nonce(12) + ciphertext.

import hashlib

PASSWORD_MAGIC = b"LCENC1"


def _derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2 ** 15, r=8, p=1, dklen=32,
        maxmem=128 * 1024 * 1024,
    )


def encrypt_with_password(data: bytes, password: str) -> bytes:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    ciphertext = AESGCM(_derive_key(password, salt)).encrypt(nonce, data, PASSWORD_MAGIC)
    return PASSWORD_MAGIC + salt + nonce + ciphertext


def decrypt_with_password(blob: bytes, password: str) -> bytes:
    """Raises ValueError for a wrong password or a corrupted / foreign file."""
    head = len(PASSWORD_MAGIC)
    if not blob.startswith(PASSWORD_MAGIC) or len(blob) < head + 16 + 12 + 16:
        raise ValueError("not an encrypted export")
    salt = blob[head:head + 16]
    nonce = blob[head + 16:head + 28]
    try:
        return AESGCM(_derive_key(password, salt)).decrypt(nonce, blob[head + 28:], PASSWORD_MAGIC)
    except Exception:
        raise ValueError("wrong password or damaged file")
