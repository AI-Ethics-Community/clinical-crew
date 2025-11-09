"""
Structured logging system with consultation context.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


class ConsultationFilter(logging.Filter):
    """Filter to add consultation_id to log records."""
    
    def filter(self, record):
        if not hasattr(record, 'consultation_id'):
            record.consultation_id = 'N/A'
        return True


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure structured logging system.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    # Detailed format with timestamp, level, module, and message
    log_format = logging.Formatter(
        '%(asctime)s - [%(consultation_id)s] - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger
    logger = logging.getLogger("clinical_crew")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplication
    logger.handlers.clear()
    
    # Add consultation filter
    logger.addFilter(ConsultationFilter())
    
    # File handler (daily rotation)
    log_file = LOGS_DIR / f"clinical_crew_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    logger.info(f"Logging initialized. Log file: {log_file}")
    
    return logger


def get_consultation_logger(consultation_id: str) -> logging.LoggerAdapter:
    """
    Create a logger with consultation-specific context.
    
    Args:
        consultation_id: Unique consultation identifier
        
    Returns:
        Logger adapter with consultation context
    """
    logger = logging.getLogger("clinical_crew")
    return logging.LoggerAdapter(logger, {"consultation_id": consultation_id})


# Initialize logger on module import
_root_logger = logging.getLogger("clinical_crew")
if not _root_logger.handlers:
    setup_logging()
