"""Top-level package for the RAG project.

Making the `src` directory a proper Python package so that modules
(such as `scrape`) can be imported from other parts of the codebase
(e.g. backend agents).

The package is intentionally lightweight; it mainly exists to enable
`from src import scrape` style imports in tests and application code.
"""

__all__ = []
