"""
Unit tests for the VectorStore class.

Tests cover document addition, similarity search, deletion, persistence,
and error handling scenarios.
"""

import pytest
import tempfile
import shutil
import os
from unittest.mock import Mock, patch, MagicMock
from langchain_core.documents import Document
from src.vector_store import VectorStore, VectorStoreError


@pytest.fixture
def mock_embeddings():
    """Create a mock OpenAI embeddings model."""
    mock = Mock()
    # Return consistent embeddings for testing
    mock.embed_documents.return_value = [
        [0.1] * 1536,  # Document 1
        [0.2] * 1536,  # Document 2
        [0.3] * 1536,  # Document 3
    ]
    mock.embed_query.return_value = [0.15] * 1536  # Query embedding
    return mock


@pytest.fixture
def vector_store(mock_embeddings):
    """Create a VectorStore instance with mock embeddings."""
    return VectorStore(embedding_model=mock_embeddings)


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        Document(
            page_content="The Colosseum is an ancient amphitheater in Rome.",
            metadata={"source": "https://example.com/colosseum", "place_tags": ["landmark"]}
        ),
        Document(
            page_content="The Trevi Fountain is a famous baroque fountain.",
            metadata={"source": "https://example.com/trevi", "place_tags": ["landmark", "fountain"]}
        ),
        Document(
            page_content="Trastevere is a charming neighborhood with restaurants.",
            metadata={"source": "https://example.com/trastevere", "place_tags": ["neighborhood", "restaurant"]}
        ),
    ]


class TestVectorStoreInitialization:
    """Tests for VectorStore initialization."""
    
    def test_init_with_custom_embeddings(self, mock_embeddings):
        """Test initialization with custom embeddings model."""
        store = VectorStore(embedding_model=mock_embeddings)
        assert store.embedding_model == mock_embeddings
        assert store.dimension == 1536
        assert store.index is None
        assert len(store.documents) == 0
    
    def test_init_without_embeddings(self):
        """Test initialization creates default embeddings model."""
        with patch('src.vector_store.OpenAIEmbeddings') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            store = VectorStore()
            
            mock_class.assert_called_once_with(model="text-embedding-ada-002")
            assert store.embedding_model == mock_instance


class TestAddDocuments:
    """Tests for adding documents to the vector store."""
    
    def test_add_documents_success(self, vector_store, sample_documents):
        """Test successfully adding documents."""
        vector_store.add_documents(sample_documents)
        
        assert len(vector_store) == 3
        assert len(vector_store.documents) == 3
        assert len(vector_store.doc_ids) == 3
        assert vector_store.index is not None
    
    def test_add_documents_adds_timestamp(self, vector_store, sample_documents):
        """Test that timestamp is added to document metadata."""
        vector_store.add_documents(sample_documents)
        
        for doc in vector_store.documents:
            assert "timestamp" in doc.metadata
            assert doc.metadata["timestamp"] is not None
    
    def test_add_documents_generates_ids(self, vector_store, sample_documents):
        """Test that document IDs are generated if not present."""
        vector_store.add_documents(sample_documents)
        
        for doc in vector_store.documents:
            assert "id" in doc.metadata
            assert doc.metadata["id"] is not None
    
    def test_add_documents_preserves_existing_ids(self, vector_store):
        """Test that existing document IDs are preserved."""
        docs = [
            Document(
                page_content="Test content",
                metadata={"id": "custom_id_123"}
            )
        ]
        vector_store.add_documents(docs)
        
        assert vector_store.documents[0].metadata["id"] == "custom_id_123"
    
    def test_add_empty_documents_list(self, vector_store):
        """Test adding empty list does nothing."""
        vector_store.add_documents([])
        
        assert len(vector_store) == 0
        assert vector_store.index is None
    
    def test_add_documents_embedding_failure(self, vector_store, sample_documents):
        """Test error handling when embedding generation fails."""
        vector_store.embedding_model.embed_documents.side_effect = Exception("API Error")
        
        with pytest.raises(VectorStoreError) as exc_info:
            vector_store.add_documents(sample_documents)
        
        assert "Failed to generate embeddings" in str(exc_info.value)


class TestSimilaritySearch:
    """Tests for similarity search functionality."""
    
    def test_similarity_search_success(self, vector_store, sample_documents):
        """Test successful similarity search."""
        vector_store.add_documents(sample_documents)
        
        results = vector_store.similarity_search("ancient Rome", k=2)
        
        assert len(results) == 2
        assert all(isinstance(doc, Document) for doc in results)
    
    def test_similarity_search_k_larger_than_documents(self, vector_store, sample_documents):
        """Test search when k is larger than available documents."""
        vector_store.add_documents(sample_documents)
        
        results = vector_store.similarity_search("Rome", k=10)
        
        # Should return all available documents
        assert len(results) == 3
    
    def test_similarity_search_empty_store(self, vector_store):
        """Test search on empty vector store raises error."""
        with pytest.raises(VectorStoreError) as exc_info:
            vector_store.similarity_search("test query", k=5)
        
        assert "empty or not initialized" in str(exc_info.value)
    
    def test_similarity_search_embedding_failure(self, vector_store, sample_documents):
        """Test error handling when query embedding fails."""
        vector_store.add_documents(sample_documents)
        vector_store.embedding_model.embed_query.side_effect = Exception("API Error")
        
        with pytest.raises(VectorStoreError) as exc_info:
            vector_store.similarity_search("test query", k=5)
        
        assert "Failed to generate query embedding" in str(exc_info.value)


class TestSimilaritySearchWithScore:
    """Tests for similarity search with scores."""
    
    def test_similarity_search_with_score_success(self, vector_store, sample_documents):
        """Test successful similarity search with scores."""
        vector_store.add_documents(sample_documents)
        
        results = vector_store.similarity_search_with_score("ancient Rome", k=2)
        
        assert len(results) == 2
        assert all(isinstance(item, tuple) for item in results)
        assert all(isinstance(item[0], Document) for item in results)
        assert all(isinstance(item[1], float) for item in results)
    
    def test_similarity_search_with_score_range(self, vector_store, sample_documents):
        """Test that similarity scores are in valid range."""
        vector_store.add_documents(sample_documents)
        
        results = vector_store.similarity_search_with_score("Rome", k=3)
        
        for doc, score in results:
            assert 0.0 <= score <= 1.0
    
    def test_similarity_search_with_score_empty_store(self, vector_store):
        """Test search with score on empty store raises error."""
        with pytest.raises(VectorStoreError) as exc_info:
            vector_store.similarity_search_with_score("test", k=5)
        
        assert "empty or not initialized" in str(exc_info.value)


class TestDeleteDocuments:
    """Tests for document deletion."""
    
    def test_delete_documents_success(self, vector_store, sample_documents):
        """Test successfully deleting documents."""
        vector_store.add_documents(sample_documents)
        initial_count = len(vector_store)
        
        # Get ID of first document
        doc_id = vector_store.documents[0].metadata["id"]
        
        vector_store.delete_documents([doc_id])
        
        assert len(vector_store) == initial_count - 1
        assert all(doc.metadata["id"] != doc_id for doc in vector_store.documents)
    
    def test_delete_multiple_documents(self, vector_store, sample_documents):
        """Test deleting multiple documents at once."""
        vector_store.add_documents(sample_documents)
        
        ids_to_delete = [
            vector_store.documents[0].metadata["id"],
            vector_store.documents[1].metadata["id"]
        ]
        
        vector_store.delete_documents(ids_to_delete)
        
        assert len(vector_store) == 1
    
    def test_delete_nonexistent_document(self, vector_store, sample_documents):
        """Test deleting non-existent document doesn't affect others."""
        vector_store.add_documents(sample_documents)
        initial_count = len(vector_store)
        
        vector_store.delete_documents(["nonexistent_id"])
        
        assert len(vector_store) == initial_count
    
    def test_delete_empty_list(self, vector_store, sample_documents):
        """Test deleting empty list does nothing."""
        vector_store.add_documents(sample_documents)
        initial_count = len(vector_store)
        
        vector_store.delete_documents([])
        
        assert len(vector_store) == initial_count
    
    def test_delete_all_documents(self, vector_store, sample_documents):
        """Test deleting all documents."""
        vector_store.add_documents(sample_documents)
        
        all_ids = [doc.metadata["id"] for doc in vector_store.documents]
        vector_store.delete_documents(all_ids)
        
        assert len(vector_store) == 0


class TestPersistence:
    """Tests for saving and loading vector store."""
    
    def test_save_and_load(self, vector_store, sample_documents):
        """Test saving and loading vector store."""
        vector_store.add_documents(sample_documents)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save
            vector_store.save(tmpdir)
            
            # Verify files exist
            assert os.path.exists(os.path.join(tmpdir, "faiss.index"))
            assert os.path.exists(os.path.join(tmpdir, "documents.pkl"))
            
            # Load into new instance
            new_store = VectorStore(embedding_model=vector_store.embedding_model)
            new_store.load(tmpdir)
            
            # Verify data
            assert len(new_store) == len(vector_store)
            assert len(new_store.documents) == len(vector_store.documents)
    
    def test_save_creates_directory(self, vector_store, sample_documents):
        """Test that save creates directory if it doesn't exist."""
        vector_store.add_documents(sample_documents)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "nested", "directory")
            vector_store.save(save_path)
            
            assert os.path.exists(save_path)
    
    def test_load_missing_directory(self, vector_store):
        """Test loading from non-existent directory raises error."""
        with pytest.raises(VectorStoreError):
            vector_store.load("/nonexistent/directory")
    
    def test_save_empty_store(self, vector_store):
        """Test saving empty vector store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            vector_store.save(tmpdir)
            
            # Should create documents file even if empty
            assert os.path.exists(os.path.join(tmpdir, "documents.pkl"))


class TestErrorHandling:
    """Tests for error handling scenarios."""
    
    def test_vector_store_error_inheritance(self):
        """Test that VectorStoreError is an Exception."""
        error = VectorStoreError("test error")
        assert isinstance(error, Exception)
    
    def test_search_after_failed_add(self, vector_store, sample_documents):
        """Test that store remains usable after failed add operation."""
        # Add some documents successfully
        vector_store.add_documents([sample_documents[0]])
        
        # Try to add with failure
        vector_store.embedding_model.embed_documents.side_effect = Exception("API Error")
        with pytest.raises(VectorStoreError):
            vector_store.add_documents([sample_documents[1]])
        
        # Reset mock for search
        vector_store.embedding_model.embed_documents.side_effect = None
        vector_store.embedding_model.embed_query.return_value = [0.1] * 1536
        
        # Should still be able to search existing documents
        results = vector_store.similarity_search("test", k=1)
        assert len(results) == 1


class TestMetadata:
    """Tests for metadata handling."""
    
    def test_metadata_preserved(self, vector_store):
        """Test that document metadata is preserved."""
        docs = [
            Document(
                page_content="Test content",
                metadata={
                    "source": "https://example.com",
                    "place_tags": ["landmark", "ancient"],
                    "custom_field": "custom_value"
                }
            )
        ]
        
        vector_store.add_documents(docs)
        
        stored_doc = vector_store.documents[0]
        assert stored_doc.metadata["source"] == "https://example.com"
        assert stored_doc.metadata["place_tags"] == ["landmark", "ancient"]
        assert stored_doc.metadata["custom_field"] == "custom_value"
    
    def test_url_metadata_stored(self, vector_store, sample_documents):
        """Test that source URLs are stored in metadata."""
        vector_store.add_documents(sample_documents)
        
        for doc in vector_store.documents:
            assert "source" in doc.metadata
            assert doc.metadata["source"].startswith("https://")
    
    def test_place_tags_metadata_stored(self, vector_store, sample_documents):
        """Test that place tags are stored in metadata."""
        vector_store.add_documents(sample_documents)
        
        for doc in vector_store.documents:
            assert "place_tags" in doc.metadata
            assert isinstance(doc.metadata["place_tags"], list)


# ============================================================================
# Property-Based Tests
# ============================================================================

from hypothesis import given, strategies as st, settings


class TestPropertyBasedTests:
    """Property-based tests for VectorStore using Hypothesis."""
    
    @given(
        place_name=st.sampled_from([
            "Colosseum", "Trevi Fountain", "Pantheon", "Vatican", 
            "Spanish Steps", "Roman Forum", "Piazza Navona"
        ])
    )
    @settings(max_examples=20)
    def test_property_6_place_query_retrieval(self, place_name):
        """
        **Validates: Requirements 3.1**
        
        Property 6: Place Query Retrieval
        
        For any place name query, the RAG pipeline should retrieve at least one 
        document from the vector store that contains information about that place 
        (assuming the place exists in the knowledge base).
        """
        # Create mock embeddings that vary based on content
        # This simulates semantic similarity by using different embeddings for different places
        mock_embeddings = Mock()
        
        all_places = ["Colosseum", "Trevi Fountain", "Pantheon", "Vatican", 
                      "Spanish Steps", "Roman Forum", "Piazza Navona"]
        
        # Create embeddings that are similar when place names match
        def create_embedding(text):
            """Create a simple embedding based on which place is mentioned."""
            base = [0.1] * 1536
            for i, place in enumerate(all_places):
                if place.lower() in text.lower():
                    # Make this embedding distinct by modifying specific dimensions
                    base[i * 10] = 0.9
                    base[i * 10 + 1] = 0.8
            return base
        
        # Mock embed_documents to return different embeddings for each document
        def mock_embed_documents(texts):
            return [create_embedding(text) for text in texts]
        
        # Mock embed_query to return embedding based on query
        def mock_embed_query(text):
            return create_embedding(text)
        
        mock_embeddings.embed_documents.side_effect = mock_embed_documents
        mock_embeddings.embed_query.side_effect = mock_embed_query
        
        # Create vector store with mock embeddings
        vector_store = VectorStore(embedding_model=mock_embeddings)
        
        # Create documents for various Rome places
        documents = [
            Document(
                page_content=f"The {p} is a famous landmark in Rome. It attracts millions of visitors each year.",
                metadata={"source": f"https://example.com/{p.lower().replace(' ', '-')}", "place_tags": ["landmark"]}
            )
            for p in all_places
        ]
        
        # Add documents to vector store
        vector_store.add_documents(documents)
        
        # Query for the place
        query = f"Tell me about the {place_name}"
        results = vector_store.similarity_search(query, k=5)
        
        # Property: Should retrieve at least one document
        assert len(results) >= 1, f"Expected at least 1 document for query '{query}', got {len(results)}"
        
        # Verify that at least one result mentions the place
        place_mentioned = any(place_name.lower() in doc.page_content.lower() for doc in results)
        assert place_mentioned, f"Expected at least one document to mention '{place_name}'"
    
    @given(
        place_type=st.sampled_from(["landmark", "restaurant", "attraction", "point of interest"])
    )
    @settings(max_examples=20)
    def test_property_7_place_type_coverage(self, place_type):
        """
        **Validates: Requirements 3.2**
        
        Property 7: Place Type Coverage
        
        For any place type (landmark, restaurant, attraction, point of interest), 
        the vector store should contain documents tagged with that place type, 
        and queries for that type should retrieve relevant documents.
        """
        # Create mock embeddings
        mock_embeddings = Mock()
        mock_embeddings.embed_documents.return_value = [[0.1] * 1536] * 4
        mock_embeddings.embed_query.return_value = [0.15] * 1536
        
        # Create vector store with mock embeddings
        vector_store = VectorStore(embedding_model=mock_embeddings)
        
        # Create documents for each place type
        documents = [
            Document(
                page_content="The Colosseum is an ancient amphitheater and iconic landmark in Rome.",
                metadata={"source": "https://example.com/colosseum", "place_tags": ["landmark"]}
            ),
            Document(
                page_content="Da Enzo is a traditional Roman restaurant in Trastevere serving authentic cuisine.",
                metadata={"source": "https://example.com/da-enzo", "place_tags": ["restaurant"]}
            ),
            Document(
                page_content="The Vatican Museums are a major attraction with world-famous art collections.",
                metadata={"source": "https://example.com/vatican-museums", "place_tags": ["attraction"]}
            ),
            Document(
                page_content="The Mouth of Truth is an interesting point of interest near the Tiber River.",
                metadata={"source": "https://example.com/mouth-of-truth", "place_tags": ["point of interest"]}
            ),
        ]
        
        # Add documents to vector store
        vector_store.add_documents(documents)
        
        # Property 1: Vector store should contain documents with this place type
        docs_with_type = [doc for doc in vector_store.documents if place_type in doc.metadata.get("place_tags", [])]
        assert len(docs_with_type) >= 1, f"Expected at least 1 document tagged with '{place_type}', found {len(docs_with_type)}"
        
        # Property 2: Queries for this type should retrieve relevant documents
        query = f"Show me {place_type}s in Rome"
        results = vector_store.similarity_search(query, k=5)
        
        assert len(results) >= 1, f"Expected at least 1 result for query about '{place_type}', got {len(results)}"
        
        # Verify that at least one result has the correct place type tag
        has_correct_type = any(place_type in doc.metadata.get("place_tags", []) for doc in results)
        assert has_correct_type, f"Expected at least one result to have place_tags containing '{place_type}'"
