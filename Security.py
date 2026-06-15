"""
Security Module

This module handles all cryptographic and security-related operations in the system.
It provides mechanisms for secure communication between client and server,
including key exchange and data encryption/decryption.

Main responsibilities:
- Generate and manage cryptographic keys
- Perform symmetric and asymmetric encryption/decryption
- Support secure key exchange between parties
- Ensure confidentiality and integrity of transmitted data
"""

import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet

# ==========================================
# Password Hashing (using SHA-256 with salt)
# ==========================================

class DataHasher:
    @staticmethod
    def hash_data(data: str) -> tuple[bytes, bytes]:
        # Hashes any string (password, flag, description) with a random salt
        salt = os.urandom(16)  # Random salt
        digest = hashes.Hash(hashes.SHA256())
        digest.update(salt + data.encode())
        hashed_data = digest.finalize()
        return hashed_data, salt

    @staticmethod
    def verify_data(data: str, hashed_data: bytes, salt: bytes) -> bool:
        # Verifies whether the provided data matches the hash and salt
        digest = hashes.Hash(hashes.SHA256())
        digest.update(salt + data.encode())
        return digest.finalize() == hashed_data

# ==========================================
# Symmetric Encryption (AES)
# ==========================================
class SymmetricCipher:

    def __init__(self, key: bytes = None):
        # If no key is provided, generate a new one
        self.key = key if key else Fernet.generate_key()
        self.cipher = Fernet(self.key)

    def encrypt(self, data: str) -> bytes:
        # Encrypts textual data
        return self.cipher.encrypt(data.encode())

    def decrypt(self, encrypted_data: bytes) -> str:
        # Decrypts data back into text
        return self.cipher.decrypt(encrypted_data).decode()


# ==========================================
# Asymmetric Encryption (RSA)
# ==========================================
class RSAKeyExchange:

    def __init__(self):
        self.private_key = None
        self.public_key = None

    def generate_keys(self):
        # Generates a public/private key pair
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        return self.public_key

    def encrypt_key(self, public_key, symmetric_key: bytes) -> bytes:
        # Encrypts the symmetric key using the recipient's PUBLIC key
        return public_key.encrypt(
            symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def decrypt_key(self, encrypted_key: bytes) -> bytes:
        # Decrypts the symmetric key using the owner's PRIVATE key
        if not self.private_key:
            raise ValueError("Private key has not been generated!")
        return self.private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )