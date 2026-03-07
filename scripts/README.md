# Data Ingestion Script

This directory contains the data ingestion script for the Rome Places Chatbot.

## Overview

The `ingest_data.py` script ingests content from various sources (YouTube videos, web pages, PDFs), chunks the text, generates embeddings using OpenAI, and stores them in a FAISS vector store.

## Usage

### Basic Usage

Ingest from command-line arguments:

```bash
# Ingest YouTube videos
python scripts/ingest_data.py --youtube https://www.youtube.com/watch?v=VIDEO_ID

# Ingest web pages
python scripts/ingest_data.py --web https://example.com/rome-guide

# Ingest PDF files
python scripts/ingest_data.py --pdf data/rome_guide.pdf

# Combine multiple sources
python scripts/ingest_data.py \
  --youtube https://www.youtube.com/watch?v=VIDEO_ID \
  --web https://example.com/rome-guide \
  --pdf data/rome_guide.pdf
```

### Using a Sources File

Create a text file with sources (one per line):

```
youtube: https://www.youtube.com/watch?v=VIDEO_ID
web: https://example.com/rome-guide
pdf: data/rome_guide.pdf
```

Then run:

```bash
python scripts/ingest_data.py --sources data/sample_sources.txt
```

### Advanced Options

```bash
# Specify output directory
python scripts/ingest_data.py --sources data/sources.txt --output data/my_vector_store

# Customize chunking parameters
python scripts/ingest_data.py --sources data/sources.txt --chunk-size 1500 --overlap 300

# Append to existing vector store
python scripts/ingest_data.py --sources data/new_sources.txt --append
```

## Command-Line Arguments

- `--youtube URL [URL ...]`: YouTube video URLs to ingest
- `--web URL [URL ...]`: Web page URLs to ingest
- `--pdf PATH [PATH ...]`: PDF file paths to ingest
- `--sources FILE`: Path to file containing sources (format: `type: value`)
- `--output DIR`: Output directory for FAISS index (default: `data/vector_store`)
- `--chunk-size N`: Chunk size in characters (default: 1000)
- `--overlap N`: Overlap between chunks in characters (default: 200)
- `--append`: Append to existing vector store instead of creating new one

## Requirements

Make sure you have set up your OpenAI API key in the `.env` file:

```
OPENAI_API_KEY=your_api_key_here
```

## Output

The script creates a FAISS vector store in the specified output directory with two files:
- `faiss.index`: The FAISS index containing embeddings
- `documents.pkl`: Pickled document metadata

## Progress Indicators

The script shows progress bars for:
- Loading content from each source type
- Adding documents to the vector store (in batches)

## Error Handling

- Failed sources are logged but don't stop the ingestion process
- The script will retry embedding generation up to 3 times with exponential backoff
- If no documents are successfully loaded, the script exits with an error

## Examples

### Example 1: Ingest Rome tourism content

```bash
python scripts/ingest_data.py \
  --youtube https://www.youtube.com/watch?v=rome_tour \
  --web https://www.rome.info/places/ \
  --output data/rome_vector_store
```

### Example 2: Append new content to existing store

```bash
# First ingestion
python scripts/ingest_data.py --sources data/initial_sources.txt

# Later, add more content
python scripts/ingest_data.py --sources data/additional_sources.txt --append
```

### Example 3: Custom chunking for longer documents

```bash
python scripts/ingest_data.py \
  --pdf data/long_rome_guide.pdf \
  --chunk-size 2000 \
  --overlap 400
```
