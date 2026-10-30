"""
Postings List Compression Utilities
Implements Variable-Byte (VByte) encoding and Delta (d-gap) encoding
for space-efficient postings list storage and fast decoding.
"""

from typing import List, Tuple
import struct


def delta_encode(numbers: List[int]) -> List[int]:
    """
    Computes d-gaps for a strictly increasing list of integers:
    [doc1, doc2, doc3] -> [doc1, doc2 - doc1, doc3 - doc2]
    """
    if not numbers:
        return []
    deltas = [numbers[0]]
    for i in range(1, len(numbers)):
        deltas.append(numbers[i] - numbers[i - 1])
    return deltas


def delta_decode(deltas: List[int]) -> List[int]:
    """
    Reconstructs original integers from d-gaps.
    """
    if not deltas:
        return []
    numbers = [deltas[0]]
    for i in range(1, len(deltas)):
        numbers.append(numbers[-1] + deltas[i])
    return numbers


def vbyte_encode_number(n: int) -> bytes:
    """
    Encodes a single unsigned integer using Variable-Byte (7 bits per byte, MSB is continuation flag).
    """
    if n < 0:
        raise ValueError("vbyte encoding requires non-negative integers")
    bytes_list = []
    while True:
        bytes_list.insert(0, n % 128)
        if n < 128:
            break
        n //= 128
    # Set high bit (continuation flag) on the last byte
    bytes_list[-1] += 128
    return bytes(bytes_list)


def vbyte_encode(numbers: List[int]) -> bytes:
    """
    Encodes a list of integers into a compressed bytes sequence using VByte.
    """
    return b"".join(vbyte_encode_number(n) for n in numbers)


def vbyte_decode(byte_data: bytes) -> List[int]:
    """
    Decodes a byte string compressed with VByte into a list of integers.
    """
    numbers = []
    n = 0
    for byte in byte_data:
        if byte < 128:
            n = 128 * n + byte
        else:
            n = 128 * n + (byte - 128)
            numbers.append(n)
            n = 0
    return numbers


def compress_postings(doc_ids: List[int], term_freqs: List[int], positions_list: List[List[int]]) -> bytes:
    """
    Compresses a full postings entry:
    - Delta-encodes sorted doc_ids
    - VByte encodes doc_ids, frequencies, and delta-encoded positions.
    """
    if not doc_ids:
        return b""
    
    num_postings = len(doc_ids)
    doc_id_deltas = delta_encode(doc_ids)
    
    # Payload format:
    # [num_postings] -> vbyte
    # [doc_id_deltas] -> vbyte
    # [term_frequencies] -> vbyte
    # For each doc: [num_positions] -> vbyte, [position_deltas] -> vbyte
    buffer = bytearray()
    buffer.extend(vbyte_encode([num_postings]))
    buffer.extend(vbyte_encode(doc_id_deltas))
    buffer.extend(vbyte_encode(term_freqs))
    
    for positions in positions_list:
        pos_deltas = delta_encode(positions)
        buffer.extend(vbyte_encode([len(pos_deltas)]))
        if pos_deltas:
            buffer.extend(vbyte_encode(pos_deltas))
            
    return bytes(buffer)


def decompress_postings(byte_data: bytes) -> Tuple[List[int], List[int], List[List[int]]]:
    """
    Decompresses bytes back to (doc_ids, term_freqs, positions_list).
    """
    if not byte_data:
        return [], [], []
        
    all_numbers = vbyte_decode(byte_data)
    if not all_numbers:
        return [], [], []
        
    idx = 0
    num_postings = all_numbers[idx]
    idx += 1
    
    doc_id_deltas = all_numbers[idx : idx + num_postings]
    idx += num_postings
    doc_ids = delta_decode(doc_id_deltas)
    
    term_freqs = all_numbers[idx : idx + num_postings]
    idx += num_postings
    
    positions_list = []
    for _ in range(num_postings):
        pos_count = all_numbers[idx]
        idx += 1
        if pos_count > 0:
            pos_deltas = all_numbers[idx : idx + pos_count]
            idx += pos_count
            positions_list.append(delta_decode(pos_deltas))
        else:
            positions_list.append([])
            
    return doc_ids, term_freqs, positions_list
