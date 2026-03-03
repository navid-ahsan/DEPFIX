"""Text processing and cleaning utilities."""

import re


def clean_scraped_content(text: str) -> str:
    """
    Cleans raw text to remove common code artifacts.
    
    Removes:
    - Shell prompts (>, >>>, $)
    - Jupyter notebook cell numbers
    - Copy buttons and other UI artifacts
    - Excessive whitespace
    
    Args:
        text: Raw text content to clean
        
    Returns:
        Cleaned text with artifacts removed
    """
    # Remove shell prompts and cell numbers
    text = re.sub(r'^\s*[\$>\>]{1,3}\s?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^In \[\d+\]:\s?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Out\[\d+\]:\s?', '', text, flags=re.MULTILINE)
    
    # Remove UI elements
    text = re.sub(r'^\s*Copy\s*$', '', text, flags=re.MULTILINE)
    
    # Normalize whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text.strip()


def normalize_text(text: str, max_length: int = None) -> str:
    """
    Normalize text by removing extra whitespace and optionally limiting length.
    
    Args:
        text: Text to normalize
        max_length: Optional maximum length (truncates if exceeded)
        
    Returns:
        Normalized text
    """
    # Remove extra spaces
    text = ' '.join(text.split())
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length].rstrip() + '...'
    
    return text
