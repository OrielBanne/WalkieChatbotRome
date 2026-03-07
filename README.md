# Rome Places Chatbot

An interactive conversational AI system that helps users discover and learn about places of interest in Rome. The chatbot provides information, recommendations, and answers questions about Roman landmarks, restaurants, attractions, and other points of interest, while maintaining conversation context across sessions.

## Features

- **Conversational AI**: Natural language interaction powered by OpenAI GPT models
- **RAG Architecture**: Retrieval-Augmented Generation using curated content from YouTube, web sources, and PDFs
- **Session Persistence**: Conversation history saved across sessions for continuous user experience
- **Interactive Maps**: Visual place discovery with Folium maps integrated into the chat interface
- **Place Extraction**: Automatic identification of Rome landmarks using spaCy NER
- **Geocoding**: Accurate location mapping with fallback to manual coordinates for major landmarks
- **Context-Aware**: Maintains conversation context and references previous discussions

## Architecture

The system uses a pipeline architecture with the following components:

- **Session Manager**: File-based conversation history persistence
- **Context Manager**: Token-aware conversation context building
- **Place Extractor**: spaCy-based named entity recognition for places
- **RAG Chain**: LangChain-powered retrieval and generation pipeline
- **Vector Store**: FAISS-based document embedding storage
- **Geocoder**: Geopy-based place name to coordinate conversion
- **Map Builder**: Folium-based interactive map generation
- **Streamlit UI**: User-friendly web interface

## Prerequisites

- Python 3.9 or higher
- OpenAI API key
- Internet connection for geocoding and API calls

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd rome-places-chatbot
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download spaCy Model

```bash
python -m spacy download en_core_web_sm
```

### 5. Configure Environment Variables

**IMPORTANT: Your OpenAI API key should be set as a system environment variable, NOT in the `.env` file.**

#### Option 1: PowerShell (Recommended for Windows)
```powershell
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'your-key-here', 'User')
```

#### Option 2: Windows GUI
1. Open System Properties (Win + Pause/Break)
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "User variables", click "New"
5. Variable name: `OPENAI_API_KEY`
6. Variable value: Your OpenAI API key
7. Click OK

#### Option 3: macOS/Linux
```bash
# Add to ~/.bashrc or ~/.zshrc
export OPENAI_API_KEY='your-key-here'

# Then reload:
source ~/.bashrc  # or source ~/.zshrc
```

#### Verify It Works
```bash
python -c "import os; print('✓ API key found' if os.getenv('OPENAI_API_KEY') else '✗ API key not found')"
```

**Note:** After setting the environment variable, you may need to restart your terminal or IDE.

## Data Ingestion

Before running the chatbot, you need to ingest content about Rome places into the vector store.

### Ingest from YouTube

```bash
python scripts/ingest_data.py --youtube "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Ingest from Web Pages

```bash
python scripts/ingest_data.py --web "https://example.com/rome-guide"
```

### Ingest from PDF Files

```bash
python scripts/ingest_data.py --pdf "path/to/rome-guide.pdf"
```

### Batch Ingestion

You can ingest multiple sources at once:

```bash
python scripts/ingest_data.py \
  --youtube "https://www.youtube.com/watch?v=VIDEO1" \
  --youtube "https://www.youtube.com/watch?v=VIDEO2" \
  --web "https://example.com/rome-guide" \
  --pdf "path/to/guide.pdf"
```

### Append to Existing Vector Store

By default, ingestion appends to the existing vector store. To start fresh:

```bash
# Remove existing vector store
rm -rf data/vector_store

# Then run ingestion
python scripts/ingest_data.py --youtube "URL"
```

## Running the Application

### Start the Chatbot

```bash
streamlit run src/app.py
```

The application will open in your default web browser at `http://localhost:8501`.

### Using the Chatbot

1. **Ask Questions**: Type your question about Rome places in the chat input
   - "Tell me about the Colosseum"
   - "What are the best restaurants in Trastevere?"
   - "Recommend some landmarks to visit"

2. **View Maps**: Places mentioned in responses are automatically shown on an interactive map

3. **Session Management**:
   - **New Session**: Click "New Session" in the sidebar to start fresh
   - **Clear History**: Click "Clear History" to delete current conversation
   - **Export History**: Click "Export History" to download conversation as text

4. **Conversation Context**: The chatbot remembers previous messages in your session, so you can ask follow-up questions naturally

## Project Structure

