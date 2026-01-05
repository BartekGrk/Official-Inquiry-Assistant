from app_from_scratch.document_reader.document_reader import OfficialDocumentHandler 

def test_load_pdf():
    loader = OfficialDocumentHandler("data\docs\D20011198.pdf")
    assert len(loader.load_document()) > 0