"""
FAISS-based vector store for document retrieval (RAG).
Each user gets their own isolated FAISS index stored in a subdirectory.
"""
import os
import pickle
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import numpy as np
from app.core.config import settings

_faiss = None
_model = None
_store_cache: Dict[str, "VectorStore"] = {}  # user_id -> VectorStore


def _get_faiss():
    global _faiss
    if _faiss is None:
        import faiss as faiss_lib
        _faiss = faiss_lib
    return _faiss


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


class VectorStore:
    """Per-user FAISS vector store with persist/load support."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.index = None
        self.documents: List[str] = []
        self.metadata: List[dict] = []
        # Each user gets their own subdirectory
        self.index_path = Path(settings.FAISS_INDEX_PATH) / user_id
        self.dim = 384  # all-MiniLM-L6-v2 produces 384-dim vectors

    def initialize(self):
        """Load existing user index or create a fresh one."""
        self.index_path.mkdir(parents=True, exist_ok=True)
        idx_file = self.index_path / "index.faiss"
        docs_file = self.index_path / "docs.pkl"

        faiss = _get_faiss()
        if idx_file.exists() and docs_file.exists():
            self.index = faiss.read_index(str(idx_file))
            with open(docs_file, "rb") as f:
                data = pickle.load(f)
                self.documents = data["documents"]
                self.metadata = data["metadata"]
        else:
            self.index = faiss.IndexFlatL2(self.dim)

    def _save(self):
        faiss = _get_faiss()
        faiss.write_index(self.index, str(self.index_path / "index.faiss"))
        with open(self.index_path / "docs.pkl", "wb") as f:
            pickle.dump({"documents": self.documents, "metadata": self.metadata}, f)

    def _chunk_text(self, text: str) -> List[str]:
        size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i : i + size])
            chunks.append(chunk)
            i += size - overlap
        return chunks

    def add_document(self, text: str, filename: str = "unknown") -> int:
        model = _get_model()
        chunks = self._chunk_text(text)
        if not chunks:
            return 0

        embeddings = model.encode(chunks, show_progress_bar=False)
        embeddings = np.array(embeddings, dtype="float32")

        self.index.add(embeddings)
        for i, chunk in enumerate(chunks):
            self.documents.append(chunk)
            self.metadata.append({"filename": filename, "chunk": i})

        self._save()
        return len(chunks)

    def list_documents(self) -> List[dict]:
        counts: dict = {}
        for meta in self.metadata:
            fname = meta["filename"]
            counts[fname] = counts.get(fname, 0) + 1
        return [{"filename": k, "chunks": v} for k, v in counts.items()]

    def remove_document(self, filename: str) -> int:
        keep_indices = [i for i, m in enumerate(self.metadata) if m["filename"] != filename]
        removed = len(self.metadata) - len(keep_indices)
        if removed == 0:
            return 0

        self.documents = [self.documents[i] for i in keep_indices]
        self.metadata = [self.metadata[i] for i in keep_indices]

        faiss = _get_faiss()
        self.index = faiss.IndexFlatL2(self.dim)
        if self.documents:
            model = _get_model()
            embeddings = model.encode(self.documents, show_progress_bar=False)
            embeddings = np.array(embeddings, dtype="float32")
            self.index.add(embeddings)

        self._save()
        return removed

    def search(self, query: str, k: int = None) -> List[Tuple[str, dict, float]]:
        if not self.documents:
            return []
        k = k or settings.TOP_K_RESULTS
        model = _get_model()
        query_vec = model.encode([query], show_progress_bar=False)
        query_vec = np.array(query_vec, dtype="float32")

        actual_k = min(k, len(self.documents))
        distances, indices = self.index.search(query_vec, actual_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.documents):
                results.append((self.documents[idx], self.metadata[idx], float(dist)))
        return results

    def get_context_for_query(self, query: str) -> str:
        results = self.search(query)
        if not results:
            return ""
        parts = ["[Relevant context from uploaded documents]\n"]
        for text, meta, dist in results:
            parts.append(f"--- Source: {meta['filename']} (chunk {meta['chunk']}) ---\n{text}")
        return "\n\n".join(parts)

    @property
    def document_count(self) -> int:
        return len(self.documents)


# ── Per-user store accessor ────────────────────────────────────────────────────

def get_user_store(user_id: str) -> VectorStore:
    """Return a cached, initialized VectorStore for the given user_id."""
    if user_id not in _store_cache:
        store = VectorStore(user_id)
        store.initialize()
        _store_cache[user_id] = store
    return _store_cache[user_id]


# Legacy singleton kept for startup compatibility (used in main.py lifespan)
class _LegacyStub:
    """No-op stub so existing main.py lifespan call doesn't error."""
    def initialize(self):
        pass
    document_count = 0

vector_store = _LegacyStub()
