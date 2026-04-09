import pdfplumber
import docx
import openpyxl
from openpyxl.utils import get_column_letter
from pydantic import BaseModel, Field
from typing import List, Any


class ParsedChunkPDF(BaseModel):
    """
    Represents a single extracted line of text from a PDF, along with
    its exact location metadata that will be stored in the database.
    """
    content: str
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
    location_metadata: dict = Field(
        default_factory=dict,
        description="e.g. {'sheet': 'Sheet1', 'row': 4, 'cells': [{'ref': 'A4', 'column': 'Name', 'value': 'ID1234'}]}"
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
                    location_metadata={
                        "sheet": sheet_name,
                        "row": row_number,
                        "cells": cell_details,
                    },
                )
            )

    workbook.close()
    return chunks