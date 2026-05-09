import requests
import io

def test_upload():
    file_content = b"This is a test document."
    files = {"file": ("test.txt", file_content, "text/plain")}
    # Wait, the upload accepts pdf, docx, xlsx, images.
    # Let's create a minimal docx using python-docx!
    pass

import docx
doc = docx.Document()
doc.add_paragraph("This is a test paragraph for embeddings.")
bio = io.BytesIO()
doc.save(bio)
bio.seek(0)

files = {"file": ("test.docx", bio, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
res = requests.post("http://127.0.0.1:8000/api/v1/documents/upload", files=files)
print(res.json())
