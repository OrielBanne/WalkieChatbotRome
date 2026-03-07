"""
Vector store implementation using FAISS for efficient similarity search.

This module provides a VectorStore class that uses FAISS (Facebook AI Similarity Search)
for local vector storage and OpenAI embeddings for generating embeddings.
It supports adding documents, similarity search, and document deletion.
"""

from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import faiss
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import pickle
import os
from datetime import datetime

# Import config for embedding model
from src.config import EMBEDDING_MODEL


class VectorStoreError(Exception):
    """Base exception for vector store errors."""
    pass


class VectorStore:
    """
    Vector store for document embeddings using FAISS.
    
    This class manages document embeddings and provides efficient similarity search
    using FAISS indexing. It uses OpenAI embeddings for generating embeddings.
    
    Attributes:
        embedding_model: OpenAI embeddings model
        index: FAISS index for similarity search
        documents: List of stored documents
        doc_ids: List of document IDs corresponding to index positions
    """
    
    def __init__(self, embedding_model: Optional[OpenAIEmbeddings] = None):
        """
        Initialize the vector store.
        
        Args:
            embedding_model: Optional OpenAI embeddings model. If None, creates default from config.
        """
        self.embedding_model = embedding_model or OpenAIEmbeddings(
            model=EMBEDDING_MODEL
        )
        # Dimension depends on the model - text-embedding-3-small is 1536, ada-002 is 1536
        self.dimension = 1536
        self.index: Optional[faiss.IndexFlatL2] = None
        self.documents: List[Document] = []
        self.doc_ids: List[str] = []
        
    def _ensure_index_exists(self) -> None:
        """Create FAISS index if it doesn't exist."""
        if self.index is None:
            self.index = faiss.IndexFlatL2(self.dimension)
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the vector store with error handling.
        
        Args:
            documents: List of Document objects to add
            
        Raises:
            VectorStoreError: If embedding generation or indexing fails
        """
        if not documents:
            return
            
        try:
            self._ensure_index_exists()
            
            # Generate embeddings for all documents with retry logic
            texts = [doc.page_content for doc in documents]
            
            max_retries = 3
            embeddings = None
            
            for attempt in range(max_retries):
                try:
                    embeddings = self.embedding_model.embed_documents(texts)
                    break
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Embedding generation failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                    )
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1 * (2 ** attempt))  # Exponential backoff
                    else:
                        raise VectorStoreError(f"Failed to generate embeddings after {max_retries} attempts") from e
            
            # Convert to numpy array and add to FAISS index
            embeddings_array = np.array(embeddings, dtype=np.float32)
            self.index.add(embeddings_array)
            
            # Store documents and generate IDs
            for i, doc in enumerate(documents):
                # Add metadata
                if "timestamp" not in doc.metadata:
                    doc.metadata["timestamp"] = datetime.now().isoformat()
                
                # Generate document ID if not present
                doc_id = doc.metadata.get("id", f"doc_{len(self.documents) + i}")
                doc.metadata["id"] = doc_id
                
                self.documents.append(doc)
                self.doc_ids.append(doc_id)
                
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(f"Failed to add documents: {str(e)}") from e
    
    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """
        Search for similar documents using cosine similarity with retry logic.
        
        Args:
            query: Query text to search for
            k: Number of results to return
            
        Returns:
            List of most similar documents
            
        Raises:
            VectorStoreError: If vector store is unavailable or search fails
        """
        try:
            if self.index is None or len(self.documents) == 0:
                raise VectorStoreError("Vector store is empty or not initialized")
            
            # Generate query embedding with retry logic
            max_retries = 3
            query_embedding = None
            
            for attempt in range(max_retries):
                try:
                    query_embedding = self.embedding_model.embed_query(query)
                    break
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Query embedding failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                    )
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1 * (2 ** attempt))  # Exponential backoff
                    else:
                        raise VectorStoreError(f"Failed to generate query embedding after {max_retries} attempts") from e
            
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # Search FAISS index
            k = min(k, len(self.documents))  # Don't request more than available
            distances, indices = self.index.search(query_vector, k)
            
            # Return corresponding documents
            results = []
            for idx in indices[0]:
                if 0 <= idx < len(self.documents):
                    results.append(self.documents[idx])
            
            return results
            
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(f"Similarity search failed: {str(e)}") from e
    
    def similarity_search_with_score(
        self, query: str, k: int = 5
    ) -> List[Tuple[Document, float]]:
        """
        Search for similar documents with similarity scores.
        
        Args:
            query: Query text to search for
            k: Number of results to return
            
        Returns:
            List of tuples (document, similarity_score)
            
        Raises:
            VectorStoreError: If vector store is unavailable or search fails
        """
        try:
            if self.index is None or len(self.documents) == 0:
                raise VectorStoreError("Vector store is empty or not initialized")
            
            # Generate query embedding
            query_embedding = self.embedding_model.embed_query(query)
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # Search FAISS index
            k = min(k, len(self.documents))
            distances, indices = self.index.search(query_vector, k)
            
            # Return documents with scores
            # FAISS returns L2 distances, convert to similarity scores
            # Lower distance = higher similarity
            results = []
            for distance, idx in zip(distances[0], indices[0]):
                if 0 <= idx < len(self.documents):
                    # Convert L2 distance to similarity score (0-1 range)
                    # Using exponential decay: similarity = exp(-distance)
                    similarity = float(np.exp(-distance))
                    results.append((self.documents[idx], similarity))
            
            return results
            
        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(
                f"Similarity search with score failed: {str(e)}"
            ) from e
    
    def delete_documents(self, ids: List[str]) -> None:
        """
        Delete documents from the vector store.
        
        Note: FAISS doesn't support efficient deletion, so this rebuilds the index
        without the deleted documents.
        
        Args:
            ids: List of document IDs to delete
            
        Raises:
            VectorStoreError: If deletion fails
        """
        try:
            if not ids:
                return
            
            # Find documents to keep
            ids_to_delete = set(ids)
            documents_to_keep = []
            
            for doc in self.documents:
                doc_id = doc.metadata.get("id", "")
                if doc_id not in ids_to_delete:
                    documents_to_keep.append(doc)
            
            # Rebuild index with remaining documents
            self.index = None
            self.documents = []
            self.doc_ids = []
            
            if documents_to_keep:
                self.add_documents(documents_to_keep)
                
        except Exception as e:
            raise VectorStoreError(f"Failed to delete documents: {str(e)}") from e
    
    def save(self, directory: str) -> None:
        """
        Save the vector store to disk.
        
        Args:
            directory: Directory path to save the vector store
            
        Raises:
            VectorStoreError: If saving fails
        """
        try:
            os.makedirs(directory, exist_ok=True)
            
            # Save FAISS index
            if self.index is not None:
                index_path = os.path.join(directory, "faiss.index")
                faiss.write_index(self.index, index_path)
            
            # Save documents and metadata
            docs_path = os.path.join(directory, "documents.pkl")
            with open(docs_path, "wb") as f:
                pickle.dump({
                    "documents": self.documents,
                    "doc_ids": self.doc_ids
                }, f)
                
        except Exception as e:
            raise VectorStoreError(f"Failed to save vector store: {str(e)}") from e
    
    def load(self, directory: str) -> None:
        """
        Load the vector store from disk.
        
        Args:
            directory: Directory path containing the saved vector store
            
        Raises:
            VectorStoreError: If loading fails
        """
        try:
            # Load FAISS index
            index_path = os.path.join(directory, "faiss.index")
            if os.path.exists(index_path):
                self.index = faiss.read_index(index_path)
            
            # Load documents and metadata
            docs_path = os.path.join(directory, "documents.pkl")
            if os.path.exists(docs_path):
                with open(docs_path, "rb") as f:
                    data = pickle.load(f)
                    self.documents = data["documents"]
                    self.doc_ids = data["doc_ids"]
            else:
                raise VectorStoreError(f"Documents file not found: {docs_path}")
                
        except Exception as e:
            raise VectorStoreError(f"Failed to load vector store: {str(e)}") from e
    
    def __len__(self) -> int:
        """Return the number of documents in the vector store."""
        return len(self.documents)
