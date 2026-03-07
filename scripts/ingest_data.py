#!/usr/bin/env python3
"""
Data ingestion script for Rome Places Chatbot.

This script ingests content from various sources (YouTube videos, web pages, PDFs),
chunks the text, generates embeddings, and stores them in a FAISS vector store.

Usage:
    python scripts/ingest_data.py --youtube URL1 URL2 --web URL3 --pdf path/to/file.pdf
    python scripts/ingest_data.py --sources sources.txt --output data/vector_store
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List
from tqdm import tqdm
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.loaders import YouTubeLoader, WebLoader, PDFLoader
from src.chunker import TextChunker
from src.vector_store import VectorStore, VectorStoreError
from langchain_core.documents import Document


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_sources_from_file(file_path: str) -> dict:
    """
    Load data sources from a text file.
    
    File format:
        youtube: URL
        web: URL
        pdf: /path/to/file.pdf
    
    Args:
        file_path: Path to sources file
        
    Returns:
        Dictionary with keys 'youtube', 'web', 'pdf' containing lists of sources
    """
    sources = {'youtube': [], 'web': [], 'pdf': []}
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if ':' in line:
                    source_type, source_value = line.split(':', 1)
                    source_type = source_type.strip().lower()
                    source_value = source_value.strip()
                    
                    if source_type in sources:
                        sources[source_type].append(source_value)
    except Exception as e:
        logger.error(f"Failed to load sources from file {file_path}: {e}")
        raise
    
    return sources


def ingest_youtube_videos(urls: List[str], chunker: TextChunker) -> List[Document]:
    """
    Ingest YouTube videos and chunk their transcripts.
    
    Args:
        urls: List of YouTube video URLs
        chunker: TextChunker instance
        
    Returns:
        List of chunked documents
    """
    loader = YouTubeLoader()
    all_chunks = []
    
    logger.info(f"Ingesting {len(urls)} YouTube video(s)...")
    
    for url in tqdm(urls, desc="YouTube videos"):
        try:
            # Load transcript
            doc = loader.load_transcript(url)
            logger.info(f"Loaded transcript from {url} ({len(doc.page_content)} chars)")
            
            # Chunk the transcript
            chunks = chunker.chunk_text(doc.page_content)
            logger.info(f"Created {len(chunks)} chunks from video")
            
            # Create Document objects for each chunk
            for i, chunk in enumerate(chunks):
                chunk_doc = Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        'chunk_id': i,
                        'total_chunks': len(chunks)
                    }
                )
                all_chunks.append(chunk_doc)
                
        except Exception as e:
            logger.error(f"Failed to ingest YouTube video {url}: {e}")
            continue
    
    return all_chunks


def ingest_webpages(urls: List[str], chunker: TextChunker) -> List[Document]:
    """
    Ingest web pages and chunk their content.
    
    Args:
        urls: List of web page URLs
        chunker: TextChunker instance
        
    Returns:
        List of chunked documents
    """
    loader = WebLoader()
    all_chunks = []
    
    logger.info(f"Ingesting {len(urls)} web page(s)...")
    
    for url in tqdm(urls, desc="Web pages"):
        try:
            # Load webpage
            doc = loader.load_webpage(url)
            logger.info(f"Loaded webpage from {url} ({len(doc.page_content)} chars)")
            
            # Chunk the content
            chunks = chunker.chunk_text(doc.page_content)
            logger.info(f"Created {len(chunks)} chunks from webpage")
            
            # Create Document objects for each chunk
            for i, chunk in enumerate(chunks):
                chunk_doc = Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        'chunk_id': i,
                        'total_chunks': len(chunks)
                    }
                )
                all_chunks.append(chunk_doc)
                
        except Exception as e:
            logger.error(f"Failed to ingest webpage {url}: {e}")
            continue
    
    return all_chunks


def ingest_pdfs(file_paths: List[str], chunker: TextChunker) -> List[Document]:
    """
    Ingest PDF files and chunk their content.
    
    Args:
        file_paths: List of PDF file paths
        chunker: TextChunker instance
        
    Returns:
        List of chunked documents
    """
    loader = PDFLoader()
    all_chunks = []
    
    logger.info(f"Ingesting {len(file_paths)} PDF file(s)...")
    
    for file_path in tqdm(file_paths, desc="PDF files"):
        try:
            # Load PDF (returns list of documents, one per page)
            docs = loader.load_pdf(file_path)
            logger.info(f"Loaded {len(docs)} pages from {file_path}")
            
            # Chunk each page
            for doc in docs:
                chunks = chunker.chunk_text(doc.page_content)
                
                # Create Document objects for each chunk
                for i, chunk in enumerate(chunks):
                    chunk_doc = Document(
                        page_content=chunk,
                        metadata={
                            **doc.metadata,
                            'chunk_id': i,
                            'total_chunks': len(chunks)
                        }
                    )
                    all_chunks.append(chunk_doc)
            
            logger.info(f"Created {len(all_chunks)} total chunks from PDF")
                
        except Exception as e:
            logger.error(f"Failed to ingest PDF {file_path}: {e}")
            continue
    
    return all_chunks


def main():
    """Main ingestion script."""
    parser = argparse.ArgumentParser(
        description='Ingest data from various sources into FAISS vector store'
    )
    
    # Source arguments
    parser.add_argument(
        '--youtube',
        nargs='+',
        default=[],
        help='YouTube video URLs to ingest'
    )
    parser.add_argument(
        '--web',
        nargs='+',
        default=[],
        help='Web page URLs to ingest'
    )
    parser.add_argument(
        '--pdf',
        nargs='+',
        default=[],
        help='PDF file paths to ingest'
    )
    parser.add_argument(
        '--sources',
        type=str,
        help='Path to file containing sources (one per line, format: type: value)'
    )
    
    # Output arguments
    parser.add_argument(
        '--output',
        type=str,
        default='data/vector_store',
        help='Output directory for FAISS index (default: data/vector_store)'
    )
    
    # Chunking arguments
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=1000,
        help='Chunk size in characters (default: 1000)'
    )
    parser.add_argument(
        '--overlap',
        type=int,
        default=200,
        help='Overlap between chunks in characters (default: 200)'
    )
    
    # Other arguments
    parser.add_argument(
        '--append',
        action='store_true',
        help='Append to existing vector store instead of creating new one'
    )
    
    args = parser.parse_args()
    
    # Collect all sources
    youtube_urls = list(args.youtube)
    web_urls = list(args.web)
    pdf_paths = list(args.pdf)
    
    # Load from sources file if provided
    if args.sources:
        logger.info(f"Loading sources from {args.sources}")
        sources = load_sources_from_file(args.sources)
        youtube_urls.extend(sources['youtube'])
        web_urls.extend(sources['web'])
        pdf_paths.extend(sources['pdf'])
    
    # Check if any sources provided
    if not youtube_urls and not web_urls and not pdf_paths:
        logger.error("No sources provided. Use --youtube, --web, --pdf, or --sources")
        parser.print_help()
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Rome Places Chatbot - Data Ingestion")
    logger.info("=" * 60)
    logger.info(f"YouTube videos: {len(youtube_urls)}")
    logger.info(f"Web pages: {len(web_urls)}")
    logger.info(f"PDF files: {len(pdf_paths)}")
    logger.info(f"Output directory: {args.output}")
    logger.info(f"Chunk size: {args.chunk_size}, Overlap: {args.overlap}")
    logger.info("=" * 60)
    
    # Initialize chunker
    chunker = TextChunker(chunk_size=args.chunk_size, overlap=args.overlap)
    
    # Ingest all sources
    all_documents = []
    
    if youtube_urls:
        youtube_docs = ingest_youtube_videos(youtube_urls, chunker)
        all_documents.extend(youtube_docs)
    
    if web_urls:
        web_docs = ingest_webpages(web_urls, chunker)
        all_documents.extend(web_docs)
    
    if pdf_paths:
        pdf_docs = ingest_pdfs(pdf_paths, chunker)
        all_documents.extend(pdf_docs)
    
    logger.info("=" * 60)
    logger.info(f"Total documents to ingest: {len(all_documents)}")
    logger.info("=" * 60)
    
    if not all_documents:
        logger.error("No documents were successfully loaded. Exiting.")
        sys.exit(1)
    
    # Initialize vector store
    try:
        vector_store = VectorStore()
        
        # Load existing index if appending
        if args.append and os.path.exists(args.output):
            logger.info(f"Loading existing vector store from {args.output}")
            vector_store.load(args.output)
            logger.info(f"Existing documents: {len(vector_store)}")
        
        # Add documents with progress bar
        logger.info("Generating embeddings and adding to vector store...")
        logger.info("(This may take a while depending on the number of documents)")
        
        # Add documents in batches to show progress
        batch_size = 10
        for i in tqdm(range(0, len(all_documents), batch_size), desc="Adding documents"):
            batch = all_documents[i:i + batch_size]
            vector_store.add_documents(batch)
        
        logger.info(f"Successfully added {len(all_documents)} documents")
        logger.info(f"Total documents in vector store: {len(vector_store)}")
        
        # Save vector store
        logger.info(f"Saving vector store to {args.output}")
        vector_store.save(args.output)
        logger.info("Vector store saved successfully!")
        
    except VectorStoreError as e:
        logger.error(f"Vector store error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("Ingestion complete!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
