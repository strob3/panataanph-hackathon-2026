"""Warm local OCR models and verify image/scanned-PDF extraction using synthetic text."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PIL import Image, ImageDraw, ImageFont

from backend.services.ocr import extract_text_from_file


def main() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        font = ImageFont.load_default(size=48)
        images = []
        for text in ["DSWD PERMIT SP-999", "RELIEF FOOD PACKS"]:
            image = Image.new("RGB", (1000, 180), "white")
            ImageDraw.Draw(image).text((30, 50), text, font=font, fill="black")
            images.append(image)
        images[0].save(root / "sample.png")
        images[0].save(root / "scanned.pdf", save_all=True, append_images=images[1:])
        for filename, file_type in [("sample.png", "png"), ("scanned.pdf", "pdf")]:
            text, method = extract_text_from_file(root / filename, file_type)
            assert "DSWD" in text and "SP-999" in text, (filename, text)
            if file_type == "pdf":
                assert "RELIEF FOOD PACKS" in text, text
            assert method == "paddleocr", method
            print(f"{filename}: local OCR passed")


if __name__ == "__main__":
    main()
