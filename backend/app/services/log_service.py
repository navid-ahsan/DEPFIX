"""Error log management and upload service."""

import logging
import os
from pathlib import Path
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from backend.app.models.database import Log, User
from datetime import datetime

logger = logging.getLogger(__name__)

# Allowed file types for error logs
ALLOWED_FORMATS = {'.log', '.txt', '.json', '.jsonl', '.csv'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class ErrorLogUploadService:
    """Handle error log uploads and processing."""
    
    @staticmethod
    def validate_uploaded_file(filename: str, file_size: int) -> tuple[bool, Optional[str]]:
        """
        Validate uploaded file.
        
        Args:
            filename: Name of the file
            file_size: Size in bytes
            
        Returns:
            (is_valid, error_message)
        """
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        if file_ext not in ALLOWED_FORMATS:
            return False, f"File format not allowed. Allowed: {', '.join(ALLOWED_FORMATS)}"
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            return False, f"File size exceeds limit ({MAX_FILE_SIZE / 1024 / 1024}MB)"
        
        return True, None
    
    @staticmethod
    def process_uploaded_file(
        db: Session,
        user: User,
        filename: str,
        content: bytes,
        file_format: str,
    ) -> Optional[Log]:
        """
        Process and store uploaded error log.
        
        Args:
            db: Database session
            user: User who uploaded the file
            filename: Name of the file
            content: File content as bytes
            file_format: File format (auto-detected from extension)
            
        Returns:
            Log object if successful
        """
        try:
            # Decode content
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                text_content = content.decode('utf-8', errors='ignore')
            
            # Create log entry
            log = Log(
                user_id=user.id,
                filename=filename,
                content=text_content,
                file_format=file_format,
                file_size_bytes=len(content),
                is_processed=False,
                created_at=datetime.utcnow(),
            )
            
            db.add(log)
            db.commit()
            db.refresh(log)
            
            logger.info(f"✓ Stored error log {filename} for user {user.id}")
            return log
        
        except Exception as e:
            logger.error(f"Failed to store error log: {e}")
            return None
    
    @staticmethod
    def get_user_logs(db: Session, user: User, limit: int = 50) -> List[Log]:
        """
        Get all error logs for a user.
        
        Args:
            db: Database session
            user: User
            limit: Maximum number of logs
            
        Returns:
            List of Log objects
        """
        return db.query(Log).filter(
            Log.user_id == user.id
        ).order_by(Log.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def delete_log(db: Session, log_id: str, user: User) -> bool:
        """
        Delete an error log.
        
        Args:
            db: Database session
            log_id: ID of log to delete
            user: User (for authorization)
            
        Returns:
            True if successful
        """
        log = db.query(Log).filter(
            Log.id == log_id,
            Log.user_id == user.id,
        ).first()
        
        if log:
            db.delete(log)
            db.commit()
            logger.info(f"✓ Deleted log {log_id}")
            return True
        
        return False


class ErrorLogAnalyzer:
    """Extract and analyze errors from log files."""
    
    @staticmethod
    def extract_errors(log_content: str, file_format: str) -> Dict:
        """
        Extract error information from log content.
        
        Args:
            log_content: Raw log content
            file_format: Format of the log file
            
        Returns:
            Dictionary with extracted error info
        """
        errors = []
        error_types = {}
        error_categories = {}
        
        lines = log_content.split('\n')
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Detect common error patterns
            if any(keyword in line_lower for keyword in ['error', 'exception', 'failed', 'traceback']):
                errors.append({
                    'line_number': i + 1,
                    'content': line.strip()[:200],  # First 200 chars
                })
                
                # Categorize error type
                if 'timeout' in line_lower:
                    error_types['timeout'] = error_types.get('timeout', 0) + 1
                    error_categories.setdefault('timeout', []).append(i + 1)
                elif 'import' in line_lower:
                    error_types['import'] = error_types.get('import', 0) + 1
                    error_categories.setdefault('import', []).append(i + 1)
                elif 'syntax' in line_lower:
                    error_types['syntax'] = error_types.get('syntax', 0) + 1
                    error_categories.setdefault('syntax', []).append(i + 1)
                elif 'assertion' in line_lower:
                    error_types['assertion'] = error_types.get('assertion', 0) + 1
                    error_categories.setdefault('assertion', []).append(i + 1)
                elif 'memory' in line_lower or 'oom' in line_lower:
                    error_types['memory'] = error_types.get('memory', 0) + 1
                    error_categories.setdefault('memory', []).append(i + 1)
                else:
                    error_types['other'] = error_types.get('other', 0) + 1
                    error_categories.setdefault('other', []).append(i + 1)
        
        # Find primary error type
        primary_error_type = max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        primary_error_category = primary_error_type
        
        return {
            'total_errors': len(errors),
            'error_count': len(errors),
            'error_types': error_types,
            'error_categories': error_categories,
            'primary_error_type': primary_error_type,
            'primary_error_category': primary_error_category,
            'sample_errors': errors[:10],  # First 10 errors
        }
    
    @staticmethod
    def update_log_analysis(db: Session, log: Log) -> bool:
        """
        Analyze and update log with extracted error info.
        
        Args:
            db: Database session
            log: Log object to analyze
            
        Returns:
            True if successful
        """
        try:
            analysis = ErrorLogAnalyzer.extract_errors(log.content, log.file_format)
            
            log.error_count = analysis['error_count']
            log.primary_error_type = analysis['primary_error_type']
            log.primary_error_category = analysis['primary_error_category']
            log.extracted_errors = analysis['sample_errors']
            log.error_summary = analysis
            log.is_processed = True
            
            from datetime import datetime
            log.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"✓ Analyzed log {log.id}: found {log.error_count} errors")
            return True
        
        except Exception as e:
            logger.error(f"Failed to analyze log: {e}")
            return False
