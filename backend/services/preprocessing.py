import re

def clean_text(text: str) -> str:
    text = text.lower()                                         # lowercases all the words
    text = re.sub(r"\s+", " ", text)               # replaces multiple spaces with single space
    text = re.sub(r"[^a-z0-9., ]", "", text)       # Removes all non-alphanumeric characters
    return text.strip()
