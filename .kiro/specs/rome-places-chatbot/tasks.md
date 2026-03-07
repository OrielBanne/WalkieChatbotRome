# Implementation Plan: Rome Places Chatbot

## Overview

This implementation plan breaks down the Rome Places Chatbot into discrete coding tasks. The system uses Python with Streamlit for the UI, LangChain for RAG, spaCy for NLP, and Folium for map visualization. The implementation follows a pipeline architecture with clear separation between conversation management, RAG processing, and map generation.

## Tasks

- [x] 1. Set up project structure and dependencies
  - Create project directory structure (src/, tests/, data/, sessions/)
  - Create requirements.txt with all dependencies (streamlit, langchain, openai, spacy, folium, streamlit-folium, geopy, hypothesis, pytest)
  - Create .env.example for configuration (OpenAI API key, session storage path)
  - Download spaCy model: en_core_web_sm
  - Create __init__.py files for Python packages
  - _Requirements: All requirements depend on proper setup_

- [x] 2. Implement data models and core types
  - [x] 2.1 Create data models module (src/models.py)
    - Implement Message dataclass with role, content, timestamp, session_id, metadata
    - Implement Session dataclass with session_id, user_id, created_at, last_interaction, message_count
    - Implement PlaceMention dataclass with name, entity_type, confidence, span, context
    - Implement PlaceMarker dataclass with name, coordinates, place_type, description, icon
    - Implement Coordinates dataclass with latitude, longitude, accuracy, source
    - _Requirements: 1.1, 1.2, 1.4_
  
  - [x] 2.2 Write property test for Message persistence round-trip
    - **Property 1: Message Persistence Round-Trip**
    - **Validates: Requirements 1.1, 1.2, 1.3**
    - Test that any message persisted and retrieved has identical content, timestamp, and session_id

- [x] 3. Implement Session Manager with file-based storage
  - [x] 3.1 Create SessionManager class (src/session_manager.py)
    - Implement get_or_create_session(user_id) -> Session
    - Implement load_conversation_history(session_id) -> List[Message]
    - Implement save_message(session_id, message) -> None
    - Implement clear_history(session_id) -> None
    - Implement list_sessions(user_id) -> List[SessionMetadata]
    - Implement export_history(session_id) -> str
    - Use JSON file format: {user_id}_{session_id}.json
    - Add file locking for concurrent access
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 5.1, 5.2, 5.3, 5.4_
  
  - [x] 3.2 Write property test for chronological message ordering
    - **Property 2: Chronological Message Ordering**
    - **Validates: Requirements 1.5**
    - Test that any set of messages with different timestamps are returned in chronological order
  
  - [x] 3.3 Write property test for history deletion round-trip
    - **Property 9: History Deletion Round-Trip**
    - **Validates: Requirements 5.1**
    - Test that clearing history and retrieving returns empty list
  
  - [x] 3.4 Write property test for unique session identifiers
    - **Property 10: Unique Session Identifiers**
    - **Validates: Requirements 5.2**
    - Test that consecutive session creations generate different IDs
  
  - [x] 3.5 Write property test for session listing completeness
    - **Property 11: Session Listing Completeness**
    - **Validates: Requirements 5.3**
    - Test that listing sessions returns exactly N sessions for user with N stored sessions
  
  - [x] 3.6 Write unit tests for SessionManager
    - Test session creation with valid UUID
    - Test empty message rejection
    - Test storage unavailable scenario (graceful degradation)
    - Test corrupted JSON handling
    - _Requirements: 1.6_

- [x] 4. Checkpoint - Ensure session management tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Context Manager
  - [x] 5.1 Create ContextManager class (src/context_manager.py)
    - Implement build_context(query, history, max_tokens) -> str
    - Implement add_to_history(session_id, role, content) -> None
    - Implement get_relevant_history(query, history, k) -> List[Message]
    - Use sliding window for token management (max 4000 tokens)
    - Format history in ChatML format for OpenAI
    - _Requirements: 2.1, 2.4_
  
  - [x] 5.2 Write property test for context includes history
    - **Property 3: Context Includes History**
    - **Validates: Requirements 2.1**
    - Test that response generation with non-empty history includes at least one historical message
  
  - [x] 5.3 Write property test for cross-session continuity
    - **Property 4: Cross-Session Continuity**
    - **Validates: Requirements 2.3**
    - Test that retrieving all histories for a user returns messages from all sessions
  
  - [x] 5.4 Write unit tests for ContextManager
    - Test token limit enforcement
    - Test ChatML formatting
    - Test relevant history selection
    - _Requirements: 2.1_

