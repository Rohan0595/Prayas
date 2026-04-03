"""
Document upload endpoint — accepts PDF and plain text files,
extracts text, and indexes into the current user's FAISS store.
"""
import io
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from app.rag.vector_store import get_user_store
from app.core.config import settings
from app.core.deps import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


class UploadResponse(BaseModel):
    filename: str
    chunks_added: int
    total_chunks: int
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """
    Upload a PDF or TXT file for RAG indexing.
    Documents are scoped to the currently authenticated user.
    """
    if file.content_type not in ("application/pdf", "text/plain"):
        raise HTTPException(
            status_code=415,
            detail="Only PDF and plain text files are supported.",
        )

    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    # Extract text
    if file.content_type == "application/pdf":
        text = _extract_pdf(raw, file.filename)
    else:
        text = raw.decode("utf-8", errors="replace")

    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file.")

    store = get_user_store(user.id)
    chunks_added = store.add_document(text, filename=file.filename)

    return UploadResponse(
        filename=file.filename,
        chunks_added=chunks_added,
        total_chunks=store.document_count,
        message=f"Successfully indexed {chunks_added} chunks from '{file.filename}'.",
    )


def _extract_pdf(raw_bytes: bytes, filename: str) -> str:
    """Extract text from a PDF using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=raw_bytes, filetype="pdf")
        pages = [page.get_text() for page in doc]
        return "\n".join(pages)
    except ImportError:
        try:
            from pdfminer.high_level import extract_text_to_fp
            from pdfminer.layout import LAParams

            output = io.StringIO()
            extract_text_to_fp(io.BytesIO(raw_bytes), output, laparams=LAParams())
            return output.getvalue()
        except ImportError:
            raise HTTPException(
                status_code=500,
                detail="PDF parsing requires PyMuPDF or pdfminer. Run: pip install pymupdf",
            )


@router.get("/upload/status")
async def upload_status(user=Depends(get_current_user)):
    """Return the document count for the current user only."""
    store = get_user_store(user.id)
    return {
        "indexed_chunks": store.document_count,
        "rag_active": store.document_count > 0,
    }


@router.get("/upload/documents")
async def list_documents(user=Depends(get_current_user)):
    """List documents indexed by the current user."""
    store = get_user_store(user.id)
    return store.list_documents()


@router.delete("/upload/documents/{filename}")
async def remove_document(filename: str, user=Depends(get_current_user)):
    """Remove a document from the current user's FAISS index."""
    store = get_user_store(user.id)
    removed = store.remove_document(filename)
    if removed == 0:
        raise HTTPException(status_code=404, detail="Document not found in index")
    return {"message": f"Successfully removed '{filename}' ({removed} chunks)"}
