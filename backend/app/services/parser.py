import base64
import mimetypes
import os

import pdfplumber
import docx
import openpyxl
from fireworks import Fireworks
from openpyxl.utils import get_column_letter
from PIL import Image
from pydantic import BaseModel, Field
from typing import List, Any

from app.core.config import settings
from app.services.embeddings import get_embedding


class ParsedChunkPDF(BaseModel):
    """
    Represents a single extracted line of text from a PDF, along with
    its exact location metadata that will be stored in the database.
    """
    content: str
    embedding: List[float]
    location_metadata: dict = Field(
        default_factory=dict,
        description="Exact location of this chunk, e.g. {'page': 3, 'line': 12, 'bbox': {...}}"
    )

class ParsedChunkDOC(BaseModel):
    """
    Represents a single extracted line of text from a DOCX file, along with
    its exact location metadata that will be stored in the database.
    """
    content: str
    embedding: List[float]
    location_metadata: dict = Field(
        default_factory=dict,
        description="Exact location of this chunk, e.g. {'paragraph_index': 4, 'style': 'Heading 1'}"
    )


class ParsedChunkXLSX(BaseModel):
    """
    Represents a single extracted row of data from an Excel file, along with
    its exact location metadata (sheet name, row number, cell references).
    Each row becomes one chunk so there is enough text context for semantic
    embeddings, while the metadata pinpoints each individual cell value.
    """
    content: str
    embedding: List[float]
    location_metadata: dict = Field(
        default_factory=dict,
        description="e.g. {'sheet': 'Sheet1', 'row': 4, 'cells': [{'ref': 'A4', 'column': 'Name', 'value': 'ID1234'}]}"
    )

class ParsedTextFromImages(BaseModel):
    """
    Texts after doing OCR on the images using a Vision AI model.
    """
    content: str
    embedding: List[float]
    location_metadata: dict = Field(
        default_factory=dict,
        description="Which picture contains this text, e.g. {'image_name': 'image1.png'}"
    )


def parse_pdf(file_path: str) -> List[ParsedChunkPDF]:
    """
    Parses a PDF file and returns a list of ParsedChunkPDF objects.

    Each chunk corresponds to one logical line of text on a page.
    Lines are detected by grouping bounding boxes with the same vertical
    position (y-coordinate, called 'top' in pdfplumber).

    Args:
        file_path: The path to the PDF file to be parsed.

    Returns:
        A list of ParsedChunkPDF objects. Each object contains the text
        content of the line and its exact page/line number location.

    Raises:
        FileNotFoundError: If the given file path does not exist.
        Exception: If pdfplumber fails to open or read the file.
    """
    chunks: List[ParsedChunkPDF] = []

    with pdfplumber.open(file_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            # Extract all words from the page; each word has a 'top' value
            # (its y-position from the top of the page) that we use to
            # determine its line number.
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=False,
                use_text_flow=True,  # Respects natural reading order
            )

            if not words:
                continue

            # --- Group words into lines by their vertical ('top') position ---
            # Words on the same line will have very close 'top' values.
            # We bucket them with a small tolerance (3 pts) to catch rounding.
            lines: dict[float, list] = {}
            for word in words:
                # Round to nearest 2pt to group words on the same visual line
                line_key = round(word["top"] / 2) * 2
                if line_key not in lines:
                    lines[line_key] = []
                lines[line_key].append(word)

            # Sort lines by their vertical position (top to bottom)
            sorted_line_keys = sorted(lines.keys())

            for line_number, line_key in enumerate(sorted_line_keys, start=1):
                line_words = lines[line_key]

                # Sort words within the line left to right by x-position
                line_words.sort(key=lambda w: w["x0"])

                line_text = " ".join(w["text"] for w in line_words).strip()

                if not line_text:
                    continue

                # Calculate a bounding box for the whole line
                # by merging the bounding boxes of each word in it
                bbox = {
                    "x0": min(w["x0"] for w in line_words),
                    "top": min(w["top"] for w in line_words),
                    "x1": max(w["x1"] for w in line_words),
                    "bottom": max(w["bottom"] for w in line_words),
                }

                chunks.append(
                    ParsedChunkPDF(
                        content=line_text,
                        embedding=get_embedding(line_text),
                        location_metadata={
                            "page": page_number,
                            "line": line_number,
                            "bbox": bbox,
                        },
                    )
                )

    return chunks


def parse_docx(file_path: str) -> List[ParsedChunkDOC]:
    """
    Parses a DOCX file and returns a list of ParsedChunkDOC objects.

    Each chunk corresponds to one non-empty paragraph in the document.
    Because Word reflows text depending on the renderer, true "line numbers"
    are not reliable. Instead, we capture richer structural metadata:
      - paragraph_index: 1-based sequential counter across the whole document
      - style: the paragraph style name (e.g. 'Heading 1', 'Normal', 'List Bullet')
      - section_heading: the most recent Heading-style paragraph seen, giving
        the reader context about WHERE in the document this paragraph lives

    Args:
        file_path: The path to the .docx file to be parsed.

    Returns:
        A list of ParsedChunkDOC objects, one per non-empty paragraph.

    Raises:
        FileNotFoundError: If the given file path does not exist.
        Exception: If python-docx fails to open or read the file.
    """
    chunks: List[ParsedChunkDOC] = []
    doc = docx.Document(file_path)

    # Track the most recent section heading so every chunk knows its context.
    # e.g. if a paragraph lives under "Chapter 3: Results", we store that.
    current_section_heading: str | None = None

    for paragraph_index, paragraph in enumerate(doc.paragraphs, start=1):
        text = paragraph.text.strip()

        # Skip blank paragraphs — they carry no searchable content
        if not text:
            continue

        style_name: str = paragraph.style.name  # e.g. 'Heading 1', 'Normal'

        # Update the running section heading whenever we encounter a Heading style
        if style_name.startswith("Heading"):
            current_section_heading = text

        chunks.append(
            ParsedChunkDOC(
                content=text,
                embedding=get_embedding(text),
                location_metadata={
                    "paragraph_index": paragraph_index,
                    "style": style_name,
                    # Provides human-readable document context alongside the chunk
                    "section_heading": current_section_heading,
                },
            )
        )

    return chunks


