from __future__ import annotations

import uuid
from pathlib import Path
from typing import List

import chromadb
from chromadb.config import Settings

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
CHROMA_DIR = BASE_DIR / "chroma_pdfs"


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
    return client.get_or_create_collection(PDF_COLLECTION_NAME)


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



