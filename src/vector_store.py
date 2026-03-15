"""
Vector store implementation using NumPy for similarity search.

This module provides a VectorStore class that uses NumPy for local vector storage
and OpenAI embeddings for generating embeddings.
It supports adding documents, similarity search, and document deletion.
"""

from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import pickle
import os
from datetime import datetime
import logging

# Import config for embedding model
from src.config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class VectorStoreError(Exception):
    """Base exception for vector store errors."""
    pass


class VectorStore:
    """
    Vector store for document embeddings using NumPy.
    
    Uses OpenAI embeddings and brute-force cosine similarity via NumPy.
    For the typical document count (~300), this is fast enough and avoids
    the FAISS native dependency that fails on some cloud platforms.
    """
    
    def __init__(self, embedding_model: Optional[OpenAIEmbeddings] = None):
        """Initialize the vector store."""
        self.embedding_model = embedding_model or OpenAIEmbeddings(
            model=EMBEDDING_MODEL
        )
        self.embeddings: Optional[np.ndarray] = None  # shape (n, dim)
        self.documents: List[Document] = []
        self.doc_ids: List[str] = []

    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store with retry logic."""
        if not documents:
            return
            
        try:
            texts = [doc.page_content for doc in documents]
            
            max_retries = 3
            embeddings = None
            
            for attempt in range(max_retries):
                try:
                    embeddings = self.embedding_model.embed_documents(texts)
                    break
                except Exception as e:
                    logger.warning(
                        f"Embedding generation failed (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1 * (2 ** attempt))
                    else:
                        raise VectorStoreError(
                            f"Failed to generate embeddings after {max_retries} attempts"
                        ) from e
            
            new_array = np.array(embeddings, dtype=np.float32)
            
            if self.embeddings is not None:
                self.embeddings = np.vstack([self.embeddings, new_array])
            else:
                self.embeddings = new_array
            
            for i, doc in enumerate(documents):
                if "timestamp" not in doc.metadata:
                    doc.metadata["timestamp"] = datetime.now().isoformat()
                doc_id = doc.metadata.get("id", f"doc_{len(self.documents) + i}")
                doc.metadata["id"] = doc_id
                self.documents.append(doc)
                self.doc_ids.append(doc_id)
                
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(f"Failed to add documents: {e}") from e

    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """Search for similar documents using cosine similarity."""
        try:
            if self.embeddings is None or len(self.documents) == 0:
                raise VectorStoreError("Vector store is empty or not initialized")
            
            max_retries = 3
            query_embedding = None
            
            for attempt in range(max_retries):
                try:
                    query_embedding = self.embedding_model.embed_query(query)
                    break
                except Exception as e:
                    logger.warning(
                        f"Query embedding failed (attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1 * (2 ** attempt))
                    else:
                        raise VectorStoreError(
                            f"Failed to generate query embedding after {max_retries} attempts"
                        ) from e
            
            query_vec = np.array(query_embedding, dtype=np.float32)
            
            # Cosine similarity
            norms = np.linalg.norm(self.embeddings, axis=1)
            q_norm = np.linalg.norm(query_vec)
            # Avoid division by zero
            safe_norms = np.where(norms == 0, 1.0, norms)
            similarities = self.embeddings @ query_vec / (safe_norms * q_norm)
            
            k = min(k, len(self.documents))
            top_indices = np.argsort(similarities)[-k:][::-1]
            
            return [self.documents[i] for i in top_indices]
            
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(f"Similarity search failed: {e}") from e

    def similarity_search_with_score(
        self, query: str, k: int = 5
    ) -> List[Tuple[Document, float]]:
        """Search for similar documents with similarity scores."""
        try:
            if self.embeddings is None or len(self.documents) == 0:
                raise VectorStoreError("Vector store is empty or not initialized")
            
            query_embedding = self.embedding_model.embed_query(query)
            query_vec = np.array(query_embedding, dtype=np.float32)
            
            norms = np.linalg.norm(self.embeddings, axis=1)
            q_norm = np.linalg.norm(query_vec)
            safe_norms = np.where(norms == 0, 1.0, norms)
            similarities = self.embeddings @ query_vec / (safe_norms * q_norm)
            
            k = min(k, len(self.documents))
            top_indices = np.argsort(similarities)[-k:][::-1]
            
            return [(self.documents[i], float(similarities[i])) for i in top_indices]
            
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(f"Similarity search with score failed: {e}") from e

    def delete_documents(self, ids: List[str]) -> None:
        """Delete documents and rebuild embeddings array."""
        try:
            if not ids:
                return
            
            ids_to_delete = set(ids)
            keep_indices = []
            
            for i, doc in enumerate(self.documents):
                if doc.metadata.get("id", "") not in ids_to_delete:
                    keep_indices.append(i)
            
            self.documents = [self.documents[i] for i in keep_indices]
            self.doc_ids = [self.doc_ids[i] for i in keep_indices]
            
            if keep_indices and self.embeddings is not None:
                self.embeddings = self.embeddings[keep_indices]
            else:
                self.embeddings = None
                
        except Exception as e:
            raise VectorStoreError(f"Failed to delete documents: {e}") from e

    def save(self, directory: str) -> None:
        """Save the vector store to disk."""
        try:
            os.makedirs(directory, exist_ok=True)
            
            # Save embeddings as .npy
            if self.embeddings is not None:
                np.save(os.path.join(directory, "embeddings.npy"), self.embeddings)
            
            # Save documents and metadata
            with open(os.path.join(directory, "documents.pkl"), "wb") as f:
                pickle.dump({
                    "documents": self.documents,
                    "doc_ids": self.doc_ids
                }, f)
                
        except Exception as e:
            raise VectorStoreError(f"Failed to save vector store: {e}") from e

    def load(self, directory: str) -> None:
        """Load the vector store from disk.
        
        Supports both new format (embeddings.npy) and legacy FAISS format (faiss.index).
        """
        try:
            # Try new numpy format first
            npy_path = os.path.join(directory, "embeddings.npy")
            faiss_path = os.path.join(directory, "faiss.index")
            
            if os.path.exists(npy_path):
                self.embeddings = np.load(npy_path)
            elif os.path.exists(faiss_path):
                # Legacy FAISS format — reconstruct embeddings from the index
                try:
                    import faiss
                    index = faiss.read_index(faiss_path)
                    n = index.ntotal
                    if n > 0:
                        self.embeddings = np.zeros((n, index.d), dtype=np.float32)
                        index.reconstruct_n(0, n, self.embeddings)
                    logger.info(f"Migrated {n} vectors from legacy FAISS index")
                except ImportError:
                    logger.warning(
                        "Found faiss.index but faiss-cpu not installed. "
                        "Run the ingestion pipeline to regenerate embeddings.npy"
                    )
            
            # Load documents
            docs_path = os.path.join(directory, "documents.pkl")
            if os.path.exists(docs_path):
                with open(docs_path, "rb") as f:
                    data = pickle.load(f)
                    self.documents = data["documents"]
                    self.doc_ids = data["doc_ids"]
            else:
                raise VectorStoreError(f"Documents file not found: {docs_path}")
                
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(f"Failed to load vector store: {e}") from e

    def __len__(self) -> int:
        """Return the number of documents in the vector store."""
        return len(self.documents)
