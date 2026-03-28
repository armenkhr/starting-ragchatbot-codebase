# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Setup** (requires Python 3.13+, [uv](https://astral.sh/uv)):
```bash
uv sync
cp .env.example .env   # then add ANTHROPIC_API_KEY
```

**Run the server:**
```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

App at `http://localhost:8000` · API docs at `http://localhost:8000/docs`

**Re-ingest all docs** (needed after changing embedding model or doc format):
```bash
# clear_existing=True is passed via the startup logic — to force re-ingest,
# call vector_store.clear_all_data() then restart the server
```

**Add a dependency:**
```bash
uv add <package>
```

## Architecture

This is a full-stack RAG (Retrieval-Augmented Generation) chatbot. The server is started from the `backend/` directory, so all relative paths inside backend code are relative to `backend/` (e.g. `../docs`, `./chroma_db`).

### Request flow

```
Browser (frontend/) → POST /api/query → FastAPI (app.py)
  → RAGSystem.query()
      → SessionManager (conversation history)
      → AIGenerator → Claude API call #1 (with tool definition)
          → Claude decides to call search_course_content tool
          → CourseSearchTool → VectorStore.search() → ChromaDB
          → Claude API call #2 (with chunk results)
          → returns final answer
      → SessionManager (save exchange)
  → JSON response → browser renders markdown via marked.js
```

### Key components

- **`rag_system.py`** — orchestrator; the only file that touches all other components. Entry point for all queries.
- **`ai_generator.py`** — wraps Anthropic SDK. Implements the two-shot tool-use pattern: first call gets a `tool_use` stop reason, tool is executed externally, second call gets the final answer.
- **`vector_store.py`** — wraps ChromaDB with two collections: `course_catalog` (one document per course, used for fuzzy course-name resolution) and `course_content` (one document per chunk, used for semantic search). Course title is the document ID in `course_catalog`.
- **`document_processor.py`** — parses structured `.txt` course files and splits lesson text into sentence-aware overlapping chunks (800 chars, 100 overlap).
- **`search_tools.py`** — defines the `search_course_content` Anthropic tool and `ToolManager` registry. `CourseSearchTool` stores `last_sources` after each search so the API can return source attribution.
- **`session_manager.py`** — in-memory sessions (lost on restart). Keeps the last 2 exchanges; formatted as plain text and injected into Claude's system prompt.
- **`config.py`** — single `Config` dataclass; all tuneable constants live here (chunk size, model, max history, etc.).

### Course document format

Files in `docs/` must follow this structure for `DocumentProcessor` to parse them correctly:

```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <title>
Lesson Link: <url>
<lesson text...>

Lesson 1: <title>
...
```

Course title is used as the unique ID — duplicate titles are skipped on startup.

### Data models (`models.py`)

`Course` → contains `List[Lesson]` → `CourseChunk` is the unit stored in ChromaDB. All three are Pydantic models.

### API endpoints

- `POST /api/query` — accepts `{query, session_id?}`, returns `{answer, sources, session_id}`
- `GET /api/courses` — returns `{total_courses, course_titles[]}`

### Adding new tools

Subclass `Tool` in `search_tools.py`, implement `get_tool_definition()` (Anthropic tool schema) and `execute(**kwargs)`, then register with `tool_manager.register_tool(your_tool)` in `RAGSystem.__init__`. The `ToolManager` handles routing by tool name.

### Embedding

`SentenceTransformer("all-MiniLM-L6-v2")` runs locally (no API call). The same model must be used at both ingest and query time — changing it requires clearing ChromaDB and re-ingesting all docs (`vector_store.clear_all_data()`).
