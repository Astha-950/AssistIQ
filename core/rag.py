from llama_index.core import VectorStoreIndex, Document
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.settings import Settings
import chromadb
import pdfplumber
import os
from pathlib import Path

# use free local embeddings
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"
)
Settings.llm = None  # we use groq separately

# chromadb setup
CHROMA_PATH = Path(__file__).parent.parent / "vector_store"

def get_chroma_collection(user_id):
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    # each user gets their own collection
    collection = client.get_or_create_collection(f"user_{user_id}")
    return client, collection

def add_document_to_index(user_id, text, filename, source="pdf"):
    client, collection = get_chroma_collection(user_id)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # chunk text into smaller pieces
    chunks = chunk_text(text)
    documents = [
        Document(
            text=chunk,
            metadata={"filename": filename, "source": source}
        )
        for chunk in chunks
    ]

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context
    )
    return True

def search_index(user_id, query, top_k=3):
    try:
        client, collection = get_chroma_collection(user_id)

        # check if collection has any data
        if collection.count() == 0:
            return None

        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context
        )
        retriever = index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)

        if not nodes:
            return None

        # combine retrieved chunks
        context = "\n\n".join([node.text for node in nodes])
        return context

    except Exception as e:
        return None

def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
    return chunks

def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text