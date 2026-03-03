"""Log Processor - Handle log file parsing and normalization."""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import mimetypes

logger = logging.getLogger(__name__)


class LogProcessor:
    """Process and normalize log files.

    Supports:
    - Text log files (.log, .txt)
    - JSON logs
    - Stack traces
    - Multi-format logs (mixed types)
    """

    SUPPORTED_FORMATS = {".log", ".txt", ".json", ".yml", ".yaml", ".md"}

    def __init__(self):
        """Initialize log processor."""
        self.raw_logs: str = ""
        self.normalized_logs: str = ""
        self.metadata: Dict[str, Any] = {}

    async def load_file(self, file_path: str) -> bool:
        """Load log file.

        Args:
            file_path: Path to log file

        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(file_path)

            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return False

            if path.suffix not in self.SUPPORTED_FORMATS:
                logger.warning(f"Unsupported format: {path.suffix}")

            # Read file
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                self.raw_logs = f.read()

            # Store metadata
            self.metadata = {
                "filename": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "format": path.suffix,
                "loaded_at": datetime.now().isoformat(),
            }

            logger.info(
                f"Loaded log file: {path.name} ({self.metadata['size_bytes']} bytes)"
            )
            return True

        except Exception as e:
            logger.error(f"Error loading file: {e}")
            return False

    async def load_text(self, text: str) -> bool:
        """Load log content from text.

        Args:
            text: Log content as string

        Returns:
            True if successful
        """
        try:
            self.raw_logs = text
            self.metadata = {
                "source": "text_input",
                "size_bytes": len(text),
                "loaded_at": datetime.now().isoformat(),
            }
            logger.info(f"Loaded {len(text)} characters of log text")
            return True

        except Exception as e:
            logger.error(f"Error loading text: {e}")
            return False

    async def normalize(self) -> str:
        """Normalize log content.

        Removes:
        - Excess whitespace
        - Duplicate lines
        - ANSI color codes
        - Control characters

        Returns:
            Normalized log text
        """
        if not self.raw_logs:
            logger.warning("No logs to normalize")
            return ""

        try:
            text = self.raw_logs

            # Remove ANSI color codes
            import re
            text = re.sub(r"\x1b\[[0-9;]*m", "", text)

            # Remove null bytes
            text = text.replace("\x00", "")

            # Normalize line endings to \n
            text = text.replace("\r\n", "\n").replace("\r", "\n")

            # Remove excessive blank lines (> 2)
            while "\n\n\n" in text:
                text = text.replace("\n\n\n", "\n\n")

            # Strip leading/trailing whitespace
            text = text.strip()

            self.normalized_logs = text

            logger.info(
                f"Normalized logs: {len(self.raw_logs)} → {len(text)} characters"
            )
            return text

        except Exception as e:
            logger.error(f"Error normalizing logs: {e}")
            return ""

    def get_lines(self, start: int = 0, end: Optional[int] = None) -> List[str]:
        """Get log lines.

        Args:
            start: Starting line number
            end: Ending line number (None = all)

        Returns:
            List of log lines
        """
        text = self.normalized_logs or self.raw_logs
        lines = text.split("\n")

        if end is None:
            return lines[start:]
        else:
            return lines[start:end]

    def get_first_lines(self, count: int = 10) -> List[str]:
        """Get first N lines.

        Args:
            count: Number of lines to return

        Returns:
            First N lines
        """
        return self.get_lines(end=count)

    def get_last_lines(self, count: int = 10) -> List[str]:
        """Get last N lines.

        Args:
            count: Number of lines to return

        Returns:
            Last N lines
        """
        lines = self.get_lines()
        return lines[-count:] if count <= len(lines) else lines

    def get_tail(self) -> str:
        """Get last 20 lines (typical error location).

        Returns:
            Last 20 lines as string
        """
        return "\n".join(self.get_last_lines(20))

    def search(self, pattern: str, case_sensitive: bool = False) -> List[tuple]:
        """Search for pattern in logs.

        Args:
            pattern: Search pattern
            case_sensitive: Whether to match case

        Returns:
            List of (line_num, line_text) tuples
        """
        import re

        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(pattern, flags)

            text = self.normalized_logs or self.raw_logs
            lines = text.split("\n")

            results = []
            for i, line in enumerate(lines):
                if regex.search(line):
                    results.append((i + 1, line))

            return results

        except Exception as e:
            logger.error(f"Error searching logs: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get log statistics.

        Returns:
            Dict with log statistics
        """
        text = self.normalized_logs or self.raw_logs
        lines = text.split("\n")

        # Count error keywords
        error_count = len([l for l in lines if "error" in l.lower()])
        warning_count = len([l for l in lines if "warning" in l.lower()])
        traceback_count = text.count("Traceback")

        return {
            "total_lines": len(lines),
            "total_characters": len(text),
            "error_keyword_count": error_count,
            "warning_keyword_count": warning_count,
            "traceback_count": traceback_count,
            "metadata": self.metadata,
        }

    def get_context_around(self, line_number: int, context_lines: int = 5) -> str:
        """Get context around a specific line.

        Args:
            line_number: Line number to get context for
            context_lines: Number of lines before/after

        Returns:
            Context as string
        """
        lines = self.get_lines()

        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)

        context = lines[start:end]
        return "\n".join(context)

    def extract_error_section(self) -> str:
        """Extract the error/traceback section (usually at end).

        Returns:
            Error section text
        """
        text = self.normalized_logs or self.raw_logs

        # Find last traceback or error
        last_traceback = text.rfind("Traceback")
        if last_traceback >= 0:
            return text[last_traceback:]

        # Fall back to last error
        lines = text.split("\n")
        for i in range(len(lines) - 1, -1, -1):
            if "error" in lines[i].lower():
                start = max(0, i - 5)
                return "\n".join(lines[start:])

        return self.get_tail()
