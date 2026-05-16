import sys
import os
import io
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gamepilot.capture import image_to_bytes

def test_image_to_bytes_no_resize():
    """Test that an image smaller than max_size is not resized."""
    img = Image.new("RGB", (800, 600), color="blue")
    result_bytes = image_to_bytes(img, max_size=1280)

    # Verify the output is a valid JPEG
    result_img = Image.open(io.BytesIO(result_bytes))
    assert result_img.format == "JPEG"
    assert result_img.size == (800, 600)

def test_image_to_bytes_downscale_width():
    """Test downscaling when width is the longest edge."""
    img = Image.new("RGB", (2000, 1000), color="red")
    result_bytes = image_to_bytes(img, max_size=1000)

    result_img = Image.open(io.BytesIO(result_bytes))
    assert result_img.format == "JPEG"
    assert result_img.size == (1000, 500)

def test_image_to_bytes_downscale_height():
    """Test downscaling when height is the longest edge."""
    img = Image.new("RGB", (1000, 2500), color="green")
    result_bytes = image_to_bytes(img, max_size=1000)

    result_img = Image.open(io.BytesIO(result_bytes))
    assert result_img.format == "JPEG"
    assert result_img.size == (400, 1000)

def test_image_to_bytes_exact_match():
    """Test that an image exactly matching max_size is not resized."""
    img = Image.new("RGB", (1280, 720), color="yellow")
    result_bytes = image_to_bytes(img, max_size=1280)

    result_img = Image.open(io.BytesIO(result_bytes))
    assert result_img.format == "JPEG"
    assert result_img.size == (1280, 720)
