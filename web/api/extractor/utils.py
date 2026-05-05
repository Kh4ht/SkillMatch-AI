def clean_text(text):
    text = text.replace("\n", " ")
    text = " ".join(text.split())
    return text


def extract_section(text, section_name):
    lines = text.split("\n")
    capture = False
    section = []

    for line in lines:
        if section_name.lower() in line.lower():
            capture = True
            continue
        elif capture and line.strip() == "":
            break
        if capture:
            section.append(line)

    return " ".join(section)