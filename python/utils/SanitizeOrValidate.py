"""
This module provides functions for validating and sanitizing user input to prevent
SQL injection, XSS, and other security vulnerabilities.
"""

import re
import os
from typing import Optional, Union

# SQL Injection Detection Pattern
DB_PATTERN = re.compile(
    r"(--)|(;)|(union\s+select)|(drop\s+)|(insert\s+)|(delete\s+)|(update\s+)"
    r"|(exec\s*)|(execute\s*)|(script\s*)|(javascript:)|(onerror\s*=)|(onload\s*=)"
    r"|(')|('')|(\")|(\"\")|(select\s+.*\s+from)|(union\s+.*\s+select)",
    re.IGNORECASE,
)

# Username Pattern: alphanumeric with specific special characters
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-_%$#@!&]*[a-zA-Z0-9])?$")

# XSS Detection Pattern
XSS_PATTERN = re.compile(
    r"(<script[^>]*>.*?</script>)|(<.*?on\w+\s*=)|(<iframe)|(<object)|(<embed)|(<applet)",
    re.IGNORECASE | re.DOTALL,
)

# Path Traversal Pattern
PATH_TRAVERSAL_PATTERN = re.compile(
    r"(\.\./)|(\.\.\\/)|(%2e%2e%2f)|(%2e%2e/)", re.IGNORECASE
)


def valid_utf8(string: str) -> bool:
    """
    Check if a string is valid UTF-8.

    Args:
        string: The string to validate

    Returns:
        True if valid UTF-8, False otherwise
    """
    if not isinstance(string, str):
        return False

    try:
        # Python 3 strings are already unicode, but let's verify encoding/decoding works
        string.encode("utf-8", errors="strict").decode("utf-8", errors="strict")
        return True
    except (UnicodeEncodeError, UnicodeDecodeError, AttributeError):
        return False


def valid_input(string: str) -> bool:
    """
    Validate general input for SQL injection and encoding issues.

    Args:
        string: The input string to validate
        allow_special_chars: If True, allows quotes and special characters

    Returns:
        True if input appears safe, False otherwise
    """
    if not isinstance(string, str):
        return False

    # Empty strings are valid
    if not string:
        return True

    # Check UTF-8 validity
    if not valid_utf8(string):
        return False

    # Check for SQL injection patterns
    if DB_PATTERN.search(string):
        return False

    # Check for XSS patterns
    if XSS_PATTERN.search(string):
        return False

    # Check for path traversal
    if PATH_TRAVERSAL_PATTERN.search(string):
        return False

    return True


def valid_username(username: str, min_length: int = 3, max_length: int = 32) -> bool:
    """
    Validate a username according to security best practices.

    Args:
        username: The username to validate
        min_length: Minimum username length (default: 3)
        max_length: Maximum username length (default: 32)

    Returns:
        True if valid username, False otherwise
    """
    # Check length
    if len(username) < min_length or len(username) > max_length:
        return False

    # Check UTF-8 validity
    if not valid_utf8(username):
        return False

    # Check for SQL injection patterns
    if DB_PATTERN.search(username):
        return False

    # Check username pattern
    if not USERNAME_PATTERN.match(username):
        return False

    return True


def sanitize_string(string: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize a string by removing potentially dangerous characters.

    This removes HTML tags, script tags, and normalizes whitespace.

    Args:
        string: The string to sanitize
        max_length: Optional maximum length to truncate to

    Returns:
        Sanitized string
    """
    if not isinstance(string, str):
        return ""

    # Remove HTML/script tags
    sanitized = re.sub(r"<[^>]+>", "", string)

    # Remove control characters (except newline and tab)
    sanitized = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", sanitized)

    # Normalize whitespace
    sanitized = " ".join(sanitized.split())

    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other attacks.

    Args:
        filename: The filename to sanitize

    Returns:
        Sanitized filename safe for filesystem operations
    """
    # Remove path components
    filename = filename.split("/")[-1].split("\\")[-1]

    # Remove dangerous characters
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', "", filename)

    # Replace path traversal attempts
    filename = filename.replace("..", "")

    # Replace spaces with underscores
    filename = filename.replace(" ", "_")

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # If empty after sanitization, provide default
    if not filename:
        filename = "unnamed"

    # Limit length (filesystem limits are typically 255)
    if len(filename) > 200:
        name, _, ext = filename.rpartition(".")
        if ext and len(ext) < 10:
            filename = name[:190] + "." + ext
        else:
            filename = filename[:200]
    return filename


def is_safe_path(path: str, base_dir: str) -> bool:
    """
    Check if a path is safe (doesn't escape base directory).

    Args:
        path: The path to check
        base_dir: The base directory that should contain the path

    Returns:
        True if path is safe, False otherwise
    """
    try:
        # Resolve both paths
        safe_base = os.path.realpath(base_dir)
        safe_path = os.path.realpath(os.path.join(base_dir, path))

        # Check if resolved path is within base directory
        return safe_path.startswith(safe_base)
    except (ValueError, OSError):
        return False


def is_valid_length(string: str, min_len: int = 0, max_len: int = 1000) -> bool:
    """
    Validate string length.

    Args:
        string: The string to check
        min_len: Minimum length (inclusive)
        max_len: Maximum length (inclusive)

    Returns:
        True if length is within bounds, False otherwise
    """
    return min_len <= len(string) <= max_len


def valid_integer(
    value: Union[str, int], min_val: Optional[int] = None, max_val: Optional[int] = None
) -> bool:
    """
    Validate an integer value within optional bounds.

    Args:
        value: The value to validate (string or int)
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)

    Returns:
        True if valid integer within bounds, False otherwise
    """
    try:
        int_val = int(value)
    except (ValueError, TypeError):
        return False

    if min_val is not None and int_val < min_val:
        return False

    if max_val is not None and int_val > max_val:
        return False

    return True