- [x] 6. Implement Place Extractor with spaCy
  - [x] 6.1 Create PlaceExtractor class (src/place_extractor.py)
    - Implement extract_places(text) -> List[PlaceMention]
    - Implement filter_rome_places(places) -> List[PlaceMention]
    - Implement resolve_ambiguous_places(places, context) -> List[PlaceMention]
    - Load spaCy en_core_web_sm model
    - Extract GPE, LOC, FAC entities
    - Add custom pattern matching for Rome landmarks (Colosseum, Trevi Fountain, etc.)
    - Create gazetteer of known Rome places
    - Return confidence scores for extractions
    - _Requirements: 2.2, 3.1_
  
  - [x] 6.2 Write property test for place extraction consistency
    - **Property 13: Place Extraction Consistency**
    - **Validates: Implementation correctness**
    - Test that extracting places from same text multiple times returns same results
  
  - [x] 6.3 Write property test for place reference resolution
    - **Property 5: Place Reference Resolution**
    - **Validates: Requirements 2.2**
    - Test that places mentioned in history are identified in subsequent queries
  
  - [x] 6.4 Write unit tests for PlaceExtractor
    - Test extraction of "Colosseum" from sample text
    - Test handling of special characters in place names
    - Test empty text handling
    - Test non-English text handling
    - _Requirements: 3.1_

- [x] 7. Implement data ingestion pipeline
  - [x] 7.1 Create data loaders (src/loaders.py)
    - Implement YouTubeLoader.load_transcript(video_url) -> Document
    - Implement WebLoader.load_webpage(url) -> Document
    - Implement PDFLoader.load_pdf(file_path) -> List[Document]
    - Use youtube-transcript-api for YouTube
    - Use BeautifulSoup for web scraping
    - Use PyPDF2 for PDF extraction
    - Return LangChain Document objects with metadata
    - _Requirements: 3.1, 3.2_
  
  - [x] 7.2 Create text chunker (src/chunker.py)
    - Implement chunk_text(text, chunk_size, overlap) -> List[str]
    - Use semantic chunking (sentence boundaries)
    - Default chunk_size=1000, overlap=200
    - _Requirements: 3.1_
  
  - [x] 7.3 Write unit tests for data loaders
    - Test YouTube transcript extraction with sample URL
    - Test web scraping with sample HTML
    - Test PDF extraction with sample file
    - Test error handling for invalid URLs/files
    - _Requirements: 3.1_

- [x] 8. Implement Vector Store with FAISS
  - [x] 8.1 Create VectorStore class (src/vector_store.py)
    - Implement add_documents(documents) -> None
    - Implement similarity_search(query, k) -> List[Document]
    - Implement similarity_search_with_score(query, k) -> List[Tuple[Document, float]]
    - Implement delete_documents(ids) -> None
    - Use FAISS for local vector storage
    - Use OpenAI text-embedding-ada-002 (1536 dimensions)
    - Store metadata: source URL, timestamp, place tags
    - Add error handling for vector store unavailable
    - _Requirements: 3.1, 3.2_
  
  - [x] 8.2 Write property test for place query retrieval
    - **Property 6: Place Query Retrieval**
    - **Validates: Requirements 3.1**
    - Test that querying for a place retrieves at least one relevant document
  
  - [x] 8.3 Write property test for place type coverage
    - **Property 7: Place Type Coverage**
    - **Validates: Requirements 3.2**
    - Test that vector store contains documents for each place type
  
  - [x] 8.4 Write unit tests for VectorStore
    - Test document addition and retrieval
    - Test similarity search with "Colosseum" query
    - Test empty results handling
    - Test vector store error handling
    - _Requirements: 3.1_

