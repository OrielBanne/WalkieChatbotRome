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
    
    # Track if sources were modified
    if "sources_modified" not in st.session_state:
        st.session_state.sources_modified = False
    
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
        # Session management buttons
        st.markdown("#### Session Management")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 Start Fresh", use_container_width=True):
                # Clear current session history
                st.session_state.session_manager.clear_history(
                    st.session_state.current_session.session_id
                )
                st.session_state.messages = []
                st.session_state.last_places = []
                logger.info(f"Cleared history for session: {st.session_state.current_session.session_id}")
                st.rerun()

        with col2:
            # Export conversation history
            history_text = st.session_state.session_manager.export_history(
                st.session_state.current_session.session_id
            )

            st.download_button(
                label="💾 Download Chat",
                data=history_text,
                file_name=f"chat_{st.session_state.current_session.session_id[:8]}.txt",
                mime="text/plain",
                use_container_width=True,
                disabled=len(st.session_state.messages) == 0
            )

        # Previous Sessions
        with st.expander("📜 Previous Sessions"):
            sessions = st.session_state.session_manager.list_sessions(st.session_state.user_id)

            # Filter out empty sessions and current session
            non_empty_sessions = []
            for session in sessions:
                if session.session_id == st.session_state.current_session.session_id:
                    continue
                if session.message_count > 0:
                    non_empty_sessions.append(session)

            # Sort by last interaction (most recent first)
            non_empty_sessions.sort(key=lambda s: s.last_interaction, reverse=True)

            if len(non_empty_sessions) > 0:
                st.markdown("**Switch to a previous session:**")

                for session in non_empty_sessions:
                    # Get session name from first message
                    history = st.session_state.session_manager.load_conversation_history(session.session_id)

                    if history and len(history) > 0:
                        # Find first user message
                        first_user_msg = next((msg for msg in history if msg.role == "user"), None)

                        if first_user_msg:
                            # Create short summary (first 30 chars)
                            summary = first_user_msg.content[:30].strip()
                            if len(first_user_msg.content) > 30:
                                summary += "..."
                        else:
                            continue  # Skip if no user message
                    else:
                        continue  # Skip empty sessions

                    # Format date
                    date_str = session.last_interaction.strftime("%b %d")
                    session_name = f"{summary} ({date_str})"

                    col1, col2 = st.columns([3, 1])

                    with col1:
                        if st.button(
                            f"📅 {session_name}",
                            key=f"load_session_{session.session_id}",
                            use_container_width=True
                        ):
                            # Load the selected session
                            st.session_state.current_session = Session(
                                session_id=session.session_id,
                                user_id=session.user_id,
                                created_at=session.created_at,
                                last_interaction=session.last_interaction,
                                message_count=session.message_count
                            )

                            # Load conversation history
                            history = st.session_state.session_manager.load_conversation_history(
                                session.session_id
                            )
                            st.session_state.messages = [
                                {"role": msg.role, "content": msg.content} for msg in history
                            ]
                            st.session_state.last_places = []

                            set_session_id(session.session_id)
                            logger.info(f"Switched to session: {session.session_id}")
                            st.rerun()

                    with col2:
                        if st.button("🗑️", key=f"delete_session_{session.session_id}"):
                            # Delete the session
                            st.session_state.session_manager.delete_session(session.session_id)
                            logger.info(f"Deleted session: {session.session_id}")
                            st.rerun()
            else:
                st.info("No previous sessions yet.")

        st.markdown("---")

        # Data Management section
        st.markdown("#### 📚 Knowledge Base")

        # Show current sources
        sources_file = "data/sample_sources.txt"
        if os.path.exists(sources_file):
            with open(sources_file, 'r') as f:
                all_lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            # Separate by type
            youtube_sources = [line for line in all_lines if 'youtube.com' in line or 'youtu.be' in line]
            web_sources = [line for line in all_lines if line.startswith('http') and 'youtube' not in line and 'youtu.be' not in line]
            pdf_sources = [line for line in all_lines if line.endswith('.pdf') or 'pdf:' in line.lower()]

            st.text(f"Videos: {len(youtube_sources)} | Websites: {len(web_sources)} | PDFs: {len(pdf_sources)}")

            # Manage Videos
            with st.expander("📹 Manage Videos"):
                # Display current videos
                st.markdown("**Current Videos:**")
                if youtube_sources:
                    # Show videos immediately with URLs, fetch titles in background
                    for i, url in enumerate(youtube_sources, 1):
                        col1, col2 = st.columns([4, 1])
                        
                        with col1:
                            # Show URL immediately as placeholder
                            video_placeholder = st.empty()
                            
                            # Try to get cached or fetch video info
                            if "video_info_cache" not in st.session_state:
                                st.session_state.video_info_cache = {}
                            
                            if url in st.session_state.video_info_cache:
                                # Use cached info
                                video_placeholder.text(st.session_state.video_info_cache[url])
                            else:
                                # Show URL as placeholder
                                video_placeholder.text(f"{i}. {url[:50]}...")
                                
                                # Try to fetch in background (non-blocking)
                                try:
                                    from yt_dlp import YoutubeDL
                                    ydl_opts = {
                                        'quiet': True,
                                        'no_warnings': True,
                                        'extract_flat': False,
                                        'skip_download': True,
                                    }
                                    with YoutubeDL(ydl_opts) as ydl:
                                        info = ydl.extract_info(url, download=False)
                                        title = info.get('title', 'Unknown Title')
                                        duration = info.get('duration', 0)
                                        
                                        # Format duration
                                        if duration:
                                            minutes = duration // 60
                                            seconds = duration % 60
                                            duration_str = f"{minutes}:{seconds:02d}"
                                        else:
                                            duration_str = "Unknown"
                                        
                                        display_text = f"{i}. {title} ({duration_str})"
                                        # Cache and update
                                        st.session_state.video_info_cache[url] = display_text
                                        video_placeholder.text(display_text)
                                except Exception as e:
                                    # Keep showing URL on error
                                    logger.warning(f"Failed to fetch video info: {str(e)}")
                        
                        with col2:
                            if st.button("🗑️", key=f"remove_video_{i}"):
                                all_lines.remove(url)
                                with open(sources_file, 'w') as f:
                                    f.write('\n'.join(all_lines) + '\n')
                                # Remove from cache
                                if url in st.session_state.video_info_cache:
                                    del st.session_state.video_info_cache[url]
                                st.session_state.sources_modified = True
                                st.success(f"Removed video {i}")
                                st.rerun()
                else:
                    st.info("No videos added yet")

                st.markdown("---")

                # Add new video
                st.markdown("**Add New Video:**")
                new_video_url = st.text_input("YouTube URL", key="new_video_url")
                if st.button("➕ Add Video", use_container_width=True):
                    if new_video_url and new_video_url.strip():
                        if "youtube.com" in new_video_url or "youtu.be" in new_video_url:
                            all_lines.append(new_video_url.strip())
                            with open(sources_file, 'w') as f:
                                f.write('\n'.join(all_lines) + '\n')
                            st.session_state.sources_modified = True
                            st.success("Video added! Click 'Rebuild' to update knowledge base.")
                            st.rerun()
                        else:
                            st.error("Please enter a valid YouTube URL")
                    else:
                        st.error("Please enter a URL")

            # Manage Websites
            with st.expander("🌐 Manage Websites"):
                # Display current websites
                st.markdown("**Current Websites:**")
                if web_sources:
                    for i, url in enumerate(web_sources, 1):
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.text(f"{i}. {url[:50]}...")
                        with col2:
                            if st.button("🗑️", key=f"remove_web_{i}"):
                                all_lines.remove(url)
                                with open(sources_file, 'w') as f:
                                    f.write('\n'.join(all_lines) + '\n')
                                st.session_state.sources_modified = True
                                st.success(f"Removed website {i}")
                                st.rerun()
                else:
                    st.info("No websites added yet")

                st.markdown("---")

                # Add new website
                st.markdown("**Add New Website:**")
                new_web_url = st.text_input("Website URL", key="new_web_url", placeholder="https://example.com/rome-guide")
                if st.button("➕ Add Website", use_container_width=True):
                    if new_web_url and new_web_url.strip():
                        if new_web_url.startswith('http'):
                            if 'youtube.com' not in new_web_url and 'youtu.be' not in new_web_url:
                                all_lines.append(new_web_url.strip())
                                with open(sources_file, 'w') as f:
                                    f.write('\n'.join(all_lines) + '\n')
                                st.session_state.sources_modified = True
                                st.success("Website added! Click 'Rebuild' to update knowledge base.")
                                st.rerun()
                            else:
                                st.error("YouTube URLs should be added in the Videos section")
                        else:
                            st.error("Please enter a valid URL starting with http:// or https://")
                    else:
                        st.error("Please enter a URL")

            # Manage PDFs
            with st.expander("📄 Manage PDFs"):
                # Display current PDFs
                st.markdown("**Current PDFs:**")
                if pdf_sources:
                    for i, path in enumerate(pdf_sources, 1):
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            # Extract filename from path
                            filename = path.split('/')[-1] if '/' in path else path
                            st.text(f"{i}. {filename}")
                        with col2:
                            if st.button("🗑️", key=f"remove_pdf_{i}"):
                                all_lines.remove(path)
                                with open(sources_file, 'w') as f:
                                    f.write('\n'.join(all_lines) + '\n')
                                # Also try to delete the actual file
                                try:
                                    if os.path.exists(path):
                                        os.remove(path)
                                except Exception as e:
                                    logger.warning(f"Could not delete PDF file: {e}")
                                st.session_state.sources_modified = True
                                st.success(f"Removed PDF {i}")
                                st.rerun()
                else:
                    st.info("No PDFs added yet")

                st.markdown("---")

                # Upload new PDF
                st.markdown("**Upload New PDF:**")
                uploaded_file = st.file_uploader("Choose a PDF file", type=['pdf'], key="pdf_uploader")
                if uploaded_file is not None:
                    # Save uploaded file to data directory
                    pdf_dir = Path("data/pdfs")
                    pdf_dir.mkdir(exist_ok=True)

                    pdf_path = pdf_dir / uploaded_file.name

                    if st.button("➕ Add PDF", use_container_width=True):
                        try:
                            # Save the uploaded file
                            with open(pdf_path, 'wb') as f:
                                f.write(uploaded_file.getbuffer())

                            # Add to sources list
                            all_lines.append(str(pdf_path))
                            with open(sources_file, 'w') as f:
                                f.write('\n'.join(all_lines) + '\n')

                            st.session_state.sources_modified = True
                            st.success(f"PDF '{uploaded_file.name}' added! Click 'Rebuild' to update knowledge base.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to save PDF: {str(e)}")
                            logger.error(f"PDF upload error: {e}", exc_info=True)

            # Rebuild vector store
            button_type = "primary" if st.session_state.sources_modified else "secondary"
            if st.button("🔄 Rebuild Knowledge Base", use_container_width=True, type=button_type, disabled=not st.session_state.sources_modified):
                with st.spinner("Rebuilding knowledge base... This may take a few minutes."):
                    try:
                        import subprocess
                        result = subprocess.run(
                            [sys.executable, "scripts/ingest_data.py", "--sources", sources_file],
                            capture_output=True,
                            text=True,
                            cwd=str(project_root)
                        )

                        if result.returncode == 0:
                            # Reload vector store
                            st.session_state.vector_store = VectorStore()
                            st.session_state.vector_store.load("data/vector_store")

                            # Update retriever
                            retriever = VectorStoreRetriever(vector_store=st.session_state.vector_store, k=5)
                            llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, streaming=True)
                            st.session_state.rag_chain = RAGChain(llm, retriever)

                            st.session_state.sources_modified = False
                            st.success("✅ Knowledge base rebuilt successfully!")
                            logger.info("Knowledge base rebuilt from UI")
                        else:
                            st.error(f"Failed to rebuild: {result.stderr}")
                            logger.error(f"Rebuild failed: {result.stderr}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        logger.error(f"Rebuild error: {e}", exc_info=True)
        else:
            st.warning("No sources file found")

        st.markdown("---")

        # About button
        with st.expander("ℹ️ About"):
            st.markdown("""
            **Rome Places Chatbot**

            Discover the Eternal City through natural conversation with AI-powered recommendations and interactive maps.

            **Features:**
            - 💬 Natural conversation
            - 🗺️ Interactive maps
            - 📚 Curated knowledge base

            **Created by:**
            - Oriel Banne
            - GitHub: [OrielBanne/WalkieChatbotRome](https://github.com/OrielBanne/WalkieChatbotRome)

            Built with OpenAI, LangChain, and Streamlit.
            """)

        # Tips
        with st.expander("💡 Tips"):
            st.markdown("""
            - Ask about specific places: "Tell me about the Colosseum"
            - Request recommendations: "Best restaurants in Trastevere"
            - Follow-up questions: "What's nearby?"
            - The chatbot remembers your conversation!
            """)

        st.markdown("---")

        # Session info at bottom
        st.markdown("#### Current Session")
        st.text(f"Messages: {len(st.session_state.messages)}")



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
