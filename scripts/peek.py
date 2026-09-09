from pypdf import PdfReader

# Inspect the target PDF structure and sample extracted page text
reader = PdfReader("data/p538.pdf")
print(len(reader.pages), "pages")
print(reader.pages[2].extract_text())