import zipfile
import os
import shutil
import re

doc_path = "C:/Auto_CV_Maker/Resume_template/template_2.docx"
out_path = "C:/Auto_CV_Maker/Resume_template/Resume_Prof.docx"
temp_dir = "C:/Auto_CV_Maker/scratch/docx_prof_temp"

if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
os.makedirs(temp_dir)

with zipfile.ZipFile(doc_path, 'r') as zip_ref:
    zip_ref.extractall(temp_dir)

xml_path = os.path.join(temp_dir, "word", "document.xml")
with open(xml_path, 'r', encoding='utf-8') as f:
    xml = f.read()

# ── Simple replacements ────────────────────────────────────────────────────────
xml = xml.replace("<w:t>Jordan</w:t>", "<w:t>{{ emp_name.split()[0] }}</w:t>")
xml = xml.replace("<w:t>Mitchell</w:t>", "<w:t>{{ ' '.join(emp_name.split()[1:]) }}</w:t>")
xml = xml.replace("<w:t>UI/UX Designer</w:t>", "<w:t>{{ designation }}</w:t>")
xml = xml.replace("<w:t>jordan@email.com</w:t>", "<w:t>{{ contact_info }}</w:t>")
xml = xml.replace("<w:t>+1 (555) 000-0000</w:t>", "<w:t></w:t>")
xml = xml.replace("<w:t>linkedin.com/in/</w:t>", "<w:t></w:t>")
xml = xml.replace("<w:t>jordan</w:t>", "<w:t></w:t>")
xml = xml.replace("<w:t>New York, USA</w:t>", "<w:t></w:t>")

summary_text = "Creative and detail-oriented UI/UX Designer with 2+ years of experience crafting intuitive digital experiences for web and mobile platforms. Proven ability to lead end-to-end design \u2014 from user research and wireframing to high-fidelity prototyping and developer handoff. Passionate about solving complex user problems through clean, accessible, and impactful design."
xml = xml.replace(f"<w:t>{summary_text}</w:t>", "<w:t>{{ profile_summary }}</w:t>")

# Skills section
xml = xml.replace("<w:t>Figma, Adobe XD, Sketch, InVision, Zeplin</w:t>", "<w:t>{{ skills_string }}</w:t>")
xml = xml.replace("<w:t>User Research, Wireframing, Prototyping, Usability Testing</w:t>", "<w:t></w:t>")
xml = xml.replace("<w:t>User Personas, Journey Mapping, Information Architecture, Design Systems</w:t>", "<w:t></w:t>")
xml = xml.replace("<w:t>Agile/Scrum, Developer Handoff, Client Presentations, Team Leadership</w:t>", "<w:t></w:t>")

# ── Helpers ────────────────────────────────────────────────────────────────────
def inject_loops_and_replace(xml, search_term, replacement_t_text, tags_before, tags_after):
    pattern = re.compile(
        r'(<w:p(?: [^>]+)?>(?:(?!<w:p(?: [^>]+)?>).)*?<w:t(?: [^>]+)?>)'
        r'([^<]*' + re.escape(search_term) + r'[^<]*)'
        r'(</w:t>.*?</w:p>)',
        re.DOTALL
    )
    match = pattern.search(xml)
    if not match:
        print(f"FAILED to find: {search_term}")
        return xml

    before_xml = "".join(f'<w:p><w:r><w:t>{tb}</w:t></w:r></w:p>' for tb in tags_before)
    after_xml  = "".join(f'<w:p><w:r><w:t>{ta}</w:t></w:r></w:p>' for ta in tags_after)
    new_p_inner = match.group(1) + replacement_t_text + match.group(3)
    return xml[:match.start()] + before_xml + new_p_inner + after_xml + xml[match.end():]

def delete_paragraph(xml, target_t_text):
    pattern = re.compile(
        r'<w:p(?: [^>]+)?>(?:(?!<w:p(?: [^>]+)?>).)*?'
        r'<w:t(?: [^>]+)?>[^<]*' + re.escape(target_t_text) + r'[^<]*</w:t>.*?</w:p>',
        re.DOTALL
    )
    return pattern.sub('', xml)

