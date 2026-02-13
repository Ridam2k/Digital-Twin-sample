"""
Extract text from writing sample PDFs for style calibration.
"""
from pathlib import Path
from pypdf import PdfReader


def extract_writing_samples(pdf_path: Path, max_excerpts: int = 3, words_per_excerpt: int = 100) -> list[str]:
    """
    Extract short excerpts from a PDF for style calibration.

    Args:
        pdf_path: Path to PDF file
        max_excerpts: Maximum number of excerpts to extract
        words_per_excerpt: Target words per excerpt (approximate)

    Returns:
        List of text excerpts, each ~100 words
    """
    try:
        reader = PdfReader(pdf_path)
        full_text = ""

        # Extract text from first few pages only (to keep it manageable)
        max_pages = min(10, len(reader.pages))
        for page_num in range(max_pages):
            page_text = reader.pages[page_num].extract_text()
            if page_text:
                full_text += page_text + "\n\n"

        if not full_text.strip():
            return []

        # Split into paragraphs and clean
        paragraphs = [p.strip() for p in full_text.split('\n\n') if p.strip()]

        # Find paragraphs that are good style samples (avoid headers, page numbers, etc.)
        good_paragraphs = [
            p for p in paragraphs
            if len(p.split()) >= 30  # At least 30 words
            and not p.isupper()      # Not all caps (likely a header)
            and not p.isdigit()      # Not just numbers
        ]

        excerpts = []
        for para in good_paragraphs[:max_excerpts * 2]:  # Look through more to find good ones
            words = para.split()
            if len(words) >= words_per_excerpt:
                # Take first ~100 words of this paragraph
                excerpt = ' '.join(words[:words_per_excerpt])
                excerpts.append(excerpt + "...")
            elif len(words) >= 50:  # Use shorter paragraphs if they're substantial
                excerpts.append(para)

            if len(excerpts) >= max_excerpts:
                break

        return excerpts[:max_excerpts]

    except Exception as e:
        print(f"Warning: Could not extract text from {pdf_path.name}: {e}")
        return []


def load_all_writing_samples(samples_dir: Path, max_total: int = 3) -> list[str]:
    """
    Load writing samples from all PDFs in a directory.

    Args:
        samples_dir: Directory containing PDF writing samples
        max_total: Maximum total excerpts across all PDFs

    Returns:
        List of text excerpts for style calibration
    """
    all_excerpts = []

    if not samples_dir.exists():
        return []

    pdf_files = sorted(samples_dir.glob("*.pdf"))
    excerpts_per_file = max(1, max_total // len(pdf_files)) if pdf_files else 0

    for pdf_file in pdf_files:
        excerpts = extract_writing_samples(pdf_file, max_excerpts=excerpts_per_file)
        all_excerpts.extend(excerpts)

        if len(all_excerpts) >= max_total:
            break

    return all_excerpts[:max_total]