- [x] 9. Checkpoint - Ensure data pipeline tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement RAG Chain with LangChain
  - [x] 10.1 Create RAGChain class (src/rag_chain.py)
    - Implement __init__(llm, retriever)
    - Implement invoke(query, context) -> str
    - Implement stream(query, context) -> Iterator[str]
    - Use LangChain RetrievalQA chain
    - Retrieve top-k=5 most relevant chunks
    - Create custom prompt template emphasizing Rome information
    - Add error handling for API failures with retry logic
    - _Requirements: 3.1, 3.3, 4.1, 4.2_
  
  - [x] 10.2 Write property test for recommendation generation
    - **Property 8: Recommendation Generation**
    - **Validates: Requirements 3.3**
    - Test that recommendation requests generate responses with extractable place names
  
  - [x] 10.3 Write unit tests for RAGChain
    - Test response generation for "Tell me about the Colosseum"
    - Test streaming response
    - Test API timeout handling
    - Test rate limit error handling
    - _Requirements: 4.1_

- [x] 11. Implement Geocoder with caching
  - [x] 11.1 Create Geocoder class (src/geocoder.py)
    - Implement geocode_place(place_name, bias_location) -> Optional[Coordinates]
    - Implement batch_geocode(places) -> Dict[str, Optional[Coordinates]]
    - Implement reverse_geocode(lat, lon) -> Optional[str]
    - Use Geopy with Nominatim geocoder
    - Bias searches to Rome bounding box: (41.8, 12.4) to (41.95, 12.6)
    - Implement in-memory caching for geocoding results
    - Create manual coordinate database for major landmarks
    - Add fallback to manual database on geocoding failure
    - _Requirements: Map visualization support_
  
  - [x] 11.2 Write property test for geocoding cache consistency
    - **Property 14: Geocoding Cache Consistency**
    - **Validates: Implementation correctness**
    - Test that repeated geocoding of same place returns same coordinates
  
  - [x] 11.3 Write unit tests for Geocoder
    - Test geocoding "Colosseum" returns valid coordinates
    - Test caching behavior
    - Test fallback to manual database
    - Test geocoding service unavailable handling
    - _Requirements: Map visualization support_

- [x] 12. Implement Map Builder with Folium
  - [x] 12.1 Create MapBuilder class (src/map_builder.py)
    - Implement create_base_map(center, zoom) -> folium.Map
    - Implement add_markers(map_obj, places) -> None
    - Implement add_route(map_obj, coordinates) -> None
    - Implement render_to_streamlit(map_obj) -> None
    - Default center: Rome (41.9028, 12.4964)
    - Create custom marker icons for place types (landmark, restaurant, etc.)
    - Add route visualization with PolyLine
    - Add popup content with place name and description
    - _Requirements: Map visualization support_
  
  - [x] 12.2 Write property test for map marker correspondence
    - **Property 15: Map Marker Correspondence**
    - **Validates: Implementation correctness**
    - Test that map contains exactly one marker per unique place
  
  - [x] 12.3 Write unit tests for MapBuilder
    - Test base map creation
    - Test marker addition
    - Test route generation for multiple places
    - Test empty places list handling
    - _Requirements: Map visualization support_

- [x] 13. Checkpoint - Ensure geocoding and mapping tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. Implement Streamlit UI
  - [x] 14.1 Create main Streamlit app (src/app.py)
    - Set up Streamlit page configuration
    - Initialize session state for conversation management
    - Create sidebar for session management (new session, clear history, export)
    - Implement chat input widget
    - Implement chat message display with st.chat_message
    - Add loading indicators during processing
    - _Requirements: 4.1, 4.2, 5.1, 5.2, 5.3, 5.4_
  
  - [x] 14.2 Integrate RAG pipeline into Streamlit
    - Wire SessionManager to Streamlit session state
    - Wire ContextManager to build context from history
    - Wire PlaceExtractor to extract places from user query
    - Wire RAGChain to generate responses
    - Display streaming responses in real-time
    - Save messages to SessionManager after generation
    - _Requirements: 2.1, 3.1, 4.1_
  
  - [x] 14.3 Integrate map visualization into Streamlit
    - Extract places from chatbot response using PlaceExtractor
    - Geocode extracted places using Geocoder
    - Build map with MapBuilder
    - Render map using st-folium
    - Display map below chat messages
    - Handle cases with no places extracted
    - _Requirements: Map visualization support_
  
  - [x] 14.4 Write integration tests for Streamlit app
    - Test full query → response → map flow
    - Test session persistence across app reruns
    - Test clear history functionality
    - Test export history functionality
    - _Requirements: All requirements_

