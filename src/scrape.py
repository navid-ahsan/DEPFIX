import os
import io
import json
import re
import requests
import time
from bs4 import BeautifulSoup, Tag
from PyPDF2 import PdfReader
from pathlib import Path
from urllib.parse import urljoin, urlparse

# --- Configuration: Using your original URLs ---
LIBRARIES = {
    "flower": "https://flower.ai/docs/framework/",
    "torch": "https://pytorch.org/docs/stable/",
    "torchvision": "https://pytorch.org/vision/stable/",
    "torchaudio": "https://pytorch.org/audio/stable/",
    "monai": "https://docs.monai.io/en/stable/",
    "scikit-learn": "https://scikit-learn.org/stable/",
    "requests": "https://requests.readthedocs.io/en/latest/user/advanced/",
    "waitress": "https://docs.pylonsproject.org/projects/waitress/en/stable/",
    "pyramid": "https://docs.pylonsproject.org/projects/pyramid/en/2.0-branch/",
    "tenseal": "https://arxiv.org/pdf/2104.03152",
}

# --- Core Data Structure ---
class Document:
    """A class to represent a document with its content and metadata."""
    def __init__(self, library, source, content):
        self.library = library
        self.source = source
        self.content = content

    def to_dict(self):
        """Convert the document to a dictionary for JSON serialization."""
        return { "library": self.library, "source": self.source, "content": self.content }

