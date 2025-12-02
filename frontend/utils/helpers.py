"""Helper functions for frontend"""

def get_col_letter(n):
    """Convert number to Excel column letter (0 -> A, 1 -> B, etc.)"""
    string_n = ""
    while n >= 0:
        n, remainder = divmod(n, 26)
        string_n = chr(65 + remainder) + string_n
        n -= 1
    return string_n
