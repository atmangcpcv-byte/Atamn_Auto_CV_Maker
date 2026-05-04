import zipfile
import os
import shutil
import re

doc_path = "C:/Auto_CV_Maker/Resume_template/Resume.docx"
out_path = "C:/Auto_CV_Maker/Resume_template/Resume_Dynamic.docx"
temp_dir = "C:/Auto_CV_Maker/scratch/docx_temp"

if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
os.makedirs(temp_dir)

with zipfile.ZipFile(doc_path, 'r') as zip_ref:
    zip_ref.extractall(temp_dir)

xml_path = os.path.join(temp_dir, "word", "document.xml")
with open(xml_path, 'r', encoding='utf-8') as f:
    xml = f.read()

# Simple replacements
xml = xml.replace("<w:t>YOUR NAME</w:t>", "<w:t>{{ emp_name|upper }}</w:t>")
xml = xml.replace("<w:t>Backend Developer</w:t>", "<w:t>{{ designation }}</w:t>", 1)
xml = xml.replace("<w:t>Email: your.email@example.com | Mobile: +91-XXXXXXXXXX</w:t>", "<w:t>{{ contact_info }}</w:t>")
xml = xml.replace("<w:t>LinkedIn: linkedin.com/in/yourprofile | City: Your City</w:t>", "<w:t></w:t>")
xml = xml.replace("<w:t>Motivated backend developer with experience in Django, REST APIs, and scalable systems. Passionate about building robust architectures and optimizing data flow for high-performance applications.</w:t>", "<w:t>{{ profile_summary }}</w:t>")
xml = xml.replace("<w:t>Python | Django | REST APIs | MySQL | HTML | CSS | JavaScript | Git | AWS | Docker</w:t>", "<w:t>{{ skills_string }}</w:t>")

def inject_loops_and_replace(xml, search_term, replacement_t_text, tags_before, tags_after):
    pattern = re.compile(r'(<w:p(?: [^>]+)?>(?:(?!<w:p(?: [^>]+)?>).)*?<w:t(?: [^>]+)?>)([^<]*' + re.escape(search_term) + r'[^<]*)(</w:t>.*?</w:p>)', re.DOTALL)
    match = pattern.search(xml)
    if not match:
        print(f"FAILED to find {search_term}")
        return xml
        
    before_xml = ""
    for tb in tags_before:
        before_xml += f'<w:p><w:r><w:t>{tb}</w:t></w:r></w:p>'
        
    after_xml = ""
    for ta in tags_after:
        after_xml += f'<w:p><w:r><w:t>{ta}</w:t></w:r></w:p>'
    
    new_p_inner = match.group(1) + replacement_t_text + match.group(3)
    
    return xml[:match.start()] + before_xml + new_p_inner + after_xml + xml[match.end():]

def delete_paragraph(xml, target_t_text):
    pattern = re.compile(r'<w:p(?: [^>]+)?>(?:(?!<w:p(?: [^>]+)?>).)*?<w:t(?: [^>]+)?>[^<]*' + re.escape(target_t_text) + r'[^<]*</w:t>.*?</w:p>', re.DOTALL)
    return pattern.sub('', xml)

# Experience
xml = inject_loops_and_replace(xml, "Backend Developer | Company Name", "{{ exp.title }} | {{ exp.company }}", ["{%p for exp in experiences %}"], [])
xml = re.sub(r'(<w:t(?: [^>]+)?>)[^<]*2021[^<]*Present[^<]*(</w:t>)', r'\1{{ exp.duration }}\2', xml)

xml = inject_loops_and_replace(xml, "Developed scalable web applications using Django framework", "{{ b }}", ["{%p for b in exp.bullets %}"], ["{%p endfor %}", "{%p endfor %}"])

xml = delete_paragraph(xml, "Optimized database performance")
xml = delete_paragraph(xml, "Collaborated with front-end teams")

# Projects
xml = inject_loops_and_replace(xml, "Inventory Management System", "{{ p.title }}", ["{%p for p in projects %}"], [])
xml = inject_loops_and_replace(xml, "Built a full-featured inventory tracking system", "{{ b }}", ["{%p for b in p.bullets %}"], ["{%p endfor %}", "{%p endfor %}"])

xml = delete_paragraph(xml, "API Integration Platform")
xml = delete_paragraph(xml, "Developed a suite of REST APIs")

# Education
xml = inject_loops_and_replace(xml, "Bachelor of Engineering | University Name", "{{ ed.degree }} | {{ ed.institution }}", ["{%p for ed in education %}"], ["{%p endfor %}"])
xml = re.sub(r'(<w:t(?: [^>]+)?>)[^<]*Graduated Year[^<]*(</w:t>)', r'\1{{ ed.graduation_year }}\2', xml)

# Certifications
xml = inject_loops_and_replace(xml, "Certified Django Developer", "{{ cert }}", ["{%p for cert in certifications %}"], ["{%p endfor %}"])
xml = delete_paragraph(xml, "AWS Certified Solutions Architect")


with open(xml_path, 'w', encoding='utf-8') as f:
    f.write(xml)

shutil.make_archive(out_path.replace('.docx', ''), 'zip', temp_dir)
if os.path.exists(out_path): os.remove(out_path)
os.rename(out_path.replace('.docx', '.zip'), out_path)
shutil.rmtree(temp_dir)

print("Direct XML patching complete.")
