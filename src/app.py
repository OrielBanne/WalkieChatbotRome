"""
Rome Places Chatbot - Streamlit Application

This is the main Streamlit application that provides an interactive chat interface
for discovering and learning about places in Rome. The app integrates:
- Session management for conversation persistence
- RAG pipeline for grounded responses
- Map visualization for place discovery
"""

import streamlit as st
import os
import sys
from datetime import datetime
from typing import List, Optional
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import logging configuration
from src.logging_config import (
    setup_logging, 
    set_session_id, 
    get_logger,
    get_user_friendly_error,
    log_error_with_context,
    LOG_LEVEL_INFO,
    LOG_LEVEL_DEBUG
)

# Import components
from src.session_manager import SessionManager
from src.context_manager import ContextManager
from src.place_extractor import PlaceExtractor
from src.rag_chain import RAGChain
from src.geocoder import Geocoder
from src.map_builder import MapBuilder
from src.vector_store import VectorStore
from src.models import Message, PlaceMarker

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.retrievers import BaseRetriever
from streamlit_folium import st_folium
from pydantic import ConfigDict

# Set up logging
setup_logging(
    log_level=LOG_LEVEL_INFO,
    log_file="logs/chatbot.log",
    log_to_console=True
)
logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="Rome Places Chatbot",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #8B4513;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)


class VectorStoreRetriever(BaseRetriever):
    """Adapter to make VectorStore compatible with LangChain's BaseRetriever."""
    
    vector_store: VectorStore
    k: int = 5
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def _get_relevant_documents(self, query: str):
        """Get relevant documents for a query."""
        return self.vector_store.similarity_search(query, k=self.k)
    
    async def _aget_relevant_documents(self, query: str):
        """Async version - not implemented."""
        return self._get_relevant_documents(query)
    
    def get_relevant_documents(self, query: str):
        """Public method to get relevant documents."""
        return self._get_relevant_documents(query)


