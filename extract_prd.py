import sys

import docx


def extract_text(file_path):
    try:
        doc = docx.Document(file_path)
        text = []
        for paragraph in doc.paragraphs:
            text.append(paragraph.text)
        return "\n".join(text)
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_prd.py <file_path>")
        sys.exit(1)
    print(extract_text(sys.argv[1]))