# --- Utility Functions ---
def get_soup(url):
    """Fetches a webpage and returns a BeautifulSoup object."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, timeout=20, headers=headers)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"  -> Error fetching {url}: {e}")
        return None

def clean_scraped_content(text: str) -> str:
    """Cleans raw text to remove common code artifacts."""
    text = re.sub(r'^\s*[\$>\>]{1,3}\s?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^In \[\d+\]:\s?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^Out\[\d+\]:\s?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*Copy\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()

def extract_and_clean_content(soup_element: Tag):
    """Surgically removes junk HTML elements and then extracts and cleans the text."""
    if not soup_element: return ""
    for tag in soup_element.find_all(['nav', 'footer', 'header', 'script', 'style', 'aside']):
        tag.decompose()
    for selector in ['[role="navigation"]', '[role="search"]', '.sidebar', '.header', '.footer', '.banner', '.top-bar', '.pytorch-breadcrumbs', '.pytorch-right-menu', '.skip-link']:
        for tag in soup_element.select(selector):
            tag.decompose()
    raw_text = soup_element.get_text(separator='\n', strip=True)
    return clean_scraped_content(raw_text)

def write_documents_to_jsonl(documents, output_file_path):
    """Writes a list of Document objects to a JSONL file, overwriting the old one."""
    if not documents: return
    with open(output_file_path, "w", encoding="utf-8") as f:
        for doc in documents:
            json.dump(doc.to_dict(), f, ensure_ascii=False)
            f.write("\n")
    print(f"  -> Successfully wrote {len(documents)} documents to {output_file_path.name}")

# --- Parsers from the new, robust version (For working libraries) ---
def parse_flower(soup, base_url, library_name):
    """
    Finds the 'how-to-guides' section, then for each linked page,
    extracts the main content using a robust accessibility selector.
    """
    section = soup.find("section", id="how-to-guides")
    if not section:
        print("  -> Could not find Flower 'how-to-guides' section.")
        return
        
    links = section.select("ul li a")
    print(f"  -> Found {len(links)} guide links to crawl.")
    
    for a in links:
        page_url = urljoin(base_url, a['href'])
        page_soup = get_soup(page_url)
        if page_soup:
            # --- MODIFIED PART ---
            # Instead of a brittle ID, we use a robust accessibility selector.
            # This looks for a <main> tag OR any tag with role="main".
            main_content = page_soup.select_one('main, [role="main"]')
            
            if not main_content:
                print(f"  -> WARNING: Could not find main content area on {page_url}")
                continue # Skip this page if no main content is found

            # The rest of the logic remains the same, using the clean content.
            content = extract_and_clean_content(main_content)
            if content:
                yield Document(library_name, page_url, content)
                
        time.sleep(0.25)

def parse_pyramid(soup, base_url, library_name):
    section = soup.find("section", id="narrative-documentation")
    if not section:
        print("  -> Could not find Pyramid narrative documentation section.")
        return
    links = section.select("ul li a")
    print(f"  -> Found {len(links)} narrative links to crawl.")
    for a in links:
        page_url = urljoin(base_url, a['href'])
        page_soup = get_soup(page_url)
        if page_soup:
            main_content = page_soup.find('div', class_='body', attrs={'role': 'main'})
            content = extract_and_clean_content(main_content)
            if content: yield Document(library_name, page_url, content)
        time.sleep(0.25)

def parse_simple_page(soup, base_url, library_name, selector):
    main_content = soup.select_one(selector)
    if not main_content:
        print("  -> Could not find main content with selector '{selector}'.")
        return
    content = extract_and_clean_content(main_content)
    if content: yield Document(library_name, base_url, content)

def parse_tenseal_pdf(url, library_name):
    print(f"  -> Fetching and parsing PDF for {library_name}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        pdf_stream = io.BytesIO(response.content)
        reader = PdfReader(pdf_stream)
        full_content = "".join(page.extract_text() for page in reader.pages if page.extract_text())
        if full_content:
            cleaned_content = clean_scraped_content(full_content)
            yield Document(library_name, url, cleaned_content)
        else:
            print("  -> Could not extract any text from the PDF.")
    except Exception as e:
        print(f"  -> An error occurred while processing the PDF: {e}")

# --- Parsers using your original, requested logic ---
def is_same_domain(base_url, link):
    """Helper function for your scikit-learn parser."""
    base_domain = urlparse(base_url).netloc
    link_domain = urlparse(link).netloc
    return (not link_domain) or (link_domain == base_domain)
    
def parse_user_torch_family(soup, base_url, library_name):
    """Your original scraping logic for torch and torchaudio."""
    nav = soup.find("div", id="pytorch-documentation")
    if not nav:
        print(f"  -> YOUR CODE: Could not find div#pytorch-documentation for {library_name}")
        return
    ul = nav.find("ul")
    if not ul:
        print(f"  -> YOUR CODE: Could not find ul in nav for {library_name}")
        return
    for li in ul.find_all("li", class_="toctree-l2"):
        a = li.find("a", href=True)
        if a:
            link_url = urljoin(base_url, a["href"])
            page_soup = get_soup(link_url)
            if page_soup:
                main_content = page_soup.find(class_="main-content")
                page_content = main_content.get_text(separator='\n', strip=True) if main_content else ""
                if page_content:
                    yield Document(library_name, link_url, clean_scraped_content(page_content))
            time.sleep(0.25)

def parse_user_torchvision(soup, base_url, library_name):
 import time
from urllib.parse import urljoin
# Assuming Document, get_soup, and extract_and_clean_content are defined elsewhere

def parse_pytorch_documentation(soup, base_url, library_name):
    """
    A robust, two-stage crawler for the main PyTorch documentation.
    1. Discovers top-level sections from the main index page.
    2. For each section, it crawls all the links in its detailed side-menu.
    """
    documents = []
    
    # --- STAGE 1: Discover top-level sections from the main page grid ---
    # This selector finds the grid of main topic links on the index page.
    top_level_grid = soup.select_one("div.pytorch-article-grid")
    if not top_level_grid:
        print(f"  -> Could not find the top-level documentation grid for {library_name}.")
        return []
        
    section_links = top_level_grid.select("a.pytorch-article")
    print(f"  -> STAGE 1: Found {len(section_links)} top-level sections to crawl.")

    # --- STAGE 2: Deep-crawl each discovered section ---
    for section_link in section_links:
        section_url = urljoin(base_url, section_link.get('href', ''))
        print(f"\n  -> Crawling section: {section_url}")
        
        section_soup = get_soup(section_url)
        if not section_soup:
            continue

        # Find the detailed left-side navigation menu for this specific section.
        side_menu = section_soup.select_one("nav.py-toc-menu.py-toc-side")
        if not side_menu:
            print(f"    -> WARNING: Could not find side-menu for section {section_url}")
            continue

        page_links = side_menu.select("li.toctree-l1 > a, li.toctree-l2 > a")
        print(f"    -> STAGE 2: Found {len(page_links)} pages to scrape in this section.")
        
        for page_link in page_links:
            page_url = urljoin(section_url, page_link.get('href', ''))
            print(f"      --> Scraping page: {page_url}")
            
            page_soup = get_soup(page_url)
            if page_soup:
                # --- STAGE 3: Surgically extract and clean the main content ---
                # This accessibility selector is the most robust way to find the primary content.
                main_content = page_soup.select_one('[role="main"]')
                
                content = extract_and_clean_content(main_content)
                if content:
                    documents.append(Document(library_name, page_url, content))
            
            time.sleep(0.25) # Be respectful to the server

    return documents

def parse_user_monai(soup, base_url, library_name):
    """Your original scraping logic for monai."""
    api_page_url = urljoin(base_url, "api.html")
    api_soup = get_soup(api_page_url)
    if not api_soup: return
    api_section = api_soup.find("section", id="api-reference")
    if not api_section:
        print(f"  -> YOUR CODE: Could not find section#api-reference for {library_name}")
        return
    links_to_scrape = []
    for div in api_section.find_all("div", class_="toctree-wrapper compound"):
        for a in div.find_all("a", href=True):
            links_to_scrape.append(a)
    print(f"  -> YOUR CODE: Found {len(links_to_scrape)} links in the MONAI API reference.")
    for a_tag in links_to_scrape:
        page_url = urljoin(api_page_url, a_tag['href'])
        page_soup = get_soup(page_url)
        if page_soup:
            main_content = page_soup.find("article", class_="bd-article")
            page_content = main_content.get_text(separator='\n', strip=True) if main_content else ""
            if page_content:
                yield Document(library_name, page_url, clean_scraped_content(page_content))
        time.sleep(0.25)

def parse_user_scikit_learn(soup, base_url, library_name):
    """Your original broad scraping logic for scikit-learn."""
    user_guide_url = urljoin(base_url, "user_guide.html")
    user_guide_soup = get_soup(user_guide_url)
    if not user_guide_soup: return
    
    links_crawled = 0
    for a in user_guide_soup.find_all("a", href=True):
        link_url = urljoin(user_guide_url, a["href"])
        if is_same_domain(user_guide_url, link_url) and link_url.endswith(".html"):
            links_crawled += 1
            page_soup = get_soup(link_url)
            if page_soup:
                main_content = page_soup.find("div", role="main") or page_soup.find("main")
                page_content = main_content.get_text(separator='\n', strip=True) if main_content else ""
                if page_content:
                    yield Document(library_name, link_url, clean_scraped_content(page_content))
            time.sleep(0.25)
    print(f"  -> YOUR CODE: Crawled {links_crawled} potential links for scikit-learn.")

def parse_user_requests(soup, base_url, library_name):
    """Your original simple scraping logic for requests."""
    main_content = soup.find("div", class_="document") or soup.find("main")
    if not main_content:
        print("  -> YOUR CODE: Could not find div.document or main for requests.")
        return
    content = main_content.get_text(separator='\n', strip=True)
    if content:
        yield Document(library_name, base_url, clean_scraped_content(content))

# --- Main Execution Logic ---
if __name__ == "__main__":
    PARSERS = {
        # Your requested logic
        "torch": parse_user_torch_family,
        "torchaudio": parse_user_torch_family,
        "torchvision": parse_user_torchvision,
        "monai": parse_user_monai,
        "scikit-learn": parse_user_scikit_learn,
        "requests": parse_user_requests,
        # My working logic
        "flower": parse_flower,
        "pyramid": parse_pyramid,
        "waitress": lambda soup, url, name: parse_simple_page(soup, url, name, "section#waitress"),
        "tenseal": parse_tenseal_pdf,
    }
    output_dir = Path("data/documents")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"INFO: Output will be saved to: {output_dir.resolve()}")

    for lib, url in LIBRARIES.items():
        print(f"\nScraping documentation for '{lib}'...")
        output_file = output_dir / f"{lib}.jsonl"
        # Overwrite existing file for a fresh scrape
        if output_file.exists():
            os.remove(output_file)

        documents = []
        parser_func = PARSERS.get(lib)
        if not parser_func:
            print(f"  -> No parser defined for '{lib}'. Skipping.")
            continue

        if lib == "tenseal":
            documents = list(parser_func(url, lib))
        else:
            initial_soup = get_soup(url)
            if initial_soup:
                documents = list(parser_func(initial_soup, url, lib))
        
        if documents:
            write_documents_to_jsonl(documents, output_file)
        else:
            print(f"  -> No content was scraped for '{lib}'. An output file was not created.")
    
    print("\n✅ Scraping and cleaning complete.")


# helper functions for reuse in other parts of the project

def scrape_library(lib: str):
    """Scrape documentation for a single library.

    Args:
        lib: The key from :data:`LIBRARIES` and :data:`PARSERS`.

    Returns:
        List of :class:`Document` instances.
    """
    if lib not in LIBRARIES:
        raise ValueError(f"Unknown library '{lib}'")
    parser_func = PARSERS.get(lib)
    if not parser_func:
        raise ValueError(f"No parser available for '{lib}'")

    url = LIBRARIES[lib]
    if lib == "tenseal":
        return list(parser_func(url, lib))
    soup = get_soup(url)
    return list(parser_func(soup, url, lib)) if soup else []


def scrape_libraries(libs):
    """Scrape multiple libraries at once.

    Args:
        libs: Iterable of library keys.

    Returns:
        Dict mapping each library to a list of Documents (may be empty).
    """
    results = {}
    for lib in libs:
        try:
            results[lib] = scrape_library(lib)
        except Exception as e:
            print(f"  -> Error scraping {lib}: {e}")
            results[lib] = []
    return results



# --- How you would integrate this into your main script ---
#
# if __name__ == "__main__":
#     # ...
#     PARSERS = {
#         "torch": parse_pytorch_documentation,
#         "torchvision": parse_pytorch_documentation, # Can reuse for similar sites
#         "torchaudio": parse_pytorch_documentation,
#         # ... other parsers ...
#     }
#     # ... rest of your main execution loop ...