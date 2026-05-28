import os
from pathlib import Path


class Config:
    """Configuration class for the application"""

    # Get the project root directory (where config.py is located)
    PROJECT_ROOT = Path(__file__).parent.resolve()

    # Set upload folder relative to project root
    UPLOAD_FOLDER = str(PROJECT_ROOT / "uploads" / "resumes")

    INSTANCE_FOLDER = str(PROJECT_ROOT / "instance")

    # 16MB max file size for resume uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Allowed file extensions for resume uploads in lowercase
    ALLOWED_EXTENSIONS = {
        "pdf",
        "doc",
        "docx"
    }

    # Create upload directory if it doesn't exist
    @staticmethod
    def init_upload_folder():
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
