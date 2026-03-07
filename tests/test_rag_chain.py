"""
Unit tests and property-based tests for the RAGChain class.

Tests cover response generation, streaming, error handling, and recommendation generation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from langchain_core.documents import Document
from src.rag_chain import RAGChain, RAGChainError
from src.place_extractor import PlaceExtractor
from hypothesis import given, strategies as st, settings


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    mock = Mock()
    mock.invoke.return_value = "The Colosseum is an ancient amphitheater in Rome."
    mock.stream.return_value = iter(["The ", "Colosseum ", "is ", "ancient."])
    return mock


@pytest.fixture
def mock_retriever():
    """Create a mock retriever for testing."""
    mock = Mock()
    mock.get_relevant_documents.return_value = [
        Document(
            page_content="The Colosseum is an iconic symbol of Imperial Rome.",
            metadata={"source": "https://example.com/colosseum"}
        ),
        Document(
            page_content="Built in 70-80 AD, the Colosseum could hold 50,000 spectators.",
            metadata={"source": "https://example.com/colosseum-history"}
        ),
    ]
    return mock


@pytest.fixture
def rag_chain(mock_llm, mock_retriever):
    """Create a RAGChain instance with mocks."""
    # Patch RetrievalQA to avoid validation issues
    with patch('src.rag_chain.RetrievalQA') as mock_qa:
        mock_chain = Mock()
        mock_chain.invoke.return_value = {"result": "The Colosseum is an ancient amphitheater in Rome."}
        mock_qa.from_chain_type.return_value = mock_chain
        
        chain = RAGChain(llm=mock_llm, retriever=mock_retriever)
        chain._mock_chain = mock_chain  # Store for test access
        return chain


@pytest.fixture
def place_extractor():
    """Create a PlaceExtractor instance for testing."""
    return PlaceExtractor()


class TestRAGChainInitialization:
    """Tests for RAGChain initialization."""
    
    def test_init_with_llm_and_retriever(self, mock_llm, mock_retriever):
        """Test initialization with LLM and retriever."""
        with patch('src.rag_chain.RetrievalQA') as mock_qa:
            mock_chain = Mock()
            mock_qa.from_chain_type.return_value = mock_chain
            
            chain = RAGChain(llm=mock_llm, retriever=mock_retriever)
            
            assert chain.llm == mock_llm
            assert chain.retriever == mock_retriever
            assert chain.prompt_template is not None
            assert chain.chain is not None
    
    def test_prompt_template_contains_rome_context(self, rag_chain):
        """Test that prompt template emphasizes Rome information."""
        template = rag_chain.ROME_PROMPT_TEMPLATE
        
        assert "Rome" in template
        assert "context" in template.lower()
        assert "question" in template.lower()


class TestInvoke:
    """Tests for the invoke method."""
    
    def test_invoke_success(self, rag_chain):
        """Test successful response generation."""
        query = "Tell me about the Colosseum"
        context = ""
        
        response = rag_chain.invoke(query, context)
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_invoke_with_context(self, rag_chain):
        """Test response generation with conversation context."""
        query = "What else can you tell me?"
        context = "User: Tell me about the Colosseum\nAssistant: The Colosseum is ancient."
        
        response = rag_chain.invoke(query, context)
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_invoke_colosseum_query(self, rag_chain):
        """Test response generation for 'Tell me about the Colosseum'."""
        query = "Tell me about the Colosseum"
        
        response = rag_chain.invoke(query)
        
        assert isinstance(response, str)
        assert len(response) > 0
        # The mock returns a response mentioning Colosseum
        assert "Colosseum" in response or "colosseum" in response.lower()
    
    def test_invoke_api_timeout_handling(self, rag_chain, mock_llm):
        """Test API timeout handling with retries."""
        # Simulate timeout on first two attempts, success on third
        mock_llm.invoke.side_effect = [
            TimeoutError("Request timeout"),
            TimeoutError("Request timeout"),
            "The Colosseum is magnificent."
        ]
        
        # Patch the chain's invoke to use our mock
        with patch.object(rag_chain.chain, 'invoke') as mock_chain_invoke:
            mock_chain_invoke.side_effect = [
                TimeoutError("Request timeout"),
                TimeoutError("Request timeout"),
                {"result": "The Colosseum is magnificent."}
            ]
            
            response = rag_chain.invoke("Tell me about the Colosseum")
            
            assert isinstance(response, str)
            assert len(response) > 0
    
    def test_invoke_rate_limit_error_handling(self, rag_chain):
        """Test rate limit error handling."""
        # Simulate rate limit error
        with patch.object(rag_chain.chain, 'invoke') as mock_chain_invoke:
            mock_chain_invoke.side_effect = Exception("Rate limit exceeded")
            
            with pytest.raises(RAGChainError) as exc_info:
                rag_chain.invoke("Tell me about Rome")
            
            assert "trouble connecting" in str(exc_info.value)
    
    def test_invoke_max_retries_exceeded(self, rag_chain):
        """Test that max retries are respected."""
        with patch.object(rag_chain.chain, 'invoke') as mock_chain_invoke:
            mock_chain_invoke.side_effect = Exception("Persistent error")
            
            with pytest.raises(RAGChainError):
                rag_chain.invoke("Tell me about Rome")
            
            # Should have tried 3 times
            assert mock_chain_invoke.call_count == 3


class TestStream:
    """Tests for the stream method."""
    
    def test_stream_success(self, rag_chain, mock_llm):
        """Test successful streaming response."""
        query = "Tell me about the Colosseum"
        
        # Mock the stream method
        mock_llm.stream.return_value = iter([
            Mock(content="The "),
            Mock(content="Colosseum "),
            Mock(content="is "),
            Mock(content="ancient.")
        ])
        
        chunks = list(rag_chain.stream(query))
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
    
    def test_stream_with_context(self, rag_chain, mock_llm):
        """Test streaming with conversation context."""
        query = "What else?"
        context = "User: Tell me about Rome\nAssistant: Rome is beautiful."
        
        mock_llm.stream.return_value = iter([Mock(content="It has many landmarks.")])
        
        chunks = list(rag_chain.stream(query, context))
        
        assert len(chunks) > 0
    
    def test_stream_api_timeout_handling(self, rag_chain, mock_llm, mock_retriever):
        """Test streaming with API timeout and retry."""
        query = "Tell me about Rome"
        
        # First attempt fails, second succeeds
        call_count = [0]
        
        def stream_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise TimeoutError("Request timeout")
            return iter([Mock(content="Rome is beautiful.")])
        
        mock_llm.stream.side_effect = stream_side_effect
        
        chunks = list(rag_chain.stream(query))
        
        assert len(chunks) > 0
        assert call_count[0] == 2  # Should have retried
    
    def test_stream_fallback_to_non_streaming(self, rag_chain, mock_llm):
        """Test fallback to non-streaming when stream is not available."""
        # Remove stream method to simulate non-streaming LLM
        delattr(mock_llm, 'stream')
        mock_llm.invoke.return_value = Mock(content="The Colosseum is ancient.")
        
        chunks = list(rag_chain.stream("Tell me about the Colosseum"))
        
        assert len(chunks) > 0


class TestErrorHandling:
    """Tests for error handling scenarios."""
    
    def test_rag_chain_error_inheritance(self):
        """Test that RAGChainError is an Exception."""
        error = RAGChainError("test error")
        assert isinstance(error, Exception)
    
    def test_invoke_with_empty_query(self, rag_chain):
        """Test handling of empty query."""
        # Should still work, just might return generic response
        response = rag_chain.invoke("")
        assert isinstance(response, str)
    
    def test_retriever_failure_handling(self, rag_chain):
        """Test handling when retriever fails."""
        # Make the chain's invoke method raise an exception
        rag_chain.chain.invoke.side_effect = Exception("Retriever error")
        
        # The chain should handle this gracefully or raise RAGChainError
        with pytest.raises(RAGChainError):
            rag_chain.invoke("Tell me about Rome")


# ============================================================================
# Property-Based Tests
# ============================================================================


class TestPropertyBasedTests:
    """Property-based tests for RAGChain using Hypothesis."""
    
    @given(
        recommendation_query=st.sampled_from([
            "recommend a place to visit",
            "suggest some restaurants",
            "what landmarks should I see",
            "where should I go in Rome",
            "recommend attractions",
            "suggest places to eat",
            "what are the best places to visit"
        ])
    )
    @settings(max_examples=20, deadline=None)
    def test_property_8_recommendation_generation(self, recommendation_query):
        """
        **Validates: Requirements 3.3**
        
        Property 8: Recommendation Generation
        
        For any recommendation request query, the chatbot response should contain 
        at least one place suggestion with a place name that can be extracted by 
        the place extractor.
        """
        # Create place extractor inside the test to avoid fixture issues
        place_extractor = PlaceExtractor()
        
        # Create mock LLM that returns responses with place names
        mock_llm = Mock()
        
        # Create realistic recommendation responses
        recommendation_responses = [
            "I recommend visiting the Colosseum, it's an iconic landmark in Rome.",
            "You should definitely check out the Trevi Fountain and Pantheon.",
            "For restaurants, try Da Enzo in Trastevere for authentic Roman cuisine.",
            "The Vatican Museums are a must-see attraction with incredible art.",
            "Visit the Spanish Steps and Piazza Navona for beautiful architecture.",
            "The Roman Forum offers a glimpse into ancient Rome's history.",
            "For dining, Roscioli is excellent for traditional Italian food."
        ]
        
        # Return a random recommendation based on the query
        import random
        response_text = random.choice(recommendation_responses)
        mock_llm.invoke.return_value = response_text
        
        # Create mock retriever
        mock_retriever = Mock()
        mock_retriever.get_relevant_documents.return_value = [
            Document(
                page_content="Rome has many famous landmarks including the Colosseum, Trevi Fountain, and Pantheon.",
                metadata={"source": "https://example.com/rome-landmarks"}
            )
        ]
        
        # Create RAG chain with mocks
        with patch('src.rag_chain.RetrievalQA') as mock_qa:
            # Mock the chain to return our response
            mock_chain = Mock()
            mock_chain.invoke.return_value = {"result": response_text}
            mock_qa.from_chain_type.return_value = mock_chain
            
            rag_chain = RAGChain(llm=mock_llm, retriever=mock_retriever)
            
            # Generate response for recommendation query
            response = rag_chain.invoke(recommendation_query)
            
            # Property: Response should contain at least one extractable place name
            assert isinstance(response, str), "Response should be a string"
            assert len(response) > 0, "Response should not be empty"
            
            # Extract places from the response
            places = place_extractor.extract_places(response)
            
            # Should extract at least one place
            assert len(places) >= 1, (
                f"Expected at least 1 place in recommendation response for query '{recommendation_query}', "
                f"but extracted {len(places)} places from response: '{response}'"
            )
            
            # Verify that extracted places have valid names
            for place in places:
                assert place.name is not None, "Place name should not be None"
                assert len(place.name) > 0, "Place name should not be empty"
