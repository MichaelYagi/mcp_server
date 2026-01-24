---
name: rag_ingestion
description: >
  Ingest text or Plex media into the RAG vector database. This includes adding
  raw text, batch ingestion of Plex items, and resetting items marked as having
  no subtitles. Use this skill when the user wants to add new content to RAG.
tags:
  - rag
  - ingestion
  - embeddings
  - plex
tools:
  - rag_add_tool
  - rag_rescan_no_subtitles
---

# RAG Ingestion Skill

Use this skill when the user asks for:

- "Add this text to RAG"
- "Ingest subtitles"
- "Ingest the next batch of Plex items"
- "Re-scan items with missing subtitles"
- "Add this article to the vector database"
