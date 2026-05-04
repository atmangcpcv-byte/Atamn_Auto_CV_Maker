from docx import Document

doc = Document("C:/Auto_CV_Maker/Resume_template/Resume.docx")

for i, p in enumerate(doc.paragraphs):
    runs_info = " | ".join([f"'{r.text}'" for r in p.runs])
    if runs_info:
        print(f"Paragraph {i}: {runs_info}")
