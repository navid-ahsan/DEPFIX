"""Error Extractor - Parse and categorize errors from logs."""

import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedError:
    """Parsed error information."""

    error_type: str
    message: str
    file_path: Optional[str]
    line_number: Optional[int]
    stack_trace: List[str]
    raw_error: str
    category: str


class ErrorExtractor:
    """Extract and analyze errors from logs.

    Supports:
    - Python tracebacks
    - ImportError, ModuleNotFoundError
    - AttributeError, TypeError
    - RuntimeError, ValueError
    - Version incompatibility errors
    """

    # Error patterns
    ERROR_PATTERNS = {
        "import_error": re.compile(
            r"(?:ImportError|ModuleNotFoundError):\s*(?:No module named\s+)?['\"]?(\w+)['\"]?"
        ),
        "attribute_error": re.compile(
            r"AttributeError:\s*['\"]?(\w+)['\"]?\s+(?:has no attribute|object has no attribute)"
        ),
        "type_error": re.compile(r"TypeError:\s*(.+?)(?:\n|$)"),
        "value_error": re.compile(r"ValueError:\s*(.+?)(?:\n|$)"),
        "runtime_error": re.compile(r"RuntimeError:\s*(.+?)(?:\n|$)"),
        "version_mismatch": re.compile(
            r"(?:requires|requires\s+|version\s+)(\w+[><=!]+[\d.]+)"
        ),
        "dependency_error": re.compile(
            r"(?:No module named|cannot import name)\s+['\"]?(\w+)['\"]?"
        ),
    }

    TRACEBACK_PATTERN = re.compile(
        r'File "([^"]+)", line (\d+), in (.+)\n\s+(.+)'
    )

    def __init__(self):
        """Initialize error extractor."""
        self.parsed_errors: List[ParsedError] = []

    def extract(self, log_text: str) -> List[ParsedError]:
        """Extract errors from log text.

        Args:
            log_text: Log file content

        Returns:
            List of ParsedError objects
        """
        self.parsed_errors = []
        lines = log_text.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for error lines
            if "Error" in line or "Traceback" in line:
                error = self._parse_error_block(lines, i)
                if error:
                    self.parsed_errors.append(error)
                    i += 10  # Skip ahead
                else:
                    i += 1
            else:
                i += 1

        logger.info(f"Extracted {len(self.parsed_errors)} errors from log")
        return self.parsed_errors

    def _parse_error_block(
        self, lines: List[str], start_idx: int
    ) -> Optional[ParsedError]:
        """Parse a single error block.

        Args:
            lines: All log lines
            start_idx: Index to start parsing from

        Returns:
            ParsedError or None
        """
        error_lines = []
        stack_trace = []
        file_path = None
        line_number = None

        # Collect error lines
        for i in range(start_idx, min(start_idx + 20, len(lines))):
            line = lines[i]

            if "File" in line and "line" in line:
                match = self.TRACEBACK_PATTERN.search(line)
                if match:
                    file_path = match.group(1)
                    line_number = int(match.group(2))

            if "Error" in line or "Traceback" in line:
                error_lines.append(line)

            stack_trace.append(line)

        raw_error = "\n".join(error_lines)
        if not raw_error:
            return None

        # Categorize error
        error_type, message = self._categorize_error(raw_error)
        category = self._categorize_category(error_type, raw_error)

        return ParsedError(
            error_type=error_type,
            message=message,
            file_path=file_path,
            line_number=line_number,
            stack_trace=stack_trace,
            raw_error=raw_error,
            category=category,
        )

    def _categorize_error(self, error_text: str) -> Tuple[str, str]:
        """Categorize error type and extract message.

        Args:
            error_text: Error text

        Returns:
            Tuple of (error_type, message)
        """
        # Check each pattern
        for error_type, pattern in self.ERROR_PATTERNS.items():
            match = pattern.search(error_text)
            if match:
                message = match.group(0)
                return error_type, message

        # Default to generic
        lines = error_text.split("\n")
        last_line = next((l for l in reversed(lines) if l.strip()), "")

        if ":" in last_line:
            error_type = last_line.split(":")[0].strip()
            message = last_line.split(":", 1)[1].strip()
            return error_type, message

        return "unknown_error", error_text

    def _categorize_category(self, error_type: str, raw_error: str) -> str:
        """Categorize error into business categories.

        Args:
            error_type: Technical error type
            raw_error: Raw error text

        Returns:
            Business category
        """
        if "import" in error_type.lower() or "module" in error_type.lower():
            return "dependency"

        if "version" in raw_error.lower():
            return "incompatibility"

        if "attribute" in error_type.lower():
            return "api_mismatch"

        if "type" in error_type.lower():
            return "type_mismatch"

        if "runtime" in error_type.lower():
            return "runtime"

        if "value" in error_type.lower():
            return "invalid_input"

        return "other"

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of parsed errors.

        Returns:
            Summary dict with error counts and categories
        """
        categories = {}
        error_types = {}

        for error in self.parsed_errors:
            categories[error.category] = categories.get(error.category, 0) + 1
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1

        return {
            "total_errors": len(self.parsed_errors),
            "categories": categories,
            "error_types": error_types,
            "primary_category": max(categories, key=categories.get) if categories else None,
        }

    def get_top_error(self) -> Optional[ParsedError]:
        """Get the primary error (usually the last one).

        Returns:
            Most relevant ParsedError
        """
        if not self.parsed_errors:
            return None

        # Return the last error (usually the main one)
        return self.parsed_errors[-1]

    def filter_by_category(self, category: str) -> List[ParsedError]:
        """Get all errors of a specific category.

        Args:
            category: Error category to filter by

        Returns:
            List of matching errors
        """
        return [e for e in self.parsed_errors if e.category == category]

    def filter_by_dependency(self, dependency: str) -> List[ParsedError]:
        """Get all errors related to a specific dependency.

        Args:
            dependency: Dependency name

        Returns:
            List of matching errors
        """
        return [
            e for e in self.parsed_errors
            if dependency.lower() in e.raw_error.lower()
        ]