- [x] 15. Implement error handling and logging
  - [x] 15.1 Add error handling throughout application
    - Add try-except blocks for storage errors (graceful degradation)
    - Add retry logic with exponential backoff for API calls
    - Add fallback for geocoding failures
    - Add safe wrappers for place extraction
    - Add safe wrappers for vector store operations
    - _Requirements: 1.6_
  
  - [x] 15.2 Set up logging configuration
    - Configure Python logging with appropriate levels (ERROR, WARNING, INFO, DEBUG)
    - Log all errors with timestamp, error type, stack trace, session ID
    - Log warnings for degraded functionality
    - Create user-friendly error messages for UI display
    - _Requirements: 1.6_
  
  - [x] 15.3 Write unit tests for error handling
    - Test storage unavailable scenario
    - Test API timeout handling
    - Test geocoding failure fallback
    - Test vector store error handling
    - _Requirements: 1.6_

- [x] 16. Create data ingestion script
  - [x] 16.1 Create ingestion script (scripts/ingest_data.py)
    - Accept command-line arguments for data sources (URLs, file paths)
    - Load content using appropriate loaders
    - Chunk text using text chunker
    - Generate embeddings using OpenAI
    - Store vectors in FAISS index
    - Save FAISS index to disk
    - Add progress indicators for long-running ingestion
    - _Requirements: 3.1, 3.2_
  
  - [x] 16.2 Write unit tests for ingestion script
    - Test ingestion of sample YouTube video
    - Test ingestion of sample webpage
    - Test ingestion of sample PDF
    - Test FAISS index persistence
    - _Requirements: 3.1_

- [x] 17. Create configuration and environment setup
  - [x] 17.1 Create configuration module (src/config.py)
    - Load environment variables from .env
    - Define constants (ROME_CENTER, ROME_BBOX, MAX_CONTEXT_TOKENS, etc.)
    - Define file paths (SESSION_STORAGE_PATH, VECTOR_STORE_PATH)
    - Validate required configuration (OpenAI API key)
    - _Requirements: All requirements_
  
  - [x] 17.2 Create README.md with setup instructions
    - Document installation steps
    - Document environment variable configuration
    - Document data ingestion process
    - Document running the application
    - Document testing procedures
    - _Requirements: All requirements_

- [x] 18. Final integration and testing
  - [x] 18.1 Wire all components together
    - Ensure SessionManager is properly initialized in app.py
    - Ensure ContextManager uses SessionManager
    - Ensure RAGChain uses VectorStore and OpenAI LLM
    - Ensure PlaceExtractor is used in both query and response processing
    - Ensure Geocoder and MapBuilder work together
    - Verify all error handling is in place
    - _Requirements: All requirements_
  
  - [x] 18.2 Run full test suite
    - Run all unit tests with pytest
    - Run all property tests with Hypothesis (100 iterations)
    - Generate coverage report (target >80%)
    - Fix any failing tests
    - _Requirements: All requirements_
  
  - [x] 18.3 Write property test for history export round-trip
    - **Property 12: History Export Round-Trip**
    - **Validates: Requirements 5.4**
    - Test that exporting and parsing history preserves all message data

- [x] 19. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with minimum 100 iterations
- Unit tests focus on specific examples and edge cases
- Error handling ensures graceful degradation when services are unavailable
- The implementation follows a pipeline architecture with clear component separation
- All components are designed to be testable in isolation
