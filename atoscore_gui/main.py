"""
Main entry point for SheetSage Native UI
"""

import sys
import os

# Add SheetSage_Core to path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Note: we are already in sheetsage_gui, so we don't need to add it to path if we run from top level,
# but keeping current_dir for internal relative imports parity.
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '..', 'AtoScore_Core')))

import logging
from datetime import datetime

class StreamToLogger(object):
    """Fake file-like stream object that redirects writes to a logger instance."""
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

def setup_logging():
    """Configure logging to file"""
    # Create logs directory next to executable/script
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    log_dir = os.path.join(base_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"ato_score_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Redirect stdout and stderr
    sys.stdout = StreamToLogger(logging.getLogger('STDOUT'), logging.INFO)
    sys.stderr = StreamToLogger(logging.getLogger('STDERR'), logging.ERROR)
    
    logging.info("NC- AtoScore started")
    logging.info(f"Log file: {log_file}")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    """Initialize and launch the application"""
    setup_logging()
    
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Application metadata
    app.setApplicationName("NC- AtoScore")
    app.setOrganizationName("NC-Engineering")
    app.setApplicationVersion("3.0.0")
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'resources', 'logo.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Set modern style
    app.setStyle('Fusion')
    
    # Load and apply stylesheet
    stylesheet_path = os.path.join(os.path.dirname(__file__), 'assets', 'resources', 'styles.qss')
    if os.path.exists(stylesheet_path):
        with open(stylesheet_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
