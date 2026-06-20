import hashlib
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

def get_aes_key(raw_key: str) -> bytes:
    """
    Derive a 256-bit (32-byte) key from the raw key using SHA-256.
    """
    return hashlib.sha256(raw_key.encode('utf-8')).digest()

def generate_file_hash(file_path: str) -> str:
    """
    Generate SHA-256 hash of a file on disk in chunks to save memory.
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def generate_stream_hash(stream) -> str:
    """
    Generate SHA-256 hash of an in-memory byte stream.
    Reset position to 0 after hashing.
    """
    sha256 = hashlib.sha256()
    stream.seek(0)
    while chunk := stream.read(8192):
        sha256.update(chunk)
    stream.seek(0)
    return sha256.hexdigest()

def encrypt_file(source_path: str, target_path: str, raw_key: str) -> None:
    """
    Encrypt a file using AES-256-CBC.
    Prepends the 16-byte random IV to the encrypted file.
    """
    key = get_aes_key(raw_key)
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    
    with open(source_path, 'rb') as f_in, open(target_path, 'wb') as f_out:
        # Write IV first
        f_out.write(iv)
        
        while chunk := f_in.read(64 * 1024):  # 64KB chunks
            # If it's the last chunk, pad it
            if len(chunk) < 64 * 1024:
                padded_chunk = pad(chunk, AES.block_size)
                f_out.write(cipher.encrypt(padded_chunk))
                break
            else:
                next_chunk = f_in.read(1)
                if not next_chunk:
                    # Current chunk is the final one, pad it
                    padded_chunk = pad(chunk, AES.block_size)
                    f_out.write(cipher.encrypt(padded_chunk))
                    break
                else:
                    # Put back the 1 byte read
                    f_in.seek(-1, os.SEEK_CUR)
                    f_out.write(cipher.encrypt(chunk))

def decrypt_file(source_path: str, target_path: str, raw_key: str) -> None:
    """
    Decrypt an AES-256-CBC encrypted file.
    Reads the 16-byte IV from the beginning of the file.
    """
    key = get_aes_key(raw_key)
    
    with open(source_path, 'rb') as f_in:
        iv = f_in.read(16)
        if len(iv) < 16:
            raise ValueError("Invalid encrypted file: file too small or missing IV.")
            
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        # Determine total size of ciphertext to handle padding removal on last chunk
        f_in.seek(0, os.SEEK_END)
        total_size = f_in.tell()
        ciphertext_size = total_size - 16
        f_in.seek(16)  # reset back to start of ciphertext
        
        with open(target_path, 'wb') as f_out:
            bytes_read = 0
            while chunk := f_in.read(64 * 1024):
                bytes_read += len(chunk)
                if bytes_read >= ciphertext_size:
                    # Last chunk, decrypt and unpad
                    decrypted_chunk = cipher.decrypt(chunk)
                    f_out.write(unpad(decrypted_chunk, AES.block_size))
                else:
                    f_out.write(cipher.decrypt(chunk))
