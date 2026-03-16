# 🏛️ WalkieChatbot Rome

An AI-powered travel companion for exploring Rome. Chat naturally about landmarks, get personalized day itineraries optimized for walking distance and opening hours, and see everything on an interactive map — all from your browser or phone.

![App in Action](screenshot%20of%20the%20App%20at%20work.jpg)

## What It Does

- **Chat about Rome** — Ask anything about landmarks, restaurants, history. Responses are grounded in a curated knowledge base (YouTube transcripts, web articles, PDFs) via RAG.
- **Plan My Day** — One click generates a full walking itinerary: optimized route order, opening hours, ticket prices, crowd predictions, lunch spots, and a feasibility score.
- **Interactive Map** — Every itinerary renders on a Folium map with walking routes, color-coded markers, and nearby suggestions.
- **Modify on the fly** — Add or remove stops from chat ("add Trevi Fountain", "remove Colosseum") and the itinerary re-optimizes automatically.
- **Multi-day support** — Mark places as visited; the planner excludes them on subsequent days.
- **Manage your knowledge base** — Add/remove YouTube videos, websites, and PDFs from the sidebar, then rebuild with one click.

![Map View](screenshot%20of%20the%20App%20Map.jpg)

## Architecture

The app is built around a **multi-agent planning workflow** orchestrated with [LangGraph](https://github.com/langchain-ai/langgraph):

```
User Query
    │
    ▼
┌─────────────────────┐
│  Place Discovery     │  RAG + gazetteer extraction
│  (multi-pass)        │  Fills available hours (~1 place / 75 min)
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Opening Hours       │  JSON data for Rome attractions
│  Tickets             │  Prices, reservation requirements
│  Travel Time (est.)  │  Manhattan-distance estimates (O(n²), instant)
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Route Optimization  │  Greedy nearest-neighbor TSP + meal breaks
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Travel Time (exact) │  OSRM Router for sequential pairs only (O(n))
│  Crowd Prediction    │  Season, time-of-day, cruise-ship heuristics
│  Cost Calculation    │  Tickets + meals + transport
│  Feasibility Check   │  Score 0–100; iterates if < 70
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Build Itinerary     │  Curated lunch spots, final schedule
└─────────────────────┘
```


### Key Components

| Module | Purpose |
|---|---|
| `src/app.py` | Streamlit UI, session management, chat interface |
| `src/rag_chain.py` | LangChain RAG pipeline (retrieve + generate) |
| `src/vector_store.py` | NumPy-based cosine similarity search (replaced FAISS for cloud compatibility) |
| `src/place_extractor.py` | Regex gazetteer with alias deduplication (e.g. "Piazza di Spagna" → "Spanish Steps") |
| `src/geocoder.py` | Nominatim HTTP API + manual coordinate fallback for 50+ landmarks |
| `src/router.py` | OSRM pedestrian routing with persistent cache |
| `src/map_builder.py` | Folium map generation with route polylines |
| `src/nearby_suggestions.py` | Suggests places near the current route |
| `src/state_persistence.py` | Survives browser refresh / battery death |
| `src/agents/` | LangGraph agent nodes (see architecture above) |
| `src/components/itinerary_display.py` | Itinerary cards, summary, preference form |
| `scripts/ingest_data.py` | Data ingestion pipeline (YouTube, web, PDF → embeddings) |

## Getting Started

### Prerequisites

- Python 3.11+
- OpenAI API key

### Install

```bash
git clone https://github.com/OrielBanne/WalkieChatbotRome.git
cd WalkieChatbotRome
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Set your API key

**Option A — Environment variable (recommended):**
```bash
export OPENAI_API_KEY='sk-...'
```

**Option B — `.env` file:**
```bash
cp .env.example .env
# Edit .env and add your key
```

### Populate the knowledge base

```bash
python scripts/ingest_data.py --sources data/sample_sources.txt
```

Or add individual sources:
```bash
python scripts/ingest_data.py \
  --youtube "https://www.youtube.com/watch?v=VIDEO_ID" \
  --web "https://example.com/rome-guide" \
  --pdf "data/pdfs/rome-guide.pdf"
```

### Run

```bash
streamlit run src/app.py
```

Opens at `http://localhost:8501`.

## Deployment (Streamlit Cloud)

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Repository: `OrielBanne/WalkieChatbotRome`, Branch: `main`, Main file: `src/app.py`
4. Add secrets (TOML format):
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
5. Deploy — the app will be live at `https://walkiechatbotrome.streamlit.app`

To use on your phone, open the URL in Safari and tap Share → "Add to Home Screen".

See [DEPLOYMENT_TO_IPHONE.md](DEPLOYMENT_TO_IPHONE.md) for the full guide.

## Managing the Knowledge Base

You can manage sources directly from the sidebar in the running app:

1. Open the **📚 Knowledge Base** section
2. Add/remove YouTube videos, websites, or PDFs
3. Click **🔄 Rebuild Knowledge Base**

The rebuild re-ingests all sources, generates embeddings, and reloads the vector store — no restart needed.

![Knowledge Base Management](rebuilding%20the%20knowledge%20base%20when%20adding%20youtube%20videos.jpg)

## Configuration

All settings are in `.env` (see [.env.example](.env.example)):

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required |
| `LLM_MODEL` | `gpt-3.5-turbo` | Chat model |
| `EMBEDDING_MODEL` | `text-embedding-ada-002` | Embedding model |
| `CHUNK_SIZE` | `1000` | Text chunk size (chars) |
| `CHUNK_OVERLAP` | `200` | Chunk overlap (chars) |
| `MAX_CONTEXT_TOKENS` | `4000` | Max conversation context |
| `RETRIEVAL_TOP_K` | `5` | Documents retrieved per query |
| `LOG_LEVEL` | `INFO` | Logging level |

## Project Structure

```
WalkieChatbotRome/
├── src/
│   ├── app.py                    # Streamlit application
│   ├── agents/                   # LangGraph planning agents
│   │   ├── workflow.py           #   Workflow graph definition
│   │   ├── models.py             #   Pydantic data models
│   │   ├── place_discovery.py    #   Multi-pass RAG place finder
│   │   ├── opening_hours.py      #   Opening hours lookup
│   │   ├── ticket.py             #   Ticket info lookup
│   │   ├── travel_time.py        #   Manhattan estimates + OSRM refinement
│   │   ├── route_optimization.py #   Greedy TSP solver
│   │   ├── crowd_prediction.py   #   Crowd level heuristics
│   │   ├── cost.py               #   Cost calculation
│   │   ├── feasibility.py        #   Feasibility scoring
│   │   └── planner.py            #   Iteration logic + itinerary builder
│   ├── components/
│   │   └── itinerary_display.py  # UI components for itinerary
│   ├── config.py                 # Environment config
│   ├── models.py                 # Core data models
│   ├── rag_chain.py              # RAG pipeline
│   ├── vector_store.py           # NumPy vector store
│   ├── place_extractor.py        # Gazetteer-based extraction
│   ├── geocoder.py               # Nominatim geocoding
│   ├── router.py                 # OSRM routing
│   ├── map_builder.py            # Folium maps
│   ├── nearby_suggestions.py     # Nearby place suggestions
│   ├── planner_integration.py    # Workflow entry point
│   ├── state_persistence.py      # App state save/restore
│   ├── session_manager.py        # Chat session persistence
│   ├── context_manager.py        # Token-aware context building
│   ├── loaders.py                # YouTube/Web/PDF loaders
│   ├── chunker.py                # Text chunking
│   └── logging_config.py         # Logging setup
├── scripts/
│   └── ingest_data.py            # Data ingestion CLI
├── data/
│   ├── vector_store/             # Embeddings + documents
│   ├── opening_hours.json        # Opening hours database
│   ├── ticket_info.json          # Ticket prices database
│   ├── crowd_patterns.json       # Crowd prediction patterns
│   └── sample_sources.txt        # Default source URLs
├── tests/                        # Test suite (35+ test files)
├── .streamlit/config.toml        # Streamlit theme config
├── requirements.txt              # Python dependencies
└── .env.example                  # Environment template
```

## Testing

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific module
pytest tests/test_place_extractor.py -v
```

## Tech Stack

- **UI**: [Streamlit](https://streamlit.io) + [streamlit-folium](https://github.com/randyzwitch/streamlit-folium)
- **LLM**: [OpenAI GPT-3.5-turbo](https://platform.openai.com/docs) via [LangChain](https://github.com/langchain-ai/langchain)
- **Workflow**: [LangGraph](https://github.com/langchain-ai/langgraph) (multi-agent state graph)
- **Embeddings**: OpenAI `text-embedding-ada-002` + NumPy cosine similarity
- **Maps**: [Folium](https://python-visualization.github.io/folium/)
- **Routing**: [OSRM](https://project-osrm.org/) (Open Source Routing Machine)
- **Geocoding**: [Nominatim](https://nominatim.org/) (OpenStreetMap)
- **Route optimization**: Greedy nearest-neighbor TSP

## License

MIT — see [LICENSE](LICENSE).

## Author

**Oriel Banne** — [GitHub](https://github.com/OrielBanne)
