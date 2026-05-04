import json

with open("c:/Auto_CV_Maker/templates/records/add_employee.html", "r", encoding="utf-8") as f:
    html = f.read()

# Replace block title, page_title, page_sub
html = html.replace('Add Employee — Office Records', 'Edit {{ emp.emp_name }} — Office Records')
html = html.replace('Add New Employee', 'Edit Employee')
html = html.replace('All fields are required — fill in the complete employee profile', 'Update profile details for {{ emp.emp_name }}')
html = html.replace('← Back to Employees', '← Back to Employee')
html = html.replace("{% url 'records:employee_list' %}", "{% url 'records:employee_detail' emp.emp_id %}")

# Prepopulate basic fields
html = html.replace('id="emp_name" class="form-control" placeholder="e.g. Rahul Sharma"', 'id="emp_name" class="form-control" placeholder="e.g. Rahul Sharma" value="{{ emp.emp_name }}"')
html = html.replace('id="emp_email" class="form-control" placeholder="rahul@atman.in"', 'id="emp_email" class="form-control" placeholder="rahul@atman.in" value="{{ emp.email|default_if_none:\'\' }}"')
html = html.replace('id="emp_password" class="form-control" placeholder="Set a login password"', 'id="emp_password" class="form-control" placeholder="Set a login password" value="{{ emp.password }}"')
html = html.replace('id="emp_designation" class="form-control" placeholder="e.g. Senior Backend Developer"', 'id="emp_designation" class="form-control" placeholder="e.g. Senior Backend Developer" value="{{ emp.designation|default_if_none:\'\' }}"')
html = html.replace('id="emp_experience" class="form-control" placeholder="e.g. 5 years"', 'id="emp_experience" class="form-control" placeholder="e.g. 5 years" value="{{ emp.experience|default_if_none:\'\' }}"')
html = html.replace('id="emp_joining_date" class="form-control" placeholder="DD/MM/YYYY"', 'id="emp_joining_date" class="form-control" placeholder="DD/MM/YYYY" value="{{ emp.joining_date|default_if_none:\'\' }}"')
html = html.replace('id="emp_linkedin" class="form-control" placeholder="https://linkedin.com/in/..."', 'id="emp_linkedin" class="form-control" placeholder="https://linkedin.com/in/..." value="{{ emp.linkedin_url|default_if_none:\'\' }}"')
html = html.replace('id="emp_github" class="form-control" placeholder="https://github.com/..."', 'id="emp_github" class="form-control" placeholder="https://github.com/..." value="{{ emp.github_portfolio_url|default_if_none:\'\' }}"')
html = html.replace('<textarea id="emp_profile_summary" class="form-control" rows="3" placeholder="A brief professional bio..."></textarea>', '<textarea id="emp_profile_summary" class="form-control" rows="3" placeholder="A brief professional bio...">{{ emp.profile_summary|default_if_none:\'\' }}</textarea>')
html = html.replace('<strong>{{ next_emp_id }}</strong>', '<strong>{{ emp.emp_id }}</strong>')

# Remove the ID hint entirely because it's not "Auto-assigned Employee ID" anymore
html = html.replace('<div class="id-hint">🆔 Auto-assigned Employee ID: <strong>{{ emp.emp_id }}</strong></div>', '<div class="id-hint">🆔 Employee ID: <strong>{{ emp.emp_id }}</strong></div>')
html = html.replace('💾 Save Employee', '💾 Update Employee')
html = html.replace('add_employee', 'edit_employee', 1)  # replace exactly once to catch the fetch url, although we can just replace specifically:
html = html.replace('{% url \'records:add_employee\' %}', '{% url \'records:edit_employee\' emp.emp_id %}')