def parse_xlsx(file_path: str, has_header_row: bool = True) -> List[ParsedChunkXLSX]:
    """
    Parses an Excel (.xlsx) file and returns a list of ParsedChunkXLSX objects.

    Strategy:
      - Each non-empty ROW becomes one chunk. This gives enough text context
        for the semantic embedding model to be useful.
      - The 'cells' list in location_metadata records the exact cell reference
        (e.g. 'B4'), the column name (if a header row exists), and the raw value
        for each cell in that row. This satisfies the 'exact cell number' requirement.
      - All sheets in the workbook are parsed.

    Args:
        file_path:      The path to the .xlsx file to be parsed.
        has_header_row: If True, the first row of each sheet is treated as
                        column headers and included in cell metadata. Defaults to True.

    Returns:
        A list of ParsedChunkXLSX objects, one per non-empty data row.

    Raises:
        FileNotFoundError: If the given file path does not exist.
        Exception: If openpyxl fails to open or read the file.
    """
    chunks: List[ParsedChunkXLSX] = []

    # read_only=False so we can access .value on merged cells too
    workbook = openpyxl.load_workbook(file_path, data_only=True)

    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]

        # --- Collect headers from the first row (if applicable) ---
        headers: List[str] = []
        rows = list(sheet.iter_rows())
        if not rows:
            continue

        start_row_index = 0
        if has_header_row:
            header_row = rows[0]
            headers = [
                str(cell.value).strip() if cell.value is not None else get_column_letter(cell.column)
                for cell in header_row
            ]
            start_row_index = 1  # skip the header row when building chunks

        # --- Process each data row ---
        for row in rows[start_row_index:]:
            row_number: int = row[0].row  # 1-based Excel row number

            # Build a structured list of non-empty cells for this row
            cell_details: List[dict[str, Any]] = []
            text_parts: List[str] = []

            for cell in row:
                if cell.value is None:
                    continue

                col_index = cell.column - 1  # 0-based for headers list
                cell_ref = f"{get_column_letter(cell.column)}{row_number}"  # e.g. 'B4'

                # Resolve column name: use header if available, else the letter
                if headers and col_index < len(headers):
                    column_name = headers[col_index]
                else:
                    column_name = get_column_letter(cell.column)

                str_value = str(cell.value).strip()

                cell_details.append({
                    "ref": cell_ref,        # e.g. 'B4'
                    "column": column_name,  # e.g. 'Employee ID'
                    "value": str_value,
                })

                # Build the human-readable text: 'Employee ID: ID1234'
                # This is what gets embedded for semantic search
                text_parts.append(f"{column_name}: {str_value}")

            # Skip entirely empty rows
            if not cell_details:
                continue

            content = " | ".join(text_parts)

            chunks.append(
                ParsedChunkXLSX(
                    content=content,
                    embedding=get_embedding(content),
                    location_metadata={
                        "sheet": sheet_name,
                        "row": row_number,
                        "cells": cell_details,
                    },
                )
            )

    workbook.close()
    return chunks

def parse_image(file_path: str) -> List[ParsedTextFromImages]:
    """
    Extracts text from an image file using a Fireworks AI vision model.

    The vision model is prompted to perform OCR-style extraction and return
    the text line by line. Each line is returned as a separate ParsedTextFromImages
    chunk so the search index can pinpoint the exact line number within the image.

    Supported formats: JPEG, PNG, GIF, WEBP (anything Pillow can open).

    Args:
        file_path: The path to the image file to be parsed.

    Returns:
        A list of ParsedTextFromImages objects, one per non-empty line of
        text detected in the image.

    Raises:
        FileNotFoundError: If the given file path does not exist.
        ValueError: If the file MIME type cannot be determined.
        Exception: If the Fireworks API call fails.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Image not found: {file_path}")

    # --- Determine MIME type so the base64 data URL is correct ---
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError(f"Cannot determine image MIME type for: {file_path}")

    # --- Get basic image metadata (dimensions) via Pillow ---
    with Image.open(file_path) as img:
        width, height = img.size
        image_format = img.format or "UNKNOWN"  # e.g. 'JPEG', 'PNG'

    # --- Encode the image to base64 for the API payload ---
    with open(file_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # --- Call the Fireworks vision model ---
    client = Fireworks(api_key=settings.VISION_MODEL_API_KEY)

    response = client.chat.completions.create(
        model=settings.VISION_MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are an OCR assistant. Extract ALL text visible in this image. "
                            "Return each line of text on its own separate line, preserving the "
                            "original reading order (top to bottom, left to right). "
                            "Do NOT add any commentary, headings, or formatting - only the raw extracted text lines."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}"
                        },
                    },
                ],
            }
        ],
    )

    raw_text: str = response.choices[0].message.content or ""

    # --- Split the response into individual lines and build chunks ---
    image_name = os.path.basename(file_path)
    chunks: List[ParsedTextFromImages] = []

    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue  # skip blank lines

        chunks.append(
            ParsedTextFromImages(
                content=line,
                embedding=get_embedding(line),
                location_metadata={
                    "image_name": image_name,
                    "image_path": file_path,
                    "line": line_number,
                    "image_format": image_format,
                    "image_dimensions": {"width": width, "height": height},
                },
            )
        )

    return chunks