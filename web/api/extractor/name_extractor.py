def extract_name(text):
    lines = text.split("\n")[:5]
    for line in lines:
        words = line.strip().split()
        if 1 < len(words) <= 4 and all(word.isalpha() for word in words):
            return line.strip()
    return None