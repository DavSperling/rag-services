from pypdf import PdfReader

reader = PdfReader("data/p538.pdf")
print(len(reader.pages), "pages")
print(reader.pages[2].extract_text())