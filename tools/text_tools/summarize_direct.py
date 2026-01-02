def summarize_direct(text: str, style: str = "medium"):
    """
    Direct summarization request for the LLM.
    This tool does NOT summarize — it simply packages the text
    so the LLM can summarize it in a single call.
    """
    return {
        "text": text,
        "style": style
    }
