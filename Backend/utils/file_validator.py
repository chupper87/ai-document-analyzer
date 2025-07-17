from fastapi import UploadFile, HTTPException, status
from pathlib import Path
import mimetypes

# Try to import magic, but handle if it fails
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    print("⚠️ python-magic could not be loaded. Using fallback validation.")

# Define allowed MIME types for our application
ALLOWED_MIME_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "text/plain",  # .txt
]

# Define allowed file extensions
ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"]

# How many bytes to read for validation (2KB is usually enough)
CHUNK_SIZE_FOR_VALIDATION = 2048

# File signatures (magic bytes) that identify file types
# These are the first few bytes that specific file types always start with
FILE_SIGNATURES = {
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # ZIP-based files like .docx
}


async def validate_file_type(file: UploadFile) -> str:
    """
    Validates file type using multiple methods for maximum reliability.

    The validation happens in three stages:
    1. Magic library (if available) - Most accurate method
    2. File signatures (magic bytes) - Checks actual file content
    3. File extension - Last resort, least secure

    Args:
        file: The uploaded file from FastAPI

    Returns:
        str: The validated MIME type

    Raises:
        HTTPException: If the file type is not allowed
    """

    # First attempt: Use magic library if it's available
    if MAGIC_AVAILABLE:
        try:
            # Read a chunk of the file to analyze
            content_chunk = await file.read(CHUNK_SIZE_FOR_VALIDATION)

            # Use magic to detect the MIME type from content
            detected_mime_type = magic.from_buffer(content_chunk, mime=True)

            # Reset file pointer to beginning so we can read it again later
            await file.seek(0)

            # Check if the detected type is allowed
            if detected_mime_type in ALLOWED_MIME_TYPES:
                return detected_mime_type
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type: {detected_mime_type}. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}",
                )
        except Exception as e:
            # If magic fails, log it and continue with fallback methods
            print(
                f"⚠️ Magic validation failed: {e}. Falling back to signature validation."
            )
            await file.seek(0)

    # Second attempt: Check file signatures (magic bytes)
    # This checks the actual content of the file, not just the name
    content_chunk = await file.read(CHUNK_SIZE_FOR_VALIDATION)
    await file.seek(0)

    # Check if the file starts with any known signatures
    for signature, mime_type in FILE_SIGNATURES.items():
        if content_chunk.startswith(signature):
            if mime_type in ALLOWED_MIME_TYPES:
                return mime_type

    # Third attempt: Validate based on file extension
    # This is the least secure method but better than nothing
    file_extension = Path(file.filename).suffix.lower()

    # First check if the extension is even allowed
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed file types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Try to get MIME type from the upload or guess it
    mime_type = file.content_type or mimetypes.guess_type(file.filename)[0]

    if mime_type and mime_type in ALLOWED_MIME_TYPES:
        return mime_type

    # Last resort: Map extension to MIME type manually
    extension_to_mime = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
    }

    # Return the mapped MIME type or a generic binary type
    return extension_to_mime.get(file_extension, "application/octet-stream")
