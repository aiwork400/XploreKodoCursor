"""
RAG Query Utility

Utility functions for querying the FAISS vector store to retrieve relevant context
from the Xplora Kodo knowledge base for RAG-based conversations.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("[WARN] LangChain/FAISS not available. RAG features disabled.")

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type
    )
    from google.api_core import exceptions as google_exceptions
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    print("[WARN] tenacity not available. Retry logic disabled.")


# Global vector store instance (initialized on first use)
_vector_store: Optional[FAISS] = None
_embeddings: Optional[HuggingFaceEmbeddings] = None


def initialize_vector_store() -> bool:
    """
    Initialize the FAISS vector store connection.
    
    Returns:
        True if initialization successful, False otherwise
    """
    global _vector_store, _embeddings
    
    if not RAG_AVAILABLE:
        return False
    
    if _vector_store is not None:
        return True  # Already initialized
    
    try:
        vector_store_path = project_root / "faiss_index"
        
        if not vector_store_path.exists():
            print("[WARN] Vector store not found. Run database/rebuild_vector_store.py first.")
            return False
        
        # Initialize embeddings
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Load existing FAISS vector store
        _vector_store = FAISS.load_local(
            folder_path=str(vector_store_path),
            embeddings=_embeddings,
            allow_dangerous_deserialization=True
        )
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize vector store: {e}")
        return False


def _query_with_retry(query: str, k: int) -> List[str]:
    """
    Internal function to perform FAISS similarity search with retry logic.
    
    Args:
        query: User's question or message
        k: Number of relevant chunks to retrieve
        
    Returns:
        List of relevant text chunks from the knowledge base
    """
    # Perform similarity search
    results = _vector_store.similarity_search(query, k=k)
    
    # Extract text content from results
    chunks = [result.page_content for result in results]
    return chunks


def _retryable_query(query: str, k: int) -> List[str]:
    """
    Retryable wrapper for FAISS query with exponential backoff for 429 errors.
    
    Args:
        query: User's question or message
        k: Number of relevant chunks to retrieve
        
    Returns:
        List of relevant text chunks from the knowledge base
    """
    return _query_with_retry(query, k)


def query_knowledge_base(query: str, k: int = 3) -> List[str]:
    """
    Query the knowledge base for relevant context with retry logic for API errors.
    
    This function queries the FAISS index (faiss_index/) to retrieve relevant context
    from the Xplora Kodo Manifesto and other knowledge base documents.
    
    Args:
        query: User's question or message
        k: Number of relevant chunks to retrieve (default: 3)
        
    Returns:
        List of relevant text chunks from the knowledge base
    """
    if not initialize_vector_store():
        return []
    
    try:
        # Apply retry logic if tenacity is available
        if TENACITY_AVAILABLE:
            # Retry on Resource Exhausted (429) errors with exponential backoff
            @retry(
                stop=stop_after_attempt(5),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry=retry_if_exception_type(google_exceptions.ResourceExhausted),
                reraise=True
            )
            def _retry_wrapper():
                return _query_with_retry(query, k)
            
            return _retry_wrapper()
        else:
            # Fallback without retry logic
            return _query_with_retry(query, k)
        
    except Exception as e:
        # Handle errors (including retry exhaustion)
        error_msg = str(e)
        if "429" in error_msg or "Resource Exhausted" in error_msg:
            print(f"[WARN] Rate limit hit after retries. Please try again in a moment: {e}")
        else:
            print(f"[ERROR] Failed to query knowledge base: {e}")
        return []


def get_rag_context(user_message: str, max_chunks: int = 3) -> str:
    """
    Get RAG context for a user message to inject into LLM prompt.
    
    Args:
        user_message: User's message/query
        max_chunks: Maximum number of relevant chunks to retrieve
        
    Returns:
        Formatted context string to inject into system prompt
    """
    chunks = query_knowledge_base(user_message, k=max_chunks)
    
    if not chunks:
        return ""
    
    context_parts = []
    context_parts.append("**Relevant Context from Xplora Kodo Knowledge Base:**")
    context_parts.append("")
    
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[Context {i}]")
        context_parts.append(chunk.strip())
        context_parts.append("")
    
    return "\n".join(context_parts)


if __name__ == "__main__":
    # Test the RAG query utility
    print("RAG Query Utility - Test")
    print("=" * 50)
    
    if not initialize_vector_store():
        print("Vector store not available. Run database/rebuild_vector_store.py first.")
    else:
        print("Vector store initialized successfully.")
        print()
        
        # Test query
        test_query = "What is Xplora Kodo?"
        print(f"Test query: '{test_query}'")
        print()
        
        context = get_rag_context(test_query, max_chunks=2)
        if context:
            print("Retrieved context:")
            print(context)
        else:
            print("No context retrieved.")

