from typing import Any, Dict
from rag_ingest import ingest_text_document

# Example MCP-style tool registration function;
# adjust to your MCP framework’s actual API.

async def rag_ingest_text_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP tool entry point.

    Expected args:
    {
      "doc_id": str,
      "text": str
    }
    """

    doc_id = args.get("doc_id")
    text = args.get("text")

    if not isinstance(doc_id, str) or not doc_id.strip():
        return {
            "error": "doc_id is required and must be a non-empty string"
        }

    if not isinstance(text, str) or not text.strip():
        return {
            "error": "text is required and must be a non-empty string"
        }

    result = ingest_text_document(doc_id=doc_id, text=text)

    # You can choose how much detail to expose to the LLM
    return {
        "doc_id": result["doc_id"],
        "status": result["status"],
        "num_chunks": result["num_chunks"],
        "truncated": result["truncated"],
        "limited_by": result["limited_by"],
    }
