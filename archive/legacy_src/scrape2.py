import os
import re
import json
from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader

# --- Core Data Structure ---
class Document:
    """A simple class to hold our structured data for output, with richer metadata."""
    def __init__(self, library, source, content, section=None, filetype=None, chunk_idx=None):
        self.library = library
        self.source = source
        self.content = content
        self.section = section
        self.filetype = filetype
        self.chunk_idx = chunk_idx

    def to_dict(self):
        d = { "library": self.library, "source": self.source, "content": self.content }
        if self.section:
            d["section"] = self.section
        if self.filetype:
            d["filetype"] = self.filetype
        if self.chunk_idx is not None:
            d["chunk_idx"] = self.chunk_idx
        return d

# --- Utility Function ---
def write_documents_to_jsonl(documents, output_file_path):
    """Writes a list of Document objects to a JSONL file, overwriting the old one."""
    if not documents: return
    with open(output_file_path, "w", encoding="utf-8") as f:
        for doc in documents:
            json.dump(doc.to_dict(), f, ensure_ascii=False)
            f.write("\n")
    print(f"  -> Successfully wrote {len(documents)} documents to {output_file_path.name}")

def clean_for_embedding(text):
    # Remove Sphinx directives and roles
    text = re.sub(r"^\s*\.\. .*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*:[a-zA-Z0-9_-]+:.*", "", text, flags=re.MULTILINE)
    # Remove code blocks and fenced code
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"::\n([ ]{2,}.*\n)+", "", text)
    # Remove images and raw HTML
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    # Remove section headers (lines with ===, ---, ~~~, etc.)
    text = re.sub(r"^\s*[=\-~^`#]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Remove empty lines and excessive whitespace
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"\s+", " ", text)
    # Normalize to lowercase
    text = text.strip().lower()
    return text

def split_by_section(text, filetype):
    """
    Split text into sections by heading for .rst/.md, or by cell for .ipynb.
    Returns list of (section_title, chunk_text) tuples.
    """
    if filetype == "rst":
        # Split by lines with ===, ---, ~~~, etc. (section headers)
        pattern = r"(^.+\n[=\-~^`#]{3,}\s*$)"
        parts = re.split(pattern, text, flags=re.MULTILINE)
        # Merge header and content
        chunks = []
        for i in range(1, len(parts), 2):
            title = parts[i].strip().split("\n")[0] if i < len(parts) else None
            content = parts[i+1] if (i+1) < len(parts) else ""
            chunks.append((title, content))
        if not chunks:
            # fallback: treat whole file as one chunk
            return [(None, text)]
        return chunks
    elif filetype == "md":
        # Split by markdown headings (##, ###, etc.)
        pattern = r"(^#+ .*$)"
        parts = re.split(pattern, text, flags=re.MULTILINE)
        chunks = []
        for i in range(1, len(parts), 2):
            title = parts[i].strip().lstrip("# ") if i < len(parts) else None
            content = parts[i+1] if (i+1) < len(parts) else ""
            chunks.append((title, content))
        if not chunks:
            return [(None, text)]
        return chunks
    else:
        # fallback: treat whole file as one chunk
        return [(None, text)]

# --- Main Processing Function ---
def process_sphinx_docs(library_name: str, path_to_docs: str):
    """
    Loads all .rst and .md files, chunks by section, adds metadata, deduplicates within file.
    """
    print(f"  -> Loading from source directory: {path_to_docs}")
    rst_loader = DirectoryLoader(
        path=path_to_docs,
        glob="**/*.rst",
        loader_cls=TextLoader,
        silent_errors=True,
        show_progress=True,
        use_multithreading=True
    )
    md_loader = DirectoryLoader(
        path=path_to_docs,
        glob="**/*.md",
        loader_cls=TextLoader,
        silent_errors=True,
        show_progress=True,
        use_multithreading=True
    )
    try:
        rst_docs = rst_loader.load()
        md_docs = md_loader.load()
        langchain_docs = rst_docs + md_docs
        langchain_docs = [doc for doc in langchain_docs if doc.page_content.strip()]
        print(f"  -> Found {len(langchain_docs)} non-empty raw documents.")
    except Exception as e:
        print(f"  -> ERROR: Failed to load documents from {path_to_docs}. Error: {e}")
        return []

    output_docs = []
    for doc in langchain_docs:
        source_path = doc.metadata.get('source', path_to_docs)
        ext = Path(source_path).suffix.lower()
        filetype = "rst" if ext == ".rst" else ("md" if ext == ".md" else ext.lstrip("."))
        cleaned_content = clean_for_embedding(doc.page_content)
        # Chunk by section/heading
        chunks = split_by_section(doc.page_content, filetype)
        seen = set()
        for idx, (section, chunk) in enumerate(chunks):
            cleaned_chunk = clean_for_embedding(chunk)
            if not cleaned_chunk or cleaned_chunk in seen:
                continue
            seen.add(cleaned_chunk)
            output_docs.append(Document(
                library=library_name,
                source=source_path,
                content=cleaned_chunk,
                section=section,
                filetype=filetype,
                chunk_idx=idx
            ))
    return output_docs

