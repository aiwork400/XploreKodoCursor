"""
Rebuild Vector Store for RAG

This script:
1. Scans knowledge_base/ directory for PDF/TXT/MD files
2. Chunks documents using LangChain's RecursiveCharacterTextSplitter
3. Initializes FAISS with HuggingFace embeddings
4. Stores chunks in faiss_index/ directory
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from utils.knowledge_base_loader import get_all_documents, get_knowledge_base_path

import os


def rebuild_vector_store():
    """
    Rebuild the FAISS vector store from knowledge_base/ documents.
    
    Creates/updates the faiss_index/ directory with embeddings.
    """
    print("=" * 80)
    print("Rebuilding Vector Store for RAG (FAISS)")
    print("=" * 80)
    print()
    
    # Step 1: Load documents from knowledge_base/
    print("[1/4] Loading documents from knowledge_base/...")
    documents = get_all_documents()
    
    if not documents:
        print("[WARN] No documents found in knowledge_base/ directory.")
        print("[INFO] Please add PDF/TXT/MD files to knowledge_base/ and try again.")
        return
    
    print(f"   Found {len(documents)} document(s):")
    for doc in documents:
        print(f"   - {doc['name']} ({doc['type']})")
    print()
    
    # Step 2: Chunk documents using RecursiveCharacterTextSplitter
    print("[2/4] Chunking documents...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    all_documents = []  # List of Document objects for FAISS
    
    for doc in documents:
        content = doc['content']
        chunks = text_splitter.split_text(content)
        
        print(f"   {doc['name']}: {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            # Create Document objects with metadata for FAISS
            doc_obj = Document(
                page_content=chunk,
                metadata={
                    'source': doc['name'],
                    'source_path': doc['path'],
                    'source_type': doc['type'],
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
            )
            all_documents.append(doc_obj)
    
    print(f"   Total chunks created: {len(all_documents)}")
    print()
    
    # Step 3: Initialize embeddings model
    print("[3/4] Initializing HuggingFace embeddings model...")
    try:
        # Use all-MiniLM-L6-v2 model (lightweight, fast, good quality)
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},  # Use CPU by default (can change to 'cuda' if GPU available)
            encode_kwargs={'normalize_embeddings': True}
        )
        print("   Model loaded: sentence-transformers/all-MiniLM-L6-v2")
        print("   Embedding dimension: 384")
    except Exception as e:
        print(f"[ERROR] Failed to load embeddings model: {e}")
        print("[INFO] Make sure sentence-transformers is installed: pip install sentence-transformers")
        return
    print()
    
    # Step 4: Initialize FAISS and store embeddings
    print("[4/4] Storing embeddings in FAISS...")
    vector_store_path = project_root / "faiss_index"
    
    # Remove existing vector store if it exists (to rebuild from scratch)
    if vector_store_path.exists():
        print(f"   Removing existing vector store at: {vector_store_path}")
        import shutil
        shutil.rmtree(vector_store_path)
    
    try:
        # Create FAISS vector store from documents
        vector_store = FAISS.from_documents(
            documents=all_documents,
            embedding=embeddings
        )
        
        # Save the FAISS index
        vector_store.save_local(str(vector_store_path))
        
        print(f"   Vector store created at: {vector_store_path}")
        print(f"   Total documents stored: {len(all_documents)}")
        print()
        
        # Verify the store
        print("[VERIFY] Testing vector store...")
        test_query = "Xplora Kodo"
        results = vector_store.similarity_search(test_query, k=2)
        print(f"   Test query: '{test_query}'")
        print(f"   Retrieved {len(results)} result(s)")
        if results:
            print(f"   First result preview: {results[0].page_content[:100]}...")
        
        print()
        print("=" * 80)
        print("[SUCCESS] Vector store rebuilt successfully!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. The vector store is ready for RAG queries")
        print("2. Use utils/rag_query.py to perform similarity searches")
        print("3. Integrate RAG into Sensei agent logic")
        
    except Exception as e:
        print(f"[ERROR] Failed to create vector store: {e}")
        import traceback
        traceback.print_exc()
        return


if __name__ == "__main__":
    rebuild_vector_store()

