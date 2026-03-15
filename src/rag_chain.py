"""
RAG Chain implementation using LangChain for retrieval-augmented generation.

This module provides a RAGChain class that orchestrates the retrieval and generation
pipeline using LangChain's RetrievalQA chain with custom prompts for Rome-specific queries.
"""

from typing import Iterator, Optional
from langchain_classic.chains import RetrievalQA
from langchain_core.language_models import BaseLLM
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import StreamingStdOutCallbackHandler
import logging
import time


logger = logging.getLogger(__name__)


class RAGChainError(Exception):
    """Base exception for RAG chain errors."""
    pass


class RAGChain:
    """
    RAG Chain for retrieval-augmented generation with Rome-specific prompts.
    
    This class orchestrates the retrieval and generation pipeline using LangChain's
    RetrievalQA chain. It retrieves relevant document chunks from a vector store
    and generates contextually grounded responses using an LLM.
    
    Attributes:
        llm: Language model for generation
        retriever: Document retriever for context
        chain: LangChain RetrievalQA chain
        prompt_template: Custom prompt emphasizing Rome information
    """
    
    # Custom prompt template emphasizing Rome-specific information
    ROME_PROMPT_TEMPLATE = """You are a knowledgeable and friendly travel assistant specializing in Rome, Italy. 
Your role is to help users discover and learn about places of interest in Rome, including landmarks, 
restaurants, attractions, and points of interest.

Use the following pieces of context to answer the question. The context comes from curated sources 
about Rome and its places. Always prioritize information from the context over general knowledge.

If the context doesn't contain enough information to fully answer the question, say so honestly 
and provide what information you can. If the question is not about Rome or places in Rome, 
politely redirect the conversation back to Rome-related topics.

Maintain a conversational, helpful tone appropriate for travel assistance. When discussing places, 
include relevant details like location, historical significance, visiting tips, or recommendations.

Context from knowledge base:
{context}

Conversation context:
{chat_history}

Question: {question}

Helpful Answer:"""
    
    def __init__(self, llm: BaseLLM, retriever: BaseRetriever):
        """
        Initialize the RAG chain.
        
        Args:
            llm: Language model for generation
            retriever: Document retriever for context (should retrieve top-k=5)
        """
        self.llm = llm
        self.retriever = retriever
        
        # Create custom prompt
        self.prompt_template = PromptTemplate(
            template=self.ROME_PROMPT_TEMPLATE,
            input_variables=["context", "chat_history", "question"]
        )

    def invoke(self, query: str, context: str = "") -> str:
        """
        Generate a response for the given query with conversation context.
        
        This method retrieves relevant documents and generates a grounded response
        using the LLM. It includes retry logic for API failures.
        
        Args:
            query: User's question or query
            context: Conversation history or additional context
            
        Returns:
            Generated response text
            
        Raises:
            RAGChainError: If generation fails after retries
        """
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Retrieve relevant documents
                try:
                    docs = self.retriever.get_relevant_documents(query)
                    context_text = "\n\n".join([doc.page_content for doc in docs[:5]])
                except Exception as retrieval_error:
                    logger.warning(f"Document retrieval failed: {retrieval_error}")
                    docs = []
                    context_text = "No specific documents available."
                
                # Format the prompt directly
                prompt_text = self.prompt_template.format(
                    context=context_text,
                    chat_history=context,
                    question=query
                )
                
                # Invoke the LLM directly
                result = self.llm.invoke(prompt_text)
                
                # Extract the answer
                if hasattr(result, "content"):
                    return result.content
                else:
                    return str(result)
                
            except Exception as e:
                logger.warning(
                    f"RAG chain invocation failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                )
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    # Final attempt failed
                    logger.error(f"RAG chain invocation failed after {max_retries} attempts: {str(e)}")
                    raise RAGChainError(
                        "I'm having trouble connecting to my knowledge base. "
                        "Please try again in a moment."
                    ) from e
    
    def stream(self, query: str, context: str = "") -> Iterator[str]:
        """
        Generate a streaming response for the given query with conversation context.
        
        This method retrieves relevant documents and generates a response in chunks,
        allowing for real-time display. It includes retry logic for API failures.
        
        Args:
            query: User's question or query
            context: Conversation history or additional context
            
        Yields:
            Response text chunks as they are generated
            
        Raises:
            RAGChainError: If generation fails after retries
        """
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Create a streaming callback handler
                streaming_handler = StreamingStdOutCallbackHandler()
                
                # Create a new LLM instance with streaming enabled
                streaming_llm = self.llm
                if hasattr(streaming_llm, "streaming"):
                    streaming_llm.streaming = True
                if hasattr(streaming_llm, "callbacks"):
                    streaming_llm.callbacks = [streaming_handler]
                
                # Prepare input with conversation context
                input_data = {
                    "query": query,
                    "chat_history": context
                }
                
                # For streaming, we need to use the chain differently
                # Since RetrievalQA doesn't natively support streaming well,
                # we'll retrieve documents first, then stream the generation
                
                # Retrieve relevant documents (with fallback for empty vector store)
                try:
                    docs = self.retriever.get_relevant_documents(query)
                    context_text = "\n\n".join([doc.page_content for doc in docs[:5]])
                except Exception as retrieval_error:
                    # Vector store is empty or unavailable - use LLM without retrieval
                    logger.warning(f"Document retrieval failed, using LLM without context: {retrieval_error}")
                    docs = []
                    context_text = "No specific documents available. Please use your general knowledge."
                
                # Format the prompt
                prompt_text = self.prompt_template.format(
                    context=context_text,
                    chat_history=context,
                    question=query
                )
                
                # Stream the response
                if hasattr(self.llm, "stream"):
                    # Use native streaming if available
                    for chunk in self.llm.stream(prompt_text):
                        if hasattr(chunk, "content"):
                            yield chunk.content
                        else:
                            yield str(chunk)
                else:
                    # Fallback to non-streaming
                    response = self.llm.invoke(prompt_text)
                    if hasattr(response, "content"):
                        yield response.content
                    else:
                        yield str(response)
                
                # Success, break retry loop
                break
                
            except Exception as e:
                logger.warning(
                    f"RAG chain streaming failed (attempt {attempt + 1}/{max_retries}): {str(e)}"
                )
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    # Final attempt failed
                    logger.error(f"RAG chain streaming failed after {max_retries} attempts: {str(e)}")
                    raise RAGChainError(
                        "I'm having trouble connecting to my knowledge base. "
                        "Please try again in a moment."
                    ) from e