def initialize_components():
    """Initialize all application components."""
    
    # Check for OpenAI API key
    if "OPENAI_API_KEY" not in os.environ:
        st.error("⚠️ OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        st.stop()
    
    # Initialize components if not already in session state
    if "components_initialized" not in st.session_state:
        try:
            with st.spinner("Initializing chatbot components..."):
                # Session Manager
                st.session_state.session_manager = SessionManager(storage_dir="sessions")
                
                # Context Manager
                st.session_state.context_manager = ContextManager(
                    st.session_state.session_manager
                )
                
                # Place Extractor
                st.session_state.place_extractor = PlaceExtractor()
                
                # Vector Store
                st.session_state.vector_store = VectorStore()
                
                # Try to load existing vector store
                vector_store_path = "data/vector_store"
                if os.path.exists(vector_store_path):
                    try:
                        st.session_state.vector_store.load(vector_store_path)
                        logger.info(f"Loaded vector store with {len(st.session_state.vector_store)} documents")
                    except Exception as e:
                        logger.warning(f"Could not load vector store: {e}")
                        st.warning("⚠️ Knowledge base not loaded. Responses may be limited.")
                
                # RAG Chain
                llm = ChatOpenAI(
                    model="gpt-3.5-turbo",
                    temperature=0.7,
                    streaming=True
                )
                
                retriever = VectorStoreRetriever(vector_store=st.session_state.vector_store, k=5)
                st.session_state.rag_chain = RAGChain(llm, retriever)
                
                # Geocoder
                st.session_state.geocoder = Geocoder()
                
                # Map Builder
                st.session_state.map_builder = MapBuilder()
                
                st.session_state.components_initialized = True
                logger.info("All components initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}", exc_info=True)
            st.error(f"⚠️ Failed to initialize chatbot: {str(e)}")
            st.stop()


def initialize_session_state():
    """Initialize Streamlit session state for conversation management."""
    
    # User ID (in production, this would come from authentication)
    if "user_id" not in st.session_state:
        st.session_state.user_id = "default_user"
    
    # Current session
    if "current_session" not in st.session_state:
        try:
            session = st.session_state.session_manager.get_or_create_session(
                st.session_state.user_id
            )
            st.session_state.current_session = session
            set_session_id(session.session_id)
            logger.info(f"Created new session: {session.session_id}")
        except Exception as e:
            log_error_with_context(logger, e, "Failed to create session")
            st.error(get_user_friendly_error("storage_unavailable"))
            st.stop()
    
    # Conversation history (in-memory for display)
    if "messages" not in st.session_state:
        try:
            # Load from persistent storage
            history = st.session_state.session_manager.load_conversation_history(
                st.session_state.current_session.session_id
            )
            st.session_state.messages = [
                {"role": msg.role, "content": msg.content} for msg in history
            ]
            logger.info(f"Loaded {len(st.session_state.messages)} messages from history")
        except Exception as e:
            log_error_with_context(
                logger, e, "Failed to load conversation history",
                st.session_state.current_session.session_id
            )
            st.warning(get_user_friendly_error("storage_unavailable"))
            st.session_state.messages = []
    
    # Last extracted places (for map display)
    if "last_places" not in st.session_state:
        st.session_state.last_places = []


def render_sidebar():
    """Render the sidebar with session management controls."""
    
    with st.sidebar:
        st.markdown("### 🏛️ Rome Places Chatbot")
        st.markdown("---")
        
        # Session info
        st.markdown("#### Current Session")
        session_id_short = st.session_state.current_session.session_id[:8]
        st.text(f"ID: {session_id_short}...")
        st.text(f"Messages: {len(st.session_state.messages)}")
        
        st.markdown("---")
        
        # Session management buttons
        st.markdown("#### Session Management")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🆕 New Session", use_container_width=True):
                # Create new session
                new_session = st.session_state.session_manager.get_or_create_session(
                    st.session_state.user_id
                )
                st.session_state.current_session = new_session
                st.session_state.messages = []
                st.session_state.last_places = []
                logger.info(f"Started new session: {new_session.session_id}")
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear History", use_container_width=True):
                # Clear current session history
                st.session_state.session_manager.clear_history(
                    st.session_state.current_session.session_id
                )
                st.session_state.messages = []
                st.session_state.last_places = []
                logger.info(f"Cleared history for session: {st.session_state.current_session.session_id}")
                st.rerun()
        
        if st.button("📥 Export History", use_container_width=True):
            # Export conversation history
            history_text = st.session_state.session_manager.export_history(
                st.session_state.current_session.session_id
            )
            
            # Create download button
            st.download_button(
                label="Download History",
                data=history_text,
                file_name=f"chat_history_{st.session_state.current_session.session_id[:8]}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        st.markdown("---")
        
        # About section
        st.markdown("#### About")
        st.markdown("""
        This chatbot helps you discover places in Rome using:
        - 💬 Natural conversation
        - 🗺️ Interactive maps
        - 📚 Curated knowledge base
        
        Ask about landmarks, restaurants, attractions, and more!
        """)
        
        # Tips
        with st.expander("💡 Tips"):
            st.markdown("""
            - Ask about specific places: "Tell me about the Colosseum"
            - Request recommendations: "Best restaurants in Trastevere"
            - Follow-up questions: "What's nearby?"
            - The chatbot remembers your conversation!
            """)


def render_chat_interface():
    """Render the main chat interface."""
    
    # Header
    st.markdown('<div class="main-header">🏛️ Rome Places Chatbot</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Discover the Eternal City through conversation</div>', unsafe_allow_html=True)
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me about places in Rome..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                # Show loading indicator
                with st.spinner("Thinking..."):
                    # Build context from conversation history
                    history = st.session_state.session_manager.load_conversation_history(
                        st.session_state.current_session.session_id
                    )
                    context = st.session_state.context_manager.build_context(
                        prompt, history, max_tokens=4000
                    )
                    
                    # Generate streaming response
                    for chunk in st.session_state.rag_chain.stream(prompt, context):
                        full_response += chunk
                        message_placeholder.markdown(full_response + "▌")
                    
                    # Final response without cursor
                    message_placeholder.markdown(full_response)
                
                # Save messages to persistent storage
                try:
                    st.session_state.context_manager.add_to_history(
                        st.session_state.current_session.session_id,
                        "user",
                        prompt
                    )
                    st.session_state.context_manager.add_to_history(
                        st.session_state.current_session.session_id,
                        "assistant",
                        full_response
                    )
                except Exception as e:
                    log_error_with_context(
                        logger, e, "Failed to save messages",
                        st.session_state.current_session.session_id
                    )
                    st.warning(get_user_friendly_error("storage_write_failed"))
                
                # Add assistant message to session state
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                # Extract places from response for map visualization
                try:
                    places = st.session_state.place_extractor.extract_places(full_response)
                    rome_places = st.session_state.place_extractor.filter_rome_places(places)
                    st.session_state.last_places = rome_places
                    logger.info(f"Generated response with {len(rome_places)} places extracted")
                except Exception as e:
                    log_error_with_context(
                        logger, e, "Failed to extract places",
                        st.session_state.current_session.session_id
                    )
                    st.session_state.last_places = []
                
            except Exception as e:
                log_error_with_context(
                    logger, e, "Error generating response",
                    st.session_state.current_session.session_id
                )
                error_message = get_user_friendly_error("api_error")
                message_placeholder.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})


def render_map_visualization():
    """Render the map visualization for extracted places."""
    
    if not st.session_state.last_places:
        return
    
    st.markdown("---")
    st.markdown("### 🗺️ Places on Map")
    
    try:
        # Geocode extracted places
        place_markers = []
        
        for place_mention in st.session_state.last_places:
            try:
                coords = st.session_state.geocoder.geocode_place(
                    place_mention.name,
                    bias_location=(41.9028, 12.4964)  # Rome center
                )
                
                if coords:
                    marker = PlaceMarker(
                        name=place_mention.name,
                        coordinates=(coords.latitude, coords.longitude),
                        place_type="landmark",  # Default type
                        description=None,
                        icon="star"
                    )
                    place_markers.append(marker)
            except Exception as e:
                logger.warning(f"Failed to geocode place '{place_mention.name}': {e}")
                continue
        
        if place_markers:
            # Create map with places
            map_obj = st.session_state.map_builder.create_map_with_places(
                places=place_markers,
                add_route=len(place_markers) > 1
            )
            
            # Render map using st-folium
            st_folium(map_obj, width=700, height=500)
            
            logger.info(f"Rendered map with {len(place_markers)} markers")
        else:
            st.info("ℹ️ No places could be mapped from the conversation.")
    
    except Exception as e:
        log_error_with_context(
            logger, e, "Error rendering map",
            st.session_state.current_session.session_id
        )
        st.warning(get_user_friendly_error("geocoding_unavailable"))


def main():
    """Main application entry point."""
    
    # Initialize components
    initialize_components()
    
    # Initialize session state
    initialize_session_state()
    
    # Render sidebar
    render_sidebar()
    
    # Render main chat interface
    render_chat_interface()
    
    # Render map visualization
    render_map_visualization()


if __name__ == "__main__":
    main()
