from docx import Document

doc = Document("C:/Auto_CV_Maker/Resume_template/Resume.docx")

for i, p in enumerate(doc.paragraphs):
    if p.runs:
        print(f"P {i}: style={p.style.name}, run0 bold={p.runs[0].bold}, italic={p.runs[0].italic}, size={p.runs[0].font.size}, font={p.runs[0].font.name}")
