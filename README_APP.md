# Rome Places Chatbot - Streamlit Application

## Overview

The Rome Places Chatbot is an interactive conversational AI system that helps users discover and learn about places in Rome. It features:

- 💬 Natural language conversation with context awareness
- 🗺️ Interactive map visualization of mentioned places
- 📚 RAG-based responses grounded in curated knowledge
- 💾 Persistent session management across conversations

## Prerequisites

- Python 3.11+
- OpenAI API key
- spaCy English model (`en_core_web_sm`)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Download spaCy model:
```bash
python -m spacy download en_core_web_sm
```

3. Set up environment variables:
```bash
# Create .env file
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

## Running the Application

### Start the Streamlit app:

```bash
streamlit run src/app.py
```

The app will open in your browser at `http://localhost:8501`

## Features

### Chat Interface

- Ask questions about places in Rome
- Get contextual responses based on conversation history
- Streaming responses for real-time feedback

### Map Visualization

- Automatically extracts places mentioned in responses
- Displays interactive map with markers
- Shows routes between multiple places

### Session Management

- **New Session**: Start a fresh conversation
- **Clear History**: Remove all messages from current session
- **Export History**: Download conversation as text file

## Usage Examples

### Ask about landmarks:
```
"Tell me about the Colosseum"
"What's the history of the Pantheon?"
```

### Request recommendations:
```
"Best restaurants in Trastevere"
"What should I visit near the Vatican?"
```

### Follow-up questions:
```
"What's nearby?"
"How do I get there?"
"Tell me more about that"
```

## Project Structure

```
src/
├── app.py                 # Main Streamlit application
├── session_manager.py     # Session persistence
├── context_manager.py     # Conversation context
├── place_extractor.py     # NLP place extraction
├── rag_chain.py          # RAG pipeline
├── geocoder.py           # Place geocoding
├── map_builder.py        # Map visualization
├── vector_store.py       # Document embeddings
└── models.py             # Data models

tests/
├── test_app.py           # Integration tests
└── ...                   # Component tests

sessions/                 # Session storage (JSON files)
data/                     # Vector store data
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)

### Storage Directories

- `sessions/`: Conversation history storage
- `data/vector_store/`: Vector embeddings storage

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run integration tests:
```bash
pytest tests/test_app.py -v
```

Run with coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

## Troubleshooting

### "OpenAI API key not found"
- Ensure `OPENAI_API_KEY` is set in your environment or `.env` file

### "Knowledge base not loaded"
- The vector store is empty. You need to ingest data first (see data ingestion documentation)
- The app will still work but responses may be less grounded

### "spaCy model not found"
- Run: `python -m spacy download en_core_web_sm`

### Map not displaying
- Check that places are being extracted from responses
- Verify geocoding service is accessible
- Some places may not geocode successfully (fallback to manual coordinates)

## Architecture

The application follows a pipeline architecture:

1. **User Input** → Session Manager loads history
2. **Context Building** → Context Manager formats conversation
3. **Place Extraction** → Extract places from query
4. **RAG Pipeline** → Retrieve relevant docs + Generate response
5. **Place Extraction** → Extract places from response
6. **Map Generation** → Geocode + Build map
7. **Display** → Show chat + map

## Performance

- Response generation: ~2-5 seconds (with streaming)
- Place extraction: <100ms
- Geocoding: ~200ms per place (cached)
- Map rendering: <500ms

## Limitations

- Requires internet connection for OpenAI API and geocoding
- Knowledge base limited to ingested content
- Place extraction accuracy depends on spaCy NER
- Geocoding may fail for obscure locations

## Future Enhancements

- Multi-language support
- Voice input/output
- Image integration
- Route optimization
- User authentication
- Analytics dashboard

## License

See LICENSE file for details.

## Support

For issues or questions, please open an issue on the project repository.
