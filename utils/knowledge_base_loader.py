"""
Knowledge Base Loader Utility

Utility functions for loading documents from knowledge_base/ directory for RAG-based conversations.

This module provides functions to:
- Scan knowledge_base/ directory for PDF, TXT, and MD files
- Load document content for RAG processing
- Prepare documents for vector store indexing
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Optional
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def get_knowledge_base_path() -> Path:
    """
    Get the path to the knowledge_base directory.
    
    Returns:
        Path object pointing to knowledge_base/ directory at project root
    """
    return project_root / "knowledge_base"


def scan_knowledge_base() -> List[Path]:
    """
    Scan knowledge_base/ directory for supported document files.
    
    Supported formats: PDF (.pdf), Text (.txt), Markdown (.md)
    
    Returns:
        List of Path objects for all found documents
    """
    kb_dir = get_knowledge_base_path()
    
    if not kb_dir.exists():
        kb_dir.mkdir(exist_ok=True)
        return []
    
    documents = []
    documents.extend(kb_dir.glob("*.pdf"))
    documents.extend(kb_dir.glob("*.txt"))
    documents.extend(kb_dir.glob("*.md"))
    
    return sorted(documents)


def load_document_content(file_path: Path) -> Optional[str]:
    """
    Load text content from a document file.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Document content as string, or None if file cannot be read
    """
    try:
        if file_path.suffix.lower() == '.pdf':
            # PDF processing - requires PyMuPDF (fitz)
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                text_parts = []
                for page in doc:
                    text = page.get_text()
                    if text.strip():
                        text_parts.append(text)
                doc.close()
                return "\n\n".join(text_parts) if text_parts else None
            except ImportError:
                print(f"[WARN] PyMuPDF not available. Cannot read PDF: {file_path.name}")
                return None
        elif file_path.suffix.lower() in ['.txt', '.md']:
            # Text and Markdown files
            return file_path.read_text(encoding='utf-8')
        else:
            print(f"[WARN] Unsupported file format: {file_path.suffix}")
            return None
    except Exception as e:
        print(f"[ERROR] Error loading document {file_path.name}: {e}")
        return None


def get_all_documents() -> List[Dict[str, str]]:
    """
    Get all documents from knowledge_base/ with their content.
    
    Returns:
        List of dictionaries with keys: 'path', 'name', 'content', 'type'
    """
    documents = scan_knowledge_base()
    result = []
    
    for doc_path in documents:
        content = load_document_content(doc_path)
        if content:
            result.append({
                'path': str(doc_path),
                'name': doc_path.name,
                'content': content,
                'type': doc_path.suffix.lower()
            })
    
    return result


def get_document_count() -> Dict[str, int]:
    """
    Get count of documents by type in knowledge_base/.
    
    Returns:
        Dictionary with counts: {'pdf': int, 'txt': int, 'md': int, 'total': int}
    """
    documents = scan_knowledge_base()
    counts = {'pdf': 0, 'txt': 0, 'md': 0, 'total': len(documents)}
    
    for doc in documents:
        ext = doc.suffix.lower()
        if ext == '.pdf':
            counts['pdf'] += 1
        elif ext == '.txt':
            counts['txt'] += 1
        elif ext == '.md':
            counts['md'] += 1
    
    return counts


if __name__ == "__main__":
    # Test the utility functions
    print("Knowledge Base Loader Utility - Test")
    print("=" * 50)
    
    kb_path = get_knowledge_base_path()
    print(f"Knowledge Base Path: {kb_path}")
    print(f"Exists: {kb_path.exists()}")
    
    documents = scan_knowledge_base()
    print(f"\nFound {len(documents)} document(s):")
    for doc in documents:
        print(f"  - {doc.name} ({doc.suffix})")
    
    counts = get_document_count()
    print(f"\nDocument Counts:")
    print(f"  PDF: {counts['pdf']}")
    print(f"  TXT: {counts['txt']}")
    print(f"  MD:  {counts['md']}")
    print(f"  Total: {counts['total']}")

