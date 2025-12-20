"""
Extract text from Japanese caregiving training PDFs and store in knowledge_base table.

Uses PyMuPDF to extract text from PDF files and stores concepts in PostgreSQL.
"""

from __future__ import annotations

import re
from pathlib import Path

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import fitz  # PyMuPDF
from sqlalchemy.orm import Session

from database.db_manager import KnowledgeBase, SessionLocal

# PDF files to process
PDF_FILES = [
    "Nihongo Sou Matome N3 - Bunpou.pdf",
    "Minna_No_Nihongo Part 1.pdf",
]


def is_image_based_pdf(pdf_path: Path, sample_pages: int = 3) -> tuple[bool, float]:
    """
    Check if PDF is image-based by analyzing text extraction success rate.
    
    Returns:
        (is_image_based: bool, text_extraction_rate: float)
        - is_image_based: True if less than 10% of pages have extractable text
        - text_extraction_rate: Percentage of pages with extractable text (0.0 to 1.0)
    """
    try:
        doc = fitz.open(pdf_path)
        total_pages = min(len(doc), sample_pages)
        
        if total_pages == 0:
            return True, 0.0
        
        pages_with_text = 0
        
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text()
            
            # Try alternative extraction methods
            if not text.strip():
                blocks = page.get_text("blocks")
                if blocks:
                    text = "\n".join([block[4] for block in blocks if len(block) > 4 and isinstance(block[4], str)])
            
            if text.strip():
                pages_with_text += 1
        
        doc.close()
        
        extraction_rate = pages_with_text / total_pages
        is_image_based = extraction_rate < 0.1  # Less than 10% of pages have text
        
        return is_image_based, extraction_rate
        
    except Exception as e:
        print(f"   [WARN] Error checking PDF type: {e}")
        return True, 0.0


def suggest_alternative_formats(pdf_path: Path) -> None:
    """
    Print suggestions for alternative file formats when PDF is image-based.
    """
    print("\n" + "=" * 80)
    print("[INFO] IMAGE-BASED PDF DETECTED - Alternative Format Suggestions")
    print("=" * 80)
    print(f"\nFile: {pdf_path.name}")
    print("\nRecommended alternative formats (in order of preference):")
    print("\n1. TEXT FILES (.txt, .md)")
    print("   - Best for: Pure text content")
    print("   - Advantages: Fastest processing, perfect text extraction, smallest file size")
    print("   - How to convert: Copy text from PDF and save as .txt or .md")
    print("   - Example: 'Nihongo_Sou_Matome_N3_Bunpou.txt'")
    
    print("\n2. MARKDOWN FILES (.md)")
    print("   - Best for: Structured text with formatting")
    print("   - Advantages: Preserves headings, lists, formatting; easy to read")
    print("   - How to convert: Export from PDF reader or manually format")
    print("   - Example: 'Nihongo_Sou_Matome_N3_Bunpou.md'")
    
    print("\n3. DOCX FILES (.docx)")
    print("   - Best for: Documents with formatting, tables, images")
    print("   - Advantages: Preserves structure, supports tables and images")
    print("   - How to convert: Use Microsoft Word, LibreOffice, or online converters")
    print("   - Note: Requires python-docx library for extraction")
    
    print("\n4. HTML FILES (.html)")
    print("   - Best for: Web-formatted content")
    print("   - Advantages: Preserves formatting, links, structure")
    print("   - How to convert: Export from PDF reader or use online tools")
    
    print("\n5. RTF FILES (.rtf)")
    print("   - Best for: Rich text with formatting")
    print("   - Advantages: Cross-platform compatibility, preserves formatting")
    print("   - How to convert: Export from PDF reader")
    
    print("\n6. OCR PROCESSING (Keep PDF, use OCR)")
    print("   - Best for: When you must keep PDF format")
    print("   - Advantages: Converts image-based PDF to searchable text")
    print("   - Tools: Tesseract OCR, Adobe Acrobat OCR, online OCR services")
    print("   - Note: Requires additional setup and processing time")
    
    print("\n" + "-" * 80)
    print("RECOMMENDATION:")
    print("For Japanese caregiving training materials, we recommend:")
    print("  - Primary: .txt or .md files (if you can extract text manually)")
    print("  - Secondary: OCR processing (if PDF must be kept)")
    print("  - Alternative: .docx files (if formatting is important)")
    print("\nPlace converted files in the project root directory.")
    print("=" * 80 + "\n")