def process_ipynb_docs(library_name: str, path_to_docs: str):
    """
    Loads only Tutorial 0-4 .ipynb files from a source directory, chunks by cell, adds metadata.
    """
    print(f"  -> Loading .ipynb tutorial files from source directory: {path_to_docs}")
    tutorial_files = [
        "Tutorial 0 - Getting Started.ipynb",
        "Tutorial 1 - Training and Evaluation of Logistic Regression on Encrypted Data.ipynb",
        "Tutorial 2 - Working with Approximate Numbers.ipynb",
        "Tutorial 3 - Benchmarks.ipynb",
        "Tutorial 4 - Encrypted Convolution on MNIST.ipynb",
    ]
    output_docs = []
    for fname in tutorial_files:
        fpath = Path(path_to_docs) / fname
        if not fpath.exists():
            print(f"  -> WARNING: Tutorial file not found: {fpath}")
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                nb_json = json.load(f)
            cells = nb_json.get("cells", [])
            seen = set()
            for idx, cell in enumerate(cells):
                if cell.get("cell_type") in ("markdown", "code"):
                    src = cell.get("source", [])
                    if isinstance(src, list):
                        raw = "".join(src)
                    elif isinstance(src, str):
                        raw = src
                    else:
                        continue
                    cleaned = clean_for_embedding(raw)
                    if not cleaned or cleaned in seen:
                        continue
                    seen.add(cleaned)
                    output_docs.append(Document(
                        library=library_name,
                        source=str(fpath),
                        content=cleaned,
                        section=cell.get("cell_type"),
                        filetype="ipynb",
                        chunk_idx=idx
                    ))
        except Exception as e:
            print(f"  -> ERROR: Failed to process {fpath}: {e}")
    print(f"  -> Found {len(output_docs)} cleaned tutorial cell documents.")
    return output_docs

# --- Main Execution Logic ---
if __name__ == "__main__":
    # --- Configuration: Define local paths to the cloned doc sources ---
    project_root = Path(__file__).resolve().parent.parent
    SOURCE_ROOT = project_root / "data/doc_sources"

    # --- VERIFIED & CORRECTED PATHS ---
    # These paths now point directly to the folders containing the .rst/.md files.

    DOC_SOURCES = {
        "flower": [
            SOURCE_ROOT / "flower/datasets/docs/source", 
            SOURCE_ROOT / "flower/intelligence/docs/source", 
            SOURCE_ROOT / "flower/framework/docs/source", 
            SOURCE_ROOT / "flower/framework/docs/source/docker",
            SOURCE_ROOT / "flower/baselines/docs/source"
            ],

        "torch":        [
            SOURCE_ROOT / "pytorch/docs/source",
            SOURCE_ROOT / "pytorch/docs/cpp/source"
            ],

        "torchvision":  [SOURCE_ROOT / "vision/docs/source"],
        "torchaudio":   [SOURCE_ROOT / "audio/docs/source"],
        "monai":        [SOURCE_ROOT / "MONAI/docs/source"],
        "scikit-learn": [SOURCE_ROOT / "scikit-learn/doc/"], # Files we dont want {binder, css, images, js/scripts, logos, scss, sphoinxext, templates}
        "requests":     [SOURCE_ROOT / "requests/docs/user"],
        "waitress":     [SOURCE_ROOT / "waitress/docs"],      
        "pyramid":      [SOURCE_ROOT / "pyramid/docs"],
        "tenseal":      [SOURCE_ROOT / "TenSEAL/tutorials"],
    }

    # Prepare output directory
    output_dir = Path(__file__).resolve().parent.parent / "data" / "documents"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"INFO: Output will be saved to: {output_dir.resolve()}")
    
    print("\n--- Starting Sphinx Documentation Ingestion from Local Sources ---")
    print(f"INFO: Make sure you have cloned the repositories into the '{SOURCE_ROOT}' directory.")

    # Process all the Sphinx-based documentation projects
    for lib, paths in DOC_SOURCES.items():
        print(f"\nProcessing documentation for '{lib}'...")
        output_file = output_dir / f"{lib}.jsonl"
        
        all_documents = []
        for path in paths:
            if not os.path.exists(path):
                print(f"  -> WARNING: Source directory not found at '{path}'. Skipping.")
                print(f"  -> Please ensure you have cloned the repository for '{lib}'.")
                continue

            if lib == "tenseal":
                documents = process_ipynb_docs(lib, path)
            else:
                documents = process_sphinx_docs(lib, path)
            if documents:
                all_documents.extend(documents)
        
        if all_documents:
            write_documents_to_jsonl(all_documents, output_file)
        else:
            print(f"  -> No content was processed for '{lib}'. An output file was not created.")

    print("\n✅ Ingestion from source complete.")

