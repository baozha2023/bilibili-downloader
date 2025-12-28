import binascii
import time

def crack_crc32(crc32_hash):
    """
    Brute force crack CRC32 hash to find the original UID.
    UID is usually a numeric string.
    """
    target = int(crc32_hash, 16)
    print(f"Target CRC32: {crc32_hash} ({target})")
    
    start_time = time.time()
    # Try UIDs from 1 to 1,000,000,000 (adjust limit as needed)
    # Bilibili UIDs are around 1-10 digits.
    # Checking 100M takes some time in Python.
    
    # Heuristic: Start from common ranges or just 1.
    for i in range(1, 1000000000):
        s = str(i)
        if binascii.crc32(s.encode()) == target:
            print(f"Found! UID: {i}")
            print(f"Time taken: {time.time() - start_time:.2f}s")
            return i
        
        if i % 1000000 == 0:
            print(f"Checked {i} UIDs... ({time.time() - start_time:.2f}s)")
            
    print("Not found in range.")
    return None

if __name__ == "__main__":
    crack_crc32("326e35e7")