def extract_text_from_pdf(pdf_path: Path) -> list[dict]:
    """
    Extract text from PDF file and split into concepts.
    
    Returns list of dictionaries with:
    - concept_title: Extracted title or heading
    - concept_content: Full text content
    - page_number: Page number
    """
    concepts = []
    
    # Check if PDF is image-based before processing
    is_image_based, extraction_rate = is_image_based_pdf(pdf_path)
    
    if is_image_based:
        print(f"\n[WARN] Image-based PDF detected (text extraction rate: {extraction_rate:.1%})")
        suggest_alternative_formats(pdf_path)
        print("[INFO] Attempting to extract text anyway (may result in empty concepts)...")
    
    try:
        doc = fitz.open(pdf_path)
        print(f"   [DEBUG] PDF opened: {len(doc)} pages")
        
        pages_without_text = 0
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Try multiple extraction methods
            text = page.get_text()
            
            # If no text, try getting text blocks
            if not text.strip():
                blocks = page.get_text("blocks")
                if blocks:
                    text = "\n".join([block[4] for block in blocks if len(block) > 4 and isinstance(block[4], str)])
            
            # If still no text, try getting text as dict
            if not text.strip():
                text_dict = page.get_text("dict")
                if text_dict and "blocks" in text_dict:
                    text_parts = []
                    for block in text_dict["blocks"]:
                        if "lines" in block:
                            for line in block["lines"]:
                                if "spans" in line:
                                    for span in line["spans"]:
                                        if "text" in span:
                                            text_parts.append(span["text"])
                    text = "\n".join(text_parts)
            
            if not text.strip():
                pages_without_text += 1
                if page_num < 3:  # Debug first few pages
                    print(f"   [DEBUG] Page {page_num + 1}: No text extracted (image-based page)")
                continue
            
            # Clean and normalize text
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            
            # Split into lines and filter empty
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            if not lines:
                if page_num < 3:  # Debug first few pages
                    print(f"   [DEBUG] Page {page_num + 1}: No text extracted")
                continue
            
            if page_num < 3:  # Debug first few pages
                print(f"   [DEBUG] Page {page_num + 1}: Extracted {len(lines)} lines, {len(text)} chars")
            
            # Group lines into concepts
            # Strategy: Each page or section becomes a concept
            # If text is long, split into smaller chunks (max 2000 chars per concept)
            full_text = "\n".join(lines)
            
            if len(full_text) <= 2000:
                # Single concept for this page
                title = lines[0][:200] if lines else f"Page {page_num + 1} Content"
                concepts.append({
                    "concept_title": title,
                    "concept_content": full_text,
                    "page_number": page_num + 1,
                })
            else:
                # Split into multiple concepts
                chunks = []
                current_chunk = []
                current_length = 0
                
                for line in lines:
                    line_length = len(line)
                    if current_length + line_length > 2000 and current_chunk:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [line]
                        current_length = line_length
                    else:
                        current_chunk.append(line)
                        current_length += line_length
                
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                
                for i, chunk in enumerate(chunks):
                    title = chunk.split('\n')[0][:200] if chunk else f"Page {page_num + 1} Section {i + 1}"
                    concepts.append({
                        "concept_title": title,
                        "concept_content": chunk,
                        "page_number": page_num + 1,
                    })
        
        doc.close()
        
        # Final warning if many pages had no text
        if pages_without_text > 0:
            total_pages = len(doc) if 'doc' in locals() else 0
            if total_pages > 0:
                empty_rate = pages_without_text / total_pages
                if empty_rate > 0.5:  # More than 50% of pages had no text
                    print(f"\n[WARN] {pages_without_text}/{total_pages} pages ({empty_rate:.1%}) had no extractable text.")
                    print("[WARN] Consider using alternative file formats (see suggestions above).")
        
    except Exception as e:
        print(f"[ERROR] Error extracting from {pdf_path}: {e}")
        return []
    
    return concepts


def store_concepts_in_database(concepts: list[dict], source_file: str, db: Session):
    """Store extracted concepts in knowledge_base table."""
    stored_count = 0
    
    for concept in concepts:
        # Check if concept already exists (by title and source)
        existing = db.query(KnowledgeBase).filter(
            KnowledgeBase.source_file == source_file,
            KnowledgeBase.concept_title == concept["concept_title"],
            KnowledgeBase.page_number == concept["page_number"]
        ).first()
        
        if existing:
            # Update existing concept
            existing.concept_content = concept["concept_content"]
        else:
            # Create new concept
            kb_entry = KnowledgeBase(
                source_file=source_file,
                concept_title=concept["concept_title"],
                concept_content=concept["concept_content"],
                page_number=concept["page_number"],
                language="ja",  # Japanese
                category="caregiving_training",  # Default category
            )
            db.add(kb_entry)
            stored_count += 1
    
    return stored_count


def main():
    """Main function to extract PDFs and populate knowledge base."""
    project_root = Path(__file__).parent.parent
    
    db: Session = SessionLocal()
    try:
        total_concepts = 0
        
        for pdf_filename in PDF_FILES:
            pdf_path = project_root / pdf_filename
            
            if not pdf_path.exists():
                print(f"[WARN] Warning: PDF file not found: {pdf_path}")
                continue
            
            print(f"[INFO] Processing: {pdf_filename}")
            concepts = extract_text_from_pdf(pdf_path)
            print(f"   Extracted {len(concepts)} concepts")
            
            stored = store_concepts_in_database(concepts, str(pdf_path), db)
            db.commit()
            print(f"   Stored {stored} new concepts in database")
            total_concepts += stored
        
        print(f"\n[SUCCESS] Total concepts stored: {total_concepts}")
        
        # Show sample concepts
        sample = db.query(KnowledgeBase).limit(3).all()
        if sample:
            print("\n[INFO] Sample concepts:")
            for kb in sample:
                print(f"   - {kb.concept_title[:60]}... (Page {kb.page_number})")
    
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

