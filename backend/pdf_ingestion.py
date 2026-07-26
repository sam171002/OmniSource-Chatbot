from __future__ import annotations
import os
import uuid
from pathlib import Path
from typing import List
import chromadb
from chromadb.config import Settings
from chromadb.api.types import Documents, EmbeddingFunction
import google.generativeai as genai
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
CHROMA_DIR = BASE_DIR / "chroma_pdfs"


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Calls Gemini's embedding API directly, bypassing chromadb's built-in
    Google wrapper (which has a version-compatibility bug)."""

    def __init__(self, api_key: str, model_name: str = "models/gemini-embedding-001"):
        genai.configure(api_key=api_key)
        self.model_name = model_name

    def __call__(self, input: Documents):
        response = genai.embed_content(
            model=self.model_name,
            content=list(input),
            task_type="RETRIEVAL_DOCUMENT",
        )
        return response["embedding"]


def get_gemini_embedding_function():
    return GeminiEmbeddingFunction(api_key=os.getenv("GEMINI_API_KEY"))


def get_pdf_client():
    CHROMA_DIR.mkdir(exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(allow_reset=False),
    )
    return client


PDF_COLLECTION_NAME = "pdf_docs"


def get_pdf_collection():
    client = get_pdf_client()
    return client.get_or_create_collection(
        PDF_COLLECTION_NAME,
        embedding_function=get_gemini_embedding_function(),
    )


def ingest_pdfs(pdf_paths: List[Path]) -> int:
    """
    Ingest PDFs into dedicated Chroma collection.
    Returns number of chunks added.
    """
    collection = get_pdf_collection()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
    )
    total_chunks = 0
    for pdf_path in pdf_paths:
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        docs = text_splitter.split_documents(pages)
        documents = [d.page_content for d in docs]
        metadatas = []
        ids = []
        for d in docs:
            meta = d.metadata or {}
            metadatas.append(
                {
                    "source": "pdf",
                    "file_name": pdf_path.name,
                    "page": meta.get("page", meta.get("page_number")),
                }
            )
            ids.append(str(uuid.uuid4()))
        if documents:
            collection.add(documents=documents, metadatas=metadatas, ids=ids)
            total_chunks += len(documents)
    return total_chunks


def pdf_semantic_search(query: str, k: int = 5):
    collection = get_pdf_collection()
    result = collection.query(query_texts=[query], n_results=k)
    return result
