from document_reader.document_reader import OfficialDocumentHandler

def main_load_document(path: str):
    loader = OfficialDocumentHandler(path)
    text_list = loader.load_document()
    return text_list




        
if __name__ == "__main__":
    from config import pdf_path
    p = pdf_path("D20011198.pdf")

    text = main_load_document(str(p))
    print(text)

# Anonymize pdfs

# Create document metadata
 
# Send chunks to supabase

# ----------------------------------


# Retrive inquiry 

# Get from supabase similar articles

# Build prompt

# Call LLM to get the answer draft

# ----------------------------------

# Validate result and send back the response


