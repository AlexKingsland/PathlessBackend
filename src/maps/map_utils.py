
from typing import Optional
from werkzeug.datastructures import FileStorage
import base64
import imghdr

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
MAX_IMAGE_SIZE_MB = 2  # 2 MB limit since we're storing directly to postgres

def validate_image(file: Optional[FileStorage]):
    """Validate image size and type."""
    if not file:
        return None, "No file uploaded."
    
    if file.mimetype not in ALLOWED_MIME_TYPES:
        return None, "Invalid image type. Only JPEG and PNG are allowed."
    
    file.seek(0, 2)  # Move cursor to end to get size
    size_mb = file.tell() / (1024 * 1024)  # Convert bytes to MB
    file.seek(0)  # Reset cursor

    if size_mb > MAX_IMAGE_SIZE_MB:
        return None, f"File size exceeds {MAX_IMAGE_SIZE_MB}MB."

    return file.read(), None  # Read and return binary data

def validate_base64_image(b64_string: str):
    try:
        # Remove header if present (e.g. "data:image/jpeg;base64,...")
        if b64_string.startswith("data:image/"):
            header, b64_string = b64_string.split(",", 1)

        image_data = base64.b64decode(b64_string)
        image_type = imghdr.what(None, h=image_data)

        if image_type not in ["jpeg", "png"]:
            return None, "Invalid image type. Only JPEG and PNG are allowed."

        size_mb = len(image_data) / (1024 * 1024)
        if size_mb > MAX_IMAGE_SIZE_MB:
            return None, f"File size exceeds {MAX_IMAGE_SIZE_MB}MB."

        return image_data, None

    except Exception as e:
        return None, f"Invalid base64 image: {str(e)}"