js_prefill = """
/* ── PREFILL LOGIC ────────────────────────────────────────────── */
var prefillEdu = JSON.parse(document.getElementById('edu_data').textContent);
var prefillCert = JSON.parse(document.getElementById('cert_data').textContent);
var prefillExp = JSON.parse(document.getElementById('exp_data').textContent);
var prefillSkill = JSON.parse(document.getElementById('emp_skill_data').textContent);

// Set manager
var initialManagerId = "{{ emp.manager_id|default_if_none:'' }}";
if (initialManagerId) {
  var opt = document.querySelector('.manager-option[data-id="' + initialManagerId + '"]');
  if (opt) {
    selectManager(initialManagerId, opt.textContent.trim());
  }
}

// Prefill Educations
prefillEdu.forEach(function(ed) {
  var idx = eduCount++;
  var div = document.createElement('div');
  div.className = 'dynamic-row';
  div.id = 'edu-' + idx;
  div.innerHTML =
    '<button type="button" class="remove-row-btn" onclick="removeRow(\\'edu-' + idx + '\\')" title="Remove">✕</button>' +
    '<div class="edu-grid">' +
      '<div class="form-group" style="margin-bottom:0"><label>Degree <span class="req">*</span></label>' +
        '<input type="text" class="form-control edu-degree" value="' + (ed.degree || '').replace(/"/g, '&quot;') + '"></div>' +
      '<div class="form-group" style="margin-bottom:0"><label>Field of Study <span class="req">*</span></label>' +
        '<input type="text" class="form-control edu-field" value="' + (ed.field_of_study || '').replace(/"/g, '&quot;') + '"></div>' +
      '<div class="form-group" style="margin-bottom:0"><label>Institution <span class="req">*</span></label>' +
        '<input type="text" class="form-control edu-inst" value="' + (ed.institution || '').replace(/"/g, '&quot;') + '"></div>' +
    '</div>' +
    '<div class="edu-grid-2">' +
      '<div class="form-group" style="margin-bottom:0"><label>Graduation Year <span class="req">*</span></label>' +
        '<input type="number" class="form-control edu-year" min="1950" max="2099" value="' + (ed.graduation_year || '') + '"></div>' +
      '<div class="form-group" style="margin-bottom:0"><label>CGPA / Percentage <span class="req">*</span></label>' +
        '<input type="number" class="form-control edu-cgpa" min="0" max="100" step="0.01" value="' + (ed.cgpa_or_percentage || '') + '"></div>' +
    '</div>';
  document.getElementById('educationContainer').appendChild(div);
});

// Prefill Certifications
prefillCert.forEach(function(cert) {
  var idx = certCount++;
  var div = document.createElement('div');
  div.className = 'dynamic-row';
  div.id = 'cert-' + idx;
  div.innerHTML =
    '<div class="cert-grid">' +
      '<div class="form-group" style="margin-bottom:0"><label>Certification Name <span class="req">*</span></label>' +
        '<input type="text" class="form-control cert-name" value="' + (cert.cert_name || '').replace(/"/g, '&quot;') + '"></div>' +
      '<button type="button" class="remove-row-btn" style="position:static;margin-top:24px" onclick="removeRow(\\'cert-' + idx + '\\')" title="Remove">✕</button>' +
    '</div>';
  document.getElementById('certContainer').appendChild(div);
});

// Prefill Experience
prefillExp.forEach(function(exp) {
  var idx = expCount++;
  var div = document.createElement('div');
  div.className = 'dynamic-row';
  div.id = 'exp-' + idx;
  div.innerHTML =
    '<button type="button" class="remove-row-btn" onclick="removeRow(\\'exp-' + idx + '\\')" title="Remove">✕</button>' +
    '<div class="exp-grid">' +
      '<div class="form-group" style="margin-bottom:0"><label>Company <span class="req">*</span></label>' +
        '<input type="text" class="form-control exp-company" value="' + (exp.company_name || '').replace(/"/g, '&quot;') + '"></div>' +
      '<div class="form-group" style="margin-bottom:0"><label>Role / Title <span class="req">*</span></label>' +
        '<input type="text" class="form-control exp-role" value="' + (exp.role || '').replace(/"/g, '&quot;') + '"></div>' +
      '<div class="form-group" style="margin-bottom:0"><label>Duration <span class="req">*</span></label>' +
        '<input type="text" class="form-control exp-duration" value="' + (exp.duration || '').replace(/"/g, '&quot;') + '"></div>' +
    '</div>' +
    '<div class="form-group" style="margin-bottom:0"><label>Description <span class="req">*</span></label>' +
      '<textarea class="form-control exp-desc" rows="2">' + (exp.description || '') + '</textarea></div>';
  document.getElementById('expContainer').appendChild(div);
});

// Prefill Skills
prefillSkill.forEach(function(sk) {
  var idx = skillCount++;
  var div = document.createElement('div');
  div.className = 'dynamic-row';
  div.id = 'skill-' + idx;
  div.innerHTML =
    '<div class="skill-grid">' +
      '<div class="form-group" style="margin-bottom:0"><label>Skill Name <span class="req">*</span></label>' +
        '<input type="text" class="form-control skill-name" autocomplete="off" value="' + (sk.skill__skill_name || '').replace(/"/g, '&quot;') + '"></div>' +
      '<div class="form-group" style="margin-bottom:0"><label>Rating (1–5) <span class="req">*</span></label>' +
        '<input type="number" class="form-control skill-rating" min="1" max="5" step="0.1" value="' + (sk.aggregate_rating || '') + '"></div>' +
      '<button type="button" class="remove-row-btn" style="position:static;margin-top:24px" onclick="removeRow(\\'skill-' + idx + '\\')" title="Remove">✕</button>' +
    '</div>';
  document.getElementById('skillContainer').appendChild(div);
});

setTimeout(function(){
  document.getElementById('managerError').classList.remove('show');
  document.getElementById('eduError').classList.remove('show');
  document.getElementById('certError').classList.remove('show');
  document.getElementById('expError').classList.remove('show');
  document.getElementById('skillError').classList.remove('show');
}, 100);

"""

html = html.replace('</script>\n{% endblock %}', js_prefill + '\n</script>\n{% endblock %}')

inject_data = '''
{{ educations|json_script:"edu_data" }}
{{ certifications|json_script:"cert_data" }}
{{ previous_experiences|json_script:"exp_data" }}
{{ emp_skills|json_script:"emp_skill_data" }}
<script>
'''

html = html.replace('<script>', inject_data, 1)

with open("c:/Auto_CV_Maker/templates/records/edit_employee.html", "w", encoding="utf-8") as f:
    f.write(html)