```
rome-places-chatbot/
├── src/                      # Source code
│   ├── app.py               # Streamlit application
│   ├── config.py            # Configuration management
│   ├── models.py            # Data models
│   ├── session_manager.py   # Session persistence
│   ├── context_manager.py   # Context building
│   ├── place_extractor.py   # Place name extraction
│   ├── rag_chain.py         # RAG pipeline
│   ├── vector_store.py      # Vector storage
│   ├── geocoder.py          # Geocoding
│   ├── map_builder.py       # Map generation
│   ├── loaders.py           # Data loaders
│   ├── chunker.py           # Text chunking
│   └── logging_config.py    # Logging setup
├── scripts/                  # Utility scripts
│   └── ingest_data.py       # Data ingestion script
├── tests/                    # Test suite
│   ├── test_*.py            # Unit tests
│   └── property_test_*.py   # Property-based tests
├── data/                     # Data directory
│   └── vector_store/        # Vector store files
├── sessions/                 # Session storage
├── .env                      # Environment variables (create from .env.example)
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Testing

### Run All Tests

```bash
pytest
```

### Run Unit Tests Only

```bash
pytest tests/ -k "not property_test"
```

### Run Property-Based Tests

```bash
pytest tests/ -k "property_test"
```

### Run Tests with Coverage

```bash
pytest --cov=src --cov-report=html
```

View coverage report by opening `htmlcov/index.html` in your browser.

### Run Specific Test File

```bash
pytest tests/test_session_manager.py -v
```

## Configuration

### Environment Variables

All configuration is managed through environment variables in the `.env` file:

**OpenAI Configuration:**
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `LLM_MODEL`: Language model (default: `gpt-3.5-turbo`)
- `EMBEDDING_MODEL`: Embedding model (default: `text-embedding-ada-002`)

**Application Settings:**
- `APP_TITLE`: Application title (default: `Rome Places Chatbot`)
- `MAX_CONTEXT_TOKENS`: Max conversation context tokens (default: `4000`)
- `RETRIEVAL_TOP_K`: Number of documents to retrieve (default: `5`)

**File Paths:**
- `SESSION_STORAGE_PATH`: Session files directory (default: `./sessions`)
- `VECTOR_STORE_PATH`: Vector store directory (default: `./data/vector_store`)
- `DATA_DIR`: Data directory (default: `./data`)

**Geographic Settings:**
- `ROME_CENTER_LAT`: Rome center latitude (default: `41.9028`)
- `ROME_CENTER_LON`: Rome center longitude (default: `12.4964`)

**Text Processing:**
- `CHUNK_SIZE`: Text chunk size in characters (default: `1000`)
- `CHUNK_OVERLAP`: Chunk overlap in characters (default: `200`)

**Session Management:**
- `SESSION_RETENTION_DAYS`: Days to retain sessions (default: `90`)

**RAG Settings:**
- `RAG_RETRIEVAL_K`: Documents to retrieve for RAG (default: `5`)
- `API_MAX_RETRIES`: Max API retry attempts (default: `3`)
- `API_TIMEOUT`: API timeout in seconds (default: `30`)

**Logging:**
- `LOG_LEVEL`: Logging level (default: `INFO`)

### Validation

Configuration is automatically validated on startup. If required settings are missing or invalid, the application will display helpful error messages.

To manually validate configuration:

```python
from src.config import validate_configuration, get_config_summary

# Validate configuration
validate_configuration()

# Print configuration summary
print(get_config_summary())
```

## Troubleshooting

### OpenAI API Key Not Found

**Error**: `OpenAI API key not found`

**Solution**: Ensure your OpenAI API key is set as a system environment variable:

```bash
# Verify the key is set
python -c "import os; print('✓ API key found' if os.getenv('OPENAI_API_KEY') else '✗ API key not found')"
```

If not found, follow the setup instructions in Step 5 above. Remember to restart your terminal or IDE after setting the environment variable.

### Vector Store Empty

**Error**: No relevant documents found for queries

**Solution**: Run data ingestion to populate the vector store:
```bash
python scripts/ingest_data.py --youtube "URL" --web "URL"
```

### Geocoding Failures

**Error**: Places not showing on map

**Solution**: 
- Check internet connection (geocoding requires API access)
- Major Rome landmarks have fallback coordinates and should always work
- Check logs for specific geocoding errors

### Session Files Not Persisting

**Error**: Conversation history lost between sessions

**Solution**:
- Ensure `SESSION_STORAGE_PATH` directory exists and is writable
- Check file permissions on the sessions directory
- Review logs for file system errors

### Import Errors

**Error**: `ModuleNotFoundError` or import errors

**Solution**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

### Port Already in Use

**Error**: Streamlit port 8501 already in use

**Solution**:
```bash
# Use a different port
streamlit run src/app.py --server.port 8502
```

## Development

### Adding New Data Sources

To add new content sources:

1. Add URLs or file paths to your ingestion command
2. Run the ingestion script
3. Restart the application to use the new content

### Extending Place Types

To add new place type categories:

1. Edit `src/map_builder.py` and add to `PLACE_TYPE_COLORS` and `PLACE_TYPE_ICONS`
2. Update place extraction patterns in `src/place_extractor.py` if needed

### Custom Prompts

To customize the RAG prompt template:

1. Edit `src/rag_chain.py`
2. Modify the `ROME_PROMPT_TEMPLATE` constant
3. Restart the application

## Performance Optimization

### Vector Store

- Use FAISS for fast similarity search
- Adjust `CHUNK_SIZE` and `CHUNK_OVERLAP` for optimal retrieval
- Consider using GPU-accelerated FAISS for large datasets

### Context Management

- Adjust `MAX_CONTEXT_TOKENS` based on your model's context window
- Use `RETRIEVAL_TOP_K` to control number of retrieved documents
- Implement semantic similarity for better history selection

### Caching

- Geocoding results are cached in memory
- Consider implementing Redis for distributed caching
- Cache embeddings for frequently accessed documents

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Add your license information here]

## Acknowledgments

- OpenAI for GPT and embedding models
- LangChain for RAG framework
- spaCy for NLP capabilities
- Streamlit for the web interface
- Folium for map visualization
- Geopy for geocoding services

## Support

For issues, questions, or contributions, please [open an issue](link-to-issues) on GitHub.
