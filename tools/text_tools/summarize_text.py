from .utils import load_text
from .split_text import split_text

def summarize_text(text: str | None = None,
                   file_path: str | None = None,
                   style: str = "medium"):

    full_text = load_text(text, file_path)
    chunks = split_text(full_text)["chunks"]

    return {
        "chunks": chunks,
        "style": style
    }
