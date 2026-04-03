# ✦ Omni Assistant

A production-ready, multi-model AI assistant powered by [OpenRouter](https://openrouter.ai).
Features streaming responses, RAG (document Q&A), an agent loop with tools, and persistent chat history.

---

## Features

| Feature | Detail |
|---|---|
| **Multi-model routing** | Auto-selects DeepSeek Coder for code, Claude Sonnet for reasoning, GPT-4o-mini for chat |
| **Streaming** | Server-Sent Events (SSE) — tokens appear as they're generated |
| **RAG** | Upload PDF/TXT → FAISS index → relevant chunks injected into context |
| **Agent loop** | LLM can call tools (calculator, web search, clock) in a multi-step loop |
| **Chat memory** | SQLite-backed sessions with full message history |
| **Model selector** | Pick any model manually or use auto-routing |

---

## Project Structure

```
omni-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── api/
│   │   │   ├── chat.py        # /chat and /chat/stream endpoints
│   │   │   ├── upload.py      # /upload endpoint
│   │   │   └── sessions.py    # /sessions CRUD
│   │   ├── core/
│   │   │   └── config.py      # Settings + model routing logic
│   │   ├── models/
│   │   │   └── openrouter.py  # OpenRouter API client (streaming + retry)
│   │   ├── memory/
│   │   │   └── store.py       # SQLite chat memory
│   │   ├── rag/
│   │   │   └── vector_store.py # FAISS vector store
│   │   └── tools/
│   │       ├── executor.py    # Tool definitions + implementations
│   │       └── agent.py       # Agent loop
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx            # Root component — layout + state
    │   ├── components/
    │   │   ├── Message.jsx    # Chat bubble with markdown + syntax highlighting
    │   │   ├── Sidebar.jsx    # Session list
    │   │   └── UploadModal.jsx # Document upload UI
    │   ├── services/
    │   │   └── api.js         # All backend calls incl. SSE streaming
    │   └── styles/
    │       └── main.css       # Full UI theme
    ├── index.html
    ├── vite.config.js
    └── package.json
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- An [OpenRouter API key](https://openrouter.ai/keys)

### 2. Backend setup

```bash
cd omni-assistant/backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY=sk-or-v1-...

# Run the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### 3. Frontend setup

```bash
cd omni-assistant/frontend

npm install
npm run dev
```

The UI will be available at `http://localhost:3000`.

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```env
# Required
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Optional overrides
MODEL_CODING=deepseek/deepseek-coder
MODEL_REASONING=anthropic/claude-3-sonnet
MODEL_DEFAULT=openai/gpt-4o-mini
```

---

## Model Routing

The backend automatically selects the best model for each query:

| Query type | Keywords detected | Model used |
|---|---|---|
| Coding | `code`, `function`, `debug`, `python`… | `deepseek/deepseek-coder` |
| Reasoning | `explain`, `analyze`, `philosophy`… | `anthropic/claude-3-sonnet` |
| General | (everything else) | `openai/gpt-4o-mini` |

The user can always override routing by selecting a model in the topbar.

---

## RAG Usage

1. Click the 📎 button in the chat input
2. Upload a PDF or .txt file (max 10 MB)
3. The document is chunked and indexed into FAISS
4. All future queries automatically retrieve the top-4 relevant chunks
5. The RAG badge in the topbar shows the indexed chunk count

---

## Agent Mode

Toggle **🔧 Agent** in the topbar to enable the agent loop.
The LLM can then call:

- **calculator** — safe math expression evaluator
- **web_search** — stub (wire to SerpAPI/Brave/Tavily in `tools/executor.py`)
- **get_current_time** — returns UTC timestamp

To add a new tool:
1. Add a function definition to `TOOL_DEFINITIONS` in `app/tools/executor.py`
2. Implement the function
3. Register it in `TOOL_MAP`

---

## API Reference

| Method | Path | Description |
|---|---|---|
| POST | `/api/chat/stream` | Streaming SSE chat |
| POST | `/api/chat` | Non-streaming chat (agent mode) |
| GET  | `/api/sessions` | List all sessions |
| POST | `/api/sessions` | Create new session |
| GET  | `/api/sessions/{id}/messages` | Get messages for a session |
| DELETE | `/api/sessions/{id}` | Delete session |
| POST | `/api/upload` | Upload document for RAG |
| GET  | `/api/upload/status` | Get indexed chunk count |
| GET  | `/health` | Health check |

---

## Extending with New Models

Any model available on OpenRouter can be used. Just add it to the `MODELS` array in `frontend/src/App.jsx`:

```js
{ value: 'google/gemini-pro', label: 'Gemini Pro' },
```

And optionally update the routing keywords in `backend/app/core/config.py`.
