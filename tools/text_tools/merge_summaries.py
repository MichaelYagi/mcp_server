def merge_summaries(summaries: list[str], style: str = "medium"):
    merged = "\n".join(f"- {s}" for s in summaries)
    return {"merged": merged, "style": style}
