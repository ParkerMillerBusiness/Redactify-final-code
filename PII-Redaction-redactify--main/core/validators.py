# core/validators.py

def luhn_ok(digits: str) -> bool:
    """
    Return True if digits pass Luhn checksum.
    """
    if not digits.isdigit():
        return False

    total = 0
    reverse = digits[::-1]
    for i, ch in enumerate(reverse):
        n = ord(ch) - 48
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0
