import openpyxl
from django.core.management.base import BaseCommand
from django.conf import settings
from records.models import (
    Employee, Project, Skill, Work, Certification,
    Education, EmployeeSkill, WorkSkillAnalysis, ProjectTech,
    PreviousExperience
)


def safe_str(val, max_len=None):
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == 'None':
        return None
    if max_len:
        return s[:max_len]
    return s


def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def safe_int(val):
    try:
        if val is None:
            return None
        return int(float(val))
    except (TypeError, ValueError):
        return None


class Command(BaseCommand):
    help = 'Import data from cv_db.xlsx into the database'

    def handle(self, *args, **options):
        path = settings.EXCEL_DB_PATH
        self.stdout.write(f'Loading workbook from: {path}')
        wb = openpyxl.load_workbook(path)

        # ── Clear existing data (order matters for FK constraints) ──────────
        self.stdout.write('Clearing existing data...')
        ProjectTech.objects.all().delete()
        WorkSkillAnalysis.objects.all().delete()
        EmployeeSkill.objects.all().delete()
        Education.objects.all().delete()
        Certification.objects.all().delete()
        PreviousExperience.objects.all().delete()
        Work.objects.all().delete()
        Employee.objects.all().delete()
        Project.objects.all().delete()
        Skill.objects.all().delete()

        # ── Helper ──────────────────────────────────────────────────────────
        def sheet_rows(sheet_name):
            ws = wb[sheet_name]
            rows = list(ws.rows)
            if not rows:
                return []
            headers = [c.value for c in rows[0]]
            data = []
            for row in rows[1:]:
                row_dict = {headers[i]: row[i].value for i in range(len(headers))}
                data.append(row_dict)
            return data

        # ── Skills ──────────────────────────────────────────────────────────
        self.stdout.write('Importing skills...')
        for row in sheet_rows('Skills'):
            sid = safe_str(row.get('skill_id'))
            if not sid:
                continue
            Skill.objects.get_or_create(
                skill_id=sid.upper(),
                defaults={
                    'skill_name': safe_str(row.get('skill_name')) or 'Unknown',
                    'category': safe_str(row.get('category')),
                }
            )

        # ── Employees ───────────────────────────────────────────────────────
        self.stdout.write('Importing employees...')
        for row in sheet_rows('Employee'):
            eid = safe_int(row.get('emp_id'))
            if not eid:
                continue
            joining = row.get('joining_date')
            if joining is not None and hasattr(joining, 'strftime'):
                joining = joining.strftime('%d/%m/%Y')
            else:
                joining = safe_str(joining)

            Employee.objects.update_or_create(
                emp_id=eid,
                defaults={
                    'emp_name': safe_str(row.get('emp_name')) or 'Unknown',
                    'password': safe_str(row.get('password')) or 'pass@123',
                    'email': safe_str(row.get('email')) or f"emp{eid}@company.com",
                    'profile_summary': safe_str(row.get('profile_summary')),
                    'linkedin_url': safe_str(row.get('linkedin_url')),
                    'github_portfolio_url': safe_str(row.get('github_portfolio_url')),
                    'joining_date': joining,
                    'manager_id': safe_int(row.get('manager_id')),
                    'designation': safe_str(row.get('designation')),
                    'experience': safe_str(row.get('experience')),
                }
            )

        # ── Projects ────────────────────────────────────────────────────────
        self.stdout.write('Importing projects...')
        for row in sheet_rows('Project'):
            pid = safe_int(row.get('project_id'))
            if not pid:
                continue
            Project.objects.update_or_create(
                project_id=pid,
                defaults={
                    'project_name': safe_str(row.get('project_name')) or 'Unknown Project',
                    'description': safe_str(row.get('description')),
                    'status': safe_str(row.get('Status')),
                }
            )

        # ── Work ────────────────────────────────────────────────────────────
        self.stdout.write('Importing work entries...')
        for row in sheet_rows('Work'):
            wid = safe_str(row.get('work_id'))
            eid = safe_int(row.get('emp_id'))
            pid = safe_int(row.get('project_id'))
            if not (wid and eid and pid):
                continue
            try:
                emp = Employee.objects.get(emp_id=eid)
                proj = Project.objects.get(project_id=pid)
                Work.objects.update_or_create(
                    work_id=wid,
                    defaults={
                        'employee': emp,
                        'project': proj,
                        'role_in_project': safe_str(row.get('role_in_project')),
                        'work_summary': safe_str(row.get('work_summary')),
                    }
                )
            except (Employee.DoesNotExist, Project.DoesNotExist):
                self.stdout.write(f'  Skipped work {wid}: employee/project not found')

        # ── Certifications ──────────────────────────────────────────────────
        self.stdout.write('Importing certifications...')
        for row in sheet_rows('Certification'):
            cid = safe_str(row.get('cert_id'))
            eid = safe_int(row.get('emp_id'))
            if not (cid and eid):
                continue
            try:
                emp = Employee.objects.get(emp_id=eid)
                Certification.objects.update_or_create(
                    cert_id=cid,
                    defaults={
                        'employee': emp,
                        'cert_name': safe_str(row.get('cert_name')) or 'Unknown',
                    }
                )
            except Employee.DoesNotExist:
                pass

        # ── Education ───────────────────────────────────────────────────────
        self.stdout.write('Importing education...')
        for row in sheet_rows('Education'):
            edu_id = safe_str(row.get('Edu_id'))
            eid = safe_int(row.get('Emp_id'))
            if not (edu_id and eid):
                continue
            try:
                emp = Employee.objects.get(emp_id=eid)
                Education.objects.update_or_create(
                    edu_id=edu_id,
                    defaults={
                        'employee': emp,
                        'institution': safe_str(row.get('Institution')),
                        'degree': safe_str(row.get('Degree')),
                        'field_of_study': safe_str(row.get('Field of Study')),
                        'graduation_year': safe_int(row.get('Graduation_Year')),
                        'cgpa_or_percentage': safe_float(row.get('Cgpa_or_Percentage')),
                    }
                )
            except Employee.DoesNotExist:
                pass

        # ── Employee Skills ─────────────────────────────────────────────────
        self.stdout.write('Importing employee skills...')
        for row in sheet_rows('Employee_skills'):
            eid = safe_int(row.get('emp_id'))
            sid = safe_str(row.get('skill_id'))
            if not (eid and sid):
                continue
            try:
                emp = Employee.objects.get(emp_id=eid)
                # Normalize skill_id to uppercase
                skill = Skill.objects.get(skill_id=sid.upper())
                EmployeeSkill.objects.update_or_create(
                    employee=emp,
                    skill=skill,
                    defaults={
                        'aggregate_rating': safe_float(row.get('aggrigate_rating')),
                    }
                )
            except (Employee.DoesNotExist, Skill.DoesNotExist):
                pass

        # ── Work Skill Analysis ─────────────────────────────────────────────
        self.stdout.write('Importing work skill analysis...')
        for row in sheet_rows('Work_skill_analysis'):
            aid = safe_str(row.get('analysis_id'))
            wid = safe_str(row.get('work_id'))
            sid = safe_str(row.get('skill_id'))
            if not (aid and wid and sid):
                continue
            try:
                work = Work.objects.get(work_id=wid)
                skill = Skill.objects.get(skill_id=sid.upper())
                WorkSkillAnalysis.objects.update_or_create(
                    analysis_id=aid,
                    defaults={
                        'work': work,
                        'skill': skill,
                        'rating': safe_float(row.get('rating')),
                        'justification': safe_str(row.get('justification')),
                    }
                )
            except (Work.DoesNotExist, Skill.DoesNotExist):
                pass

        # ── Project Tech ────────────────────────────────────────────────────
        self.stdout.write('Importing project tech...')
        for row in sheet_rows('Project_tech'):
            pid = safe_int(row.get('project_id'))
            sid = safe_str(row.get('skill_id'))
            if not (pid and sid):
                continue
            try:
                proj = Project.objects.get(project_id=pid)
                skill = Skill.objects.get(skill_id=sid.upper())
                ProjectTech.objects.get_or_create(project=proj, skill=skill)
            except (Project.DoesNotExist, Skill.DoesNotExist):
                pass

        # ── Previous Experience ─────────────────────────────────────────────
        self.stdout.write('Importing previous experience...')
        for row in sheet_rows('Previous_expirence'):
            peid = safe_str(row.get('past_exp_id'))
            eid  = safe_int(row.get('emp_id'))
            if not (peid and eid):
                continue
            try:
                emp = Employee.objects.get(emp_id=eid)
                PreviousExperience.objects.update_or_create(
                    past_exp_id=peid,
                    defaults={
                        'employee': emp,
                        'company_name': safe_str(row.get('company_name')),
                        'role': safe_str(row.get('role')),
                        'duration': safe_str(row.get('duration')),
                        'description': safe_str(row.get('description')),
                    }
                )
            except Employee.DoesNotExist:
                self.stdout.write(f'  Skipped prev exp {peid}: employee not found')

        self.stdout.write(self.style.SUCCESS('[OK] Data import complete!'))
        self.stdout.write(f'  Employees:           {Employee.objects.count()}')
        self.stdout.write(f'  Projects:            {Project.objects.count()}')
        self.stdout.write(f'  Skills:              {Skill.objects.count()}')
        self.stdout.write(f'  Works:               {Work.objects.count()}')
        self.stdout.write(f'  Previous Experience: {PreviousExperience.objects.count()}')