# ── Experience ─────────────────────────────────────────────────────────────────
# First experience block: Senior UI/UX Designer | Proseware, Inc.  Jan 20XX – Dec 20XX
xml = inject_loops_and_replace(xml, "Senior UI/UX Designer", "{{ exp.title }}", ["{%p for exp in experiences %}"], [])
xml = xml.replace("<w:t>Proseware</w:t>", "<w:t>{{ exp.company }}</w:t>", 1)   # only first occurrence
xml = xml.replace("<w:t>, Inc.</w:t>", "<w:t></w:t>", 1)
xml = xml.replace("<w:t>Jan 20XX \u2013 Dec 20XX</w:t>", "<w:t>{{ exp.duration }}</w:t>")

# First bullet → loop over bullets, close both bullet-loop and exp-loop after
xml = inject_loops_and_replace(
    xml,
    "Led and mentored a team of junior designers, improving design quality and delivery efficiency.",
    "{{ b }}",
    ["{%p for b in exp.bullets %}"],
    ["{%p endfor %}", "{%p endfor %}"]
)

# Delete remaining hard-coded bullets from first block
xml = delete_paragraph(xml, "Designed wireframes, prototypes, and high-fidelity mockups for 10+ web and mobile projects.")
xml = delete_paragraph(xml, "Collaborated with clients to translate business goals into effective, user-centered design solutions.")

# Delete entire second experience block (UI/UX Designer | Proseware, Inc.)
xml = delete_paragraph(xml, "UI/UX Designer")          # title row (first leftover)
xml = delete_paragraph(xml, "Oct 20XX \u2013 Jul 20XX")
xml = delete_paragraph(xml, "Spearheaded redesign of the company\u2019s e-commerce platform, resulting in a 25% increase in sales.")
xml = delete_paragraph(xml, "Conducted user research and usability testing to drive data-informed design decisions.")
xml = delete_paragraph(xml, "Partnered with developers to ensure pixel-accurate implementation of all designs.")

# Delete entire third experience block (UI/UX Designer | Relecloud)
xml = delete_paragraph(xml, "Relecloud")
xml = delete_paragraph(xml, "Feb 20XX \u2013 Oct 20XX")
xml = delete_paragraph(xml, "Developed user personas and conducted research to inform product design strategy.")
xml = delete_paragraph(xml, "Designed user flows, wireframes, and prototypes for an award-winning mobile application.")
xml = delete_paragraph(xml, "Worked closely with engineering to ensure design fidelity throughout development.")

# ── Education ──────────────────────────────────────────────────────────────────
# IMPORTANT: keep loop open across all three ed.* fields; endfor only on last line
xml = inject_loops_and_replace(xml, "Bachelor of Engineering",       "{{ ed.degree }}",          ["{%p for ed in education %}"], [])
xml = inject_loops_and_replace(xml, "K.K. Wagh College of Engineering", "{{ ed.institution }}",  [], [])
xml = inject_loops_and_replace(xml, "Graduation: 2025",              "{{ ed.graduation_year }}", [], ["{%p endfor %}"])

# ── Certifications ─────────────────────────────────────────────────────────────
xml = inject_loops_and_replace(xml, "UI/UX Design", "{{ cert }}", ["{%p for cert in certifications %}"], ["{%p endfor %}"])
xml = delete_paragraph(xml, "User Research")
xml = delete_paragraph(xml, "Usability Testing")
xml = delete_paragraph(xml, "Project Management")

# ── Write output ───────────────────────────────────────────────────────────────
with open(xml_path, 'w', encoding='utf-8') as f:
    f.write(xml)

shutil.make_archive(out_path.replace('.docx', ''), 'zip', temp_dir)
if os.path.exists(out_path):
    os.remove(out_path)
os.rename(out_path.replace('.docx', '.zip'), out_path)
shutil.rmtree(temp_dir)

print("Prof XML patching complete.")