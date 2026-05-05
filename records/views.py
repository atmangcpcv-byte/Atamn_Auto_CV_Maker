import os
import json
import uuid
import re
from dotenv import load_dotenv
from django.http import JsonResponse

load_dotenv()
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Count, Avg, Q, Sum
from django.conf import settings

from .models import Employee, Project, Skill, Work, EmployeeSkill, Certification, Education, WorkSkillAnalysis, PreviousExperience, ProjectTech
from google import genai
from google.genai import types
from pydantic import BaseModel
from django.http import HttpResponse
from io import BytesIO
from docxtpl import DocxTemplate
from datetime import datetime
import math
import threading
from django.db import connection

class LLMExpBullet(BaseModel):
    title: str
    company: str
    duration: str
    bullets: list[str]

class LLMProjBullet(BaseModel):
    title: str
    bullets: list[str]

class LLMEmpResume(BaseModel):
    profile_summary: str
    skills: list[str]
    experiences: list[LLMExpBullet]
    projects: list[LLMProjBullet]

class EmpRoleInput(BaseModel):
    emp_id: int
    emp_name: str
    role_in_project: str

class EmpSkillRatingGen(BaseModel):
    skill_name: str
    rating: float

class EmpSummaryGen(BaseModel):
    emp_id: int
    work_summary: str
    skills: list[EmpSkillRatingGen]

class AIProjectGen(BaseModel):
    project_tech_stack: list[str]
    employee_summaries: list[EmpSummaryGen]



class SkillCategoryGen(BaseModel):
    skill_name: str
    category: str

class SkillCategorizationList(BaseModel):
    items: list[SkillCategoryGen]

def categorize_skills_if_needed():
    try:
        uncategorized = Skill.objects.filter(Q(category__isnull=True) | Q(category__exact=''))
        if not uncategorized.exists():
            return
        
        skill_names = list(uncategorized.values_list('skill_name', flat=True))
        prompt = (
            "Categorize each of the following technology/soft skill names into a standard tech industry skill category. "
            "Use categories like: Frontend, Backend, Database, Cloud & DevOps, Data Science & AI, Mobile, Security, Design, Testing, Management, Soft Skills, or Other.\n"
            f"Skills: {', '.join(skill_names)}"
        )

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SkillCategorizationList,
            ),
        )
        data = json.loads(response.text)
        items = data.get("items", [])
        
        for item in items:
            skill_name = item.get("skill_name")
            category = item.get("category")
            if skill_name and category:
                Skill.objects.filter(skill_name__iexact=skill_name).update(category=category)
    except Exception as e:
        print(f"Error categorizing skills: {e}")
    finally:
        connection.close()

def login_required_custom(view_func):
    """Custom login decorator using session-based auth."""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('emp_id'):
            return redirect('records:login')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

def iam_required(*roles):
    """Restrict a view to users with one of the given IAM roles."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.session.get('emp_id'):
                return redirect('records:login')
            user_iam = request.session.get('IAM', 'Employee')
            if user_iam not in roles:
                messages.error(request, f"Access denied. This section requires: {', '.join(roles)} permission.")
                return redirect('records:dashboard')
            return view_func(request, *args, **kwargs)
        wrapper.__name__ = view_func.__name__
        return wrapper
    return decorator

def get_session_iam(request):
    return request.session.get('IAM', 'Employee')


def login_view(request):
    if request.session.get('emp_id'):
        return redirect('records:dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        emp = Employee.objects.filter(email=email).first()
        if emp:
            if emp.password == password:
                # Legacy plain-text match -> upgrade to hashed
                emp.password = make_password(password)
                emp.save(update_fields=['password'])
                request.session['emp_id'] = emp.emp_id
                request.session['emp_name'] = emp.emp_name
                request.session['designation'] = emp.designation
                request.session['emp_initials'] = emp.get_initials()
                request.session['IAM'] = emp.IAM
                messages.success(request, f'Welcome back, {emp.emp_name}! (Password security upgraded)')
                return redirect('records:dashboard')
            elif check_password(password, emp.password):
                # Valid hashed match
                request.session['emp_id'] = emp.emp_id
                request.session['emp_name'] = emp.emp_name
                request.session['designation'] = emp.designation
                request.session['emp_initials'] = emp.get_initials()
                request.session['IAM'] = emp.IAM
                messages.success(request, f'Welcome back, {emp.emp_name}!')
                return redirect('records:dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'records/login.html')


def logout_view(request):
    request.session.flush()
    return redirect('records:login')


@login_required_custom
def dashboard_view(request):
    total_employees = Employee.objects.count()
    total_projects = Project.objects.count()
    total_skills = Skill.objects.count()

    # Designation breakdown
    designation_stats = (
        Employee.objects
        .values('designation')
        .annotate(count=Count('emp_id'))
        .order_by('-count')
    )

    # Skill category breakdown
    skill_categories = (
        Skill.objects
        .values('category')
        .annotate(count=Count('skill_id'))
        .order_by('-count')
    )

    # Recent employees
    recent_employees = Employee.objects.all()[:5]

    # Projects with team count
    projects = Project.objects.annotate(team_size=Count('works__employee', distinct=True))

    # Top skills (most employees possess)
    top_skills = (
        EmployeeSkill.objects
        .values('skill__skill_name', 'skill__category')
        .annotate(emp_count=Count('employee', distinct=True), avg_rating=Avg('aggregate_rating'))
        .order_by('-emp_count')[:8]
    )

    current_emp = Employee.objects.filter(emp_id=request.session.get('emp_id')).first()
    user_iam = get_session_iam(request)

    context = {
        'total_employees': total_employees,
        'total_projects': total_projects,
        'total_skills': total_skills,
        'designation_stats': designation_stats,
        'skill_categories': skill_categories,
        'recent_employees': recent_employees,
        'projects': projects,
        'top_skills': top_skills,
        'current_emp': current_emp,
        'user_iam': user_iam,
    }
    return render(request, 'records/dashboard.html', context)


@login_required_custom
def employee_list_view(request):
    search = request.GET.get('search', '')
    designation_filter = request.GET.get('designation', '')
    availability_filter = request.GET.get('availability', '')

    employees = Employee.objects.annotate(
        active_project_count=Count(
            'works',
            filter=Q(works__project__status='Active'),
            distinct=True
        )
    )

    if search:
        employees = employees.filter(
            Q(emp_name__icontains=search) |
            Q(email__icontains=search) |
            Q(designation__icontains=search)
        )
    if designation_filter:
        employees = employees.filter(designation__iexact=designation_filter)
    if availability_filter == 'active':
        employees = employees.filter(active_project_count__gt=0)
    elif availability_filter == 'available':
        employees = employees.filter(active_project_count=0)

    designations = Employee.objects.values_list('designation', flat=True).distinct()
    current_emp = Employee.objects.filter(emp_id=request.session.get('emp_id')).first()
    user_iam = get_session_iam(request)

    context = {
        'employees': employees,
        'designations': designations,
        'search': search,
        'designation_filter': designation_filter,
        'availability_filter': availability_filter,
        'current_emp': current_emp,
        'user_iam': user_iam,
    }
    return render(request, 'records/employee_list.html', context)


@login_required_custom
def employee_detail_view(request, emp_id):
    employee = get_object_or_404(Employee, emp_id=emp_id)
    works = Work.objects.filter(employee=employee).select_related('project')
    active_works = works.filter(project__status='Active')
    certifications = Certification.objects.filter(employee=employee)
    educations = Education.objects.filter(employee=employee)
    emp_skills = EmployeeSkill.objects.filter(employee=employee).select_related('skill')
    previous_experiences = PreviousExperience.objects.filter(employee=employee)

    # Team members on same projects
    project_ids = works.values_list('project_id', flat=True)
    team_members = (
        Employee.objects
        .filter(works__project_id__in=project_ids)
        .exclude(emp_id=emp_id)
        .distinct()
    )

    current_emp = Employee.objects.filter(emp_id=request.session.get('emp_id')).first()
    user_iam = get_session_iam(request)
    session_emp_id = request.session.get('emp_id')
    
    can_see_ratings = False
    can_manager_edit = False
    
    if user_iam == 'HR':
        can_see_ratings = True
    elif user_iam == 'Manager':
        can_see_ratings = True
        manager_project_ids = list(
            Project.objects.filter(manager_id__icontains=str(session_emp_id))
            .values_list('project_id', flat=True)
        )
        emp_project_ids = list(project_ids)
        can_manager_edit = any(pid in manager_project_ids for pid in emp_project_ids)
    elif user_iam == 'Employee':
        if str(employee.emp_id) == str(session_emp_id):
            can_see_ratings = True

    context = {
        'employee': employee,
        'works': works,
        'active_works': active_works,
        'certifications': certifications,
        'educations': educations,
        'emp_skills': emp_skills,
        'previous_experiences': previous_experiences,
        'team_members': team_members,
        'current_emp': current_emp,
        'user_iam': user_iam,
        'can_see_ratings': can_see_ratings,
        'can_manager_edit': can_manager_edit,
    }
    return render(request, 'records/employee_detail.html', context)


@login_required_custom
def project_list_view(request):
    projects = Project.objects.annotate(
        team_size=Count('works__employee', distinct=True)
    ).prefetch_related('technologies__skill')

    current_emp = Employee.objects.filter(emp_id=request.session.get('emp_id')).first()
    user_iam = get_session_iam(request)

    context = {
        'projects': projects,
        'current_emp': current_emp,
        'user_iam': user_iam,
    }
    return render(request, 'records/project_list.html', context)


@login_required_custom
def project_detail_view(request, project_id):
    project = get_object_or_404(Project, project_id=project_id)
    works = Work.objects.filter(project=project).select_related('employee')
    tech_stack = project.technologies.all().select_related('skill')

    current_emp = Employee.objects.filter(emp_id=request.session.get('emp_id')).first()
    user_iam = get_session_iam(request)
    session_emp_id = request.session.get('emp_id')
    is_project_manager = session_emp_id in project.get_manager_ids_list

    works_with_access = []
    for w in works:
        show_rating = False
        if user_iam == 'HR':
            show_rating = True
        elif user_iam == 'Manager':
            show_rating = True
            
        skill_analyses = w.skill_analyses.select_related('skill') if show_rating else []
        works_with_access.append({
            'work': w,
            'show_rating': show_rating,
            'skill_analyses': skill_analyses,
        })

    context = {
        'project': project,
        'works_with_access': works_with_access,
        'tech_stack': tech_stack,
        'current_emp': current_emp,
        'user_iam': user_iam,
        'is_project_manager': is_project_manager,
    }
    return render(request, 'records/project_detail.html', context)


@login_required_custom
def skills_view(request):
    skills = Skill.objects.all().prefetch_related('employee_skills__employee')

    # Group by category
    categories = {}
    for skill in skills:
        cat = skill.category or 'Other'
        if cat not in categories:
            categories[cat] = []
        emp_count = skill.employee_skills.count()
        avg_rating = skill.employee_skills.aggregate(avg=Avg('aggregate_rating'))['avg'] or 0
        categories[cat].append({
            'skill': skill,
            'emp_count': emp_count,
            'avg_rating': round(avg_rating, 1),
            'avg_pct': int((avg_rating / 5) * 100),
        })

    current_emp = Employee.objects.filter(emp_id=request.session.get('emp_id')).first()

    context = {
        'categories': categories,
        'current_emp': current_emp,
    }
    return render(request, 'records/skills.html', context)


@login_required_custom
def my_profile_view(request):
    emp_id = request.session.get('emp_id')
    return redirect('records:employee_detail', emp_id=emp_id)


def update_employee_skill_rating(emp, skill):
    analyses = WorkSkillAnalysis.objects.filter(work__employee=emp, skill=skill)
    if analyses.exists():
        avg = analyses.aggregate(avg_rating=Avg('rating'))['avg_rating']
        es, _ = EmployeeSkill.objects.get_or_create(employee=emp, skill=skill)
        es.aggregate_rating = round(avg, 2)
        es.save()
    else:
        EmployeeSkill.objects.filter(employee=emp, skill=skill).delete()


def recalculate_utilization(emp):
    """Recompute Employee.total_utilization as the sum of all Work.utilization values."""
    total = Work.objects.filter(employee=emp).aggregate(s=Sum('utilization'))['s'] or 0
    Employee.objects.filter(emp_id=emp.emp_id).update(total_utilization=round(total, 2))


@iam_required('HR', 'Manager')
def generate_project_ai(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_name = data.get('project_name', '')
            description = data.get('description', '')
            employees = data.get('employees', [])
            tech_stack = data.get('tech_stack', [])

            prompt = f"Project Name: {project_name}\nDescription: {description}\n"
            if tech_stack:
                prompt += f"Predefined Tech Stack: {', '.join(tech_stack)}\n"
            prompt += "Employees:\n"
            for emp in employees:
                prompt += f"- ID: {emp['emp_id']}, Name: {emp['emp_name']}, Role: {emp['role']}\n"
            
            prompt += "\nBased on this, generate the overall project_tech_stack"
            if tech_stack:
                prompt += " (which should strictly include the Predefined Tech Stack)."
            else:
                prompt += "."
            prompt += "\nThen, for each employee, write a concise work_summary from their role's perspective, actively discussing how they utilized the Predefined Tech Stack technologies (if provided) in their work. Also, suggest what skills they specifically used and rate their skill (1.0 to 5.0) based on typical expectations."

            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=AIProjectGen,
                    ),
                )
                return JsonResponse({'success': True, 'data': json.loads(response.text)})
            except Exception as _e:
                print(str(_e))
                return JsonResponse({'success': False, 'error': str(_e)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@iam_required('HR', 'Manager')
def add_project_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project_name = data.get('project_name')
            description = data.get('description')
            status = data.get('status')
            manager_ids_list = data.get('manager_ids', [])
            manager_id_str = ",".join([str(mid) for mid in manager_ids_list]) if manager_ids_list else None
            tech_stack = data.get('tech_stack', [])
            employees_data = data.get('employees', [])

            new_project_id = 1
            last_proj = Project.objects.order_by('-project_id').first()
            if last_proj:
                new_project_id = last_proj.project_id + 1

            project = Project.objects.create(
                project_id=new_project_id,
                project_name=project_name,
                description=description,
                status=status,
                manager_id=manager_id_str
            )

            # Process Project Tech Stack
            project_skills = []
            for t in tech_stack:
                skill_name_clean = t.strip()
                skill = Skill.objects.filter(skill_name__iexact=skill_name_clean).first()
                if not skill:
                    new_skill_id = 'S' + str(uuid.uuid4().int)[:6]
                    skill = Skill.objects.create(skill_id=new_skill_id, skill_name=skill_name_clean)
                ProjectTech.objects.get_or_create(project=project, skill=skill)
                project_skills.append(skill)

            # Process Employees and their roles/skills
            for emp_data in employees_data:
                emp_id = emp_data.get('emp_id')
                role = emp_data.get('role')
                work_summary = emp_data.get('work_summary')
                emp_skills = emp_data.get('skills', [])

                emp = Employee.objects.get(emp_id=emp_id)
                new_work_id = 'W' + str(uuid.uuid4().int)[:8]
                utilization = float(emp_data.get('utilization', 0) or 0)
                work = Work.objects.create(
                    work_id=new_work_id,
                    employee=emp,
                    project=project,
                    role_in_project=role,
                    work_summary=work_summary,
                    utilization=utilization
                )
                recalculate_utilization(emp)

                for es in emp_skills:
                    skill_name_clean = es.get('skill_name').strip()
                    rating = es.get('rating')

                    skill = Skill.objects.filter(skill_name__iexact=skill_name_clean).first()
                    if not skill:
                        new_skill_id = 'S' + str(uuid.uuid4().int)[:6]
                        skill = Skill.objects.create(skill_id=new_skill_id, skill_name=skill_name_clean)

                    new_an_id = 'An' + str(uuid.uuid4().int)[:8]
                    WorkSkillAnalysis.objects.create(
                        analysis_id=new_an_id,
                        work=work,
                        skill=skill,
                        rating=rating,
                        justification="Added from project creation"
                    )

                    update_employee_skill_rating(emp, skill)

            threading.Thread(target=categorize_skills_if_needed).start()
            return JsonResponse({'success': True, 'project_id': project.project_id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # GET Request
    employees_list = list(Employee.objects.values('emp_id', 'emp_name', 'designation', 'total_utilization'))
    current_emp = Employee.objects.filter(emp_id=request.session.get('emp_id')).first()
    return render(request, 'records/add_project.html', {
        'employees_js': employees_list,
        'employees': employees_list,
        'current_emp': current_emp,
    })


@iam_required('HR', 'Manager')
def edit_project_view(request, project_id):
    project = get_object_or_404(Project, project_id=project_id)
    user_iam = get_session_iam(request)
    session_emp_id = request.session.get('emp_id')
    if user_iam == 'Manager' and session_emp_id not in project.get_manager_ids_list:
        return JsonResponse({'success': False, 'error': 'Access denied. You can only edit projects you manage.'})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            project.project_name = data.get('project_name')
            project.description = data.get('description')
            project.status = data.get('status')
            manager_ids_list = data.get('manager_ids', [])
            project.manager_id = ",".join([str(mid) for mid in manager_ids_list]) if manager_ids_list else None
            project.save()

            # Tech Stack
            tech_stack = data.get('tech_stack', [])
            current_techs = list(ProjectTech.objects.filter(project=project).values_list('skill__skill_name', flat=True))
            for tech in current_techs:
                if tech not in tech_stack:
                    ProjectTech.objects.filter(project=project, skill__skill_name=tech).delete()
            
            for t_name in tech_stack:
                t_name_clean = t_name.strip()
                if not t_name_clean: continue
                skill = Skill.objects.filter(skill_name__iexact=t_name_clean).first()
                if not skill:
                    new_skill_id = 'S' + str(uuid.uuid4().int)[:6]
                    skill = Skill.objects.create(skill_id=new_skill_id, skill_name=t_name_clean)
                ProjectTech.objects.get_or_create(project=project, skill=skill)

            # Team Handling
            employees_data = data.get('employees', [])
            passed_emp_ids = [int(emp['emp_id']) for emp in employees_data]
            
            works_to_delete = Work.objects.filter(project=project).exclude(employee__emp_id__in=passed_emp_ids)
            for work in works_to_delete:
                affected_pairs = list(WorkSkillAnalysis.objects.filter(work=work).values_list('work__employee', 'skill').distinct())
                work.delete()
                for emp_id, skill_id in affected_pairs:
                    try:
                        emp = Employee.objects.get(emp_id=emp_id)
                        sk = Skill.objects.get(skill_id=skill_id)
                        update_employee_skill_rating(emp, sk)
                    except Exception:
                        pass
            
            for emp_data in employees_data:
                emp = Employee.objects.get(emp_id=emp_data['emp_id'])
                work = Work.objects.filter(project=project, employee=emp).first()
                if work:
                    work.role_in_project = emp_data.get('role', '')
                    work.work_summary = emp_data.get('summary', '')
                    work.utilization = float(emp_data.get('utilization', 0) or 0)
                    work.save()
                else:
                    new_work_id = 'W' + str(uuid.uuid4().int)[:8]
                    work = Work.objects.create(
                        work_id=new_work_id,
                        project=project,
                        employee=emp,
                        role_in_project=emp_data.get('role', ''),
                        work_summary=emp_data.get('summary', ''),
                        utilization=float(emp_data.get('utilization', 0) or 0)
                    )
                recalculate_utilization(emp)
                
                passed_skills = emp_data.get('skills', [])
                current_analyses = list(WorkSkillAnalysis.objects.filter(work=work))
                
                for wa in current_analyses:
                    skill_obj = wa.skill
                    wa.delete()
                    update_employee_skill_rating(emp, skill_obj)
                    
                for s in passed_skills:
                    s_name = str(s.get('skill_name', '')).strip()
                    if not s_name: continue
                    rating_val = float(s.get('rating', 3.0))
                    
                    skill_obj = Skill.objects.filter(skill_name__iexact=s_name).first()
                    if not skill_obj:
                        skill_obj = Skill.objects.create(skill_id='S' + str(uuid.uuid4().int)[:6], skill_name=s_name)
                    
                    new_an_id = 'An' + str(uuid.uuid4().int)[:8]
                    WorkSkillAnalysis.objects.create(
                        analysis_id=new_an_id,
                        work=work,
                        skill=skill_obj,
                        rating=rating_val,
                        justification="Updated from edit project logic"
                    )
                    update_employee_skill_rating(emp, skill_obj)

            threading.Thread(target=categorize_skills_if_needed).start()
            messages.success(request, "Project structure updated successfully.")
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    current_emp = Employee.objects.filter(emp_id=request.session.get('emp_id')).first()
    employees_list = list(Employee.objects.values('emp_id', 'emp_name', 'designation', 'total_utilization'))
    
    current_tech_stack_str = ", ".join(project.technologies.values_list('skill__skill_name', flat=True))
    
    current_team = []
    for work in project.works.all():
        skills = []
        for wa in work.skill_analyses.all():
            skills.append({
                'skill_name': wa.skill.skill_name,
                'rating': wa.rating
            })
            
        current_team.append({
            'emp_id': work.employee.emp_id,
            'emp_name': work.employee.emp_name,
            'role': work.role_in_project or '',
            'summary': work.work_summary or '',
            'utilization': work.utilization or 0,
            'base_util': (work.employee.total_utilization or 0) - (work.utilization or 0),
            'skills': skills
        })
        
    return render(request, 'records/edit_project.html', {
        'project': project, 
        'current_emp': current_emp, 
        'employees': employees_list,
        'employees_js': employees_list,
        'current_tech_stack': current_tech_stack_str,
        'current_team_js': current_team
    })


@iam_required('HR')
def delete_project_view(request, project_id):
    project = get_object_or_404(Project, project_id=project_id)
    if request.method == 'POST':
        # Collect affected employees before deletion
        affected_emp_ids = list(Work.objects.filter(project=project).values_list('employee__emp_id', flat=True).distinct())
        affected_pairs = list(WorkSkillAnalysis.objects.filter(work__project=project).values_list('work__employee', 'skill').distinct())
        project.delete()
        # Recalculate skill ratings
        for emp_id, skill_id in affected_pairs:
            try:
                emp = Employee.objects.get(emp_id=emp_id)
                skill = Skill.objects.get(skill_id=skill_id)
                update_employee_skill_rating(emp, skill)
            except Exception:
                pass
        # Recalculate utilization for all affected employees
        for emp_id in affected_emp_ids:
            try:
                emp = Employee.objects.get(emp_id=emp_id)
                recalculate_utilization(emp)
            except Exception:
                pass
        messages.success(request, "Project deleted successfully.")
        return redirect('records:project_list')
    return redirect('records:project_detail', project_id=project.project_id)


@login_required_custom
def download_resume_view(request, emp_id):
    emp = get_object_or_404(Employee, emp_id=emp_id)
    
    # Gather Data
    works = Work.objects.filter(employee=emp).select_related('project')
    emp_skills = EmployeeSkill.objects.filter(employee=emp).select_related('skill')
    educations = Education.objects.filter(employee=emp)
    certifications = Certification.objects.filter(employee=emp)
    experiences = PreviousExperience.objects.filter(employee=emp)
    
    # Atman Duration Logic
    atman_duration_str = "Present"
    if emp.joining_date:
        try:
            join_d = datetime.strptime(emp.joining_date.strip(), '%d/%m/%Y')
            now = datetime.now()
            diff_days = (now - join_d).days
            years = diff_days / 365.25
            if years >= 1:
                y = math.floor(years)
                m = math.floor((years - y) * 12)
                if m > 0:
                    atman_duration = f"{y} year{'s' if y > 1 else ''} {m} month{'s' if m > 1 else ''}"
                else:
                    atman_duration = f"{y} year{'s' if y > 1 else ''}"
            else:
                m = math.floor(diff_days / 30.44)
                if m > 0:
                    atman_duration = f"{m} month{'s' if m > 1 else ''}"
                else:
                    atman_duration = "Less than a month"
            
            start_str = join_d.strftime('%b %Y')
            atman_duration_str = f"{start_str} - Present ({atman_duration})"
        except Exception:
            atman_duration_str = f"{emp.joining_date} - Present"

    # Project Gathering with Manager Privileges
    proj_map = {}
    for w in works:
        proj_map[w.project.project_id] = {
            'name': w.project.project_name,
            'role': w.role_in_project or 'Contributor',
            'summary': w.work_summary or '',
            'is_manager': False
        }
        
    all_projects = Project.objects.all()
    for p in all_projects:
        if emp.emp_id in p.get_manager_ids_list:
            if p.project_id in proj_map:
                proj_map[p.project_id]['is_manager'] = True
            else:
                proj_map[p.project_id] = {
                    'name': p.project_name,
                    'role': 'Project Manager',
                    'summary': p.description or '',
                    'is_manager': True
                }
                
    job_description = ""
    if request.method == 'POST':
        job_description = request.POST.get('job_description', '').strip()
        
    jd_instruction = ""
    if job_description:
        jd_instruction = (
            f"CRITICAL REQUIREMENT: This candidate is specifically applying for the following job description:\n"
            f"<Job_Description>\n{job_description}\n</Job_Description>\n"
            "You MUST fundamentally optimize their entire profile summary, skill categorizations, and project bullet points to aggressively mirror the keywords, tone, and requirements of this specific JD.\n"
            "SKILL MAPPING RULE: If the JD asks for a specific technology (e.g. Azure) and the candidate has deep experience in a directly equivalent or neighboring technology (e.g. GCP), you MUST list the JD's requested technology (e.g. Azure) alongside their existing skills in the 'skills' array to show equivalent competency. DO NOT invent entirely new career paths, but map technical equivalents to pass ATS filters.\n"
        )
    
    # Prompt Setup
    raw_data = f"Name: {emp.emp_name}\nDesignation: {emp.designation}\nProfile Summary: {emp.profile_summary}\n\n"
    
    raw_data += "Skills:\n"
    for s in emp_skills:
        raw_data += f"- {s.skill.skill_name} ({s.aggregate_rating}/5)\n"
        
    raw_data += "\nPrevious Experiences:\n"
    for ex in experiences:
        raw_data += f"- {ex.role} at {ex.company_name} ({ex.duration})\n"
        
    raw_data += "\nProjects:\n"
    for pid, data in proj_map.items():
        role = data['role']
        if data['is_manager'] and role != 'Project Manager':
            role = f"{role} (Also Project Manager)"
        raw_data += f"- Project: {data['name']}. Role: {role}. Summary: {data['summary']}\n"
        
    prompt = (
        "You are an expert tech recruiter rewriting a software engineer's profile into an elite, aggressive resume.\n"
        "Take the raw data below and rewrite the profile_summary to be highly impactful.\n\n"
        f"{jd_instruction}"
        "IMPORTANT RULES:\n"
        "1. CURRENT COMPANY: The employee currently works at a company named 'Atman'. You MUST add 'Atman' as their most recent experience in the 'experiences' array. "
        f"Their job title at Atman is '{emp.designation or 'Software Engineer'}', and their duration is '{atman_duration_str}'. "
        "Base all bullet points for the 'Atman' experience on a generalized summary of the 'Projects' list provided below.\n"
        "2. PREVIOUS EXPERIENCES: Rewrite their raw previous experiences into properly defined job titles, companies, durations, and highly impactful bullet points highlighting actual achievements. "
        f"CRITICAL: The employee has a total of '{emp.experience or '0'}' years of experience. If their raw Previous Experiences are missing or not long enough to account for this '{emp.experience}' years, you MUST realistically invent/hallucinate previous software roles, strong achievements, and company names leading up to the current date so their resume logically validates their years of experience!\n"
        "3. PROJECTS: Rewrite their internal Atman projects into specific, impressive bullet points explaining what they built and how. "
        "CRITICAL FOR PROJECTS: Only write about the SPECIFIC ROLE and tasks the person did on that project. Do NOT invent or describe parts of the project they were not involved in. If they managed the project, state that they managed it. If they only did backend, only write about the backend. "
        "When generating the JSON for Projects, the `title` string MUST be formatted as 'Project Name (Role)'. Example: 'Voice Bot (Project Manager)'.\n\n"
        f"Raw Data:\n{raw_data}"
    )
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LLMEmpResume,
            ),
        )
        llm_out = json.loads(response.text)
    except Exception as e:
        messages.error(request, f"CV Generation AI Failed: {str(e)}")
        return redirect('records:employee_detail', emp_id=emp_id)
        
    # Build Docx
    template_type = request.POST.get('template_type', 'general')
    if template_type == 'prof':
        tpl_path = os.path.join(settings.BASE_DIR, 'Resume_template', 'Resume_Prof.docx')
    else:
        tpl_path = os.path.join(settings.BASE_DIR, 'Resume_template', 'Resume_Dynamic.docx')
        
    tpl = DocxTemplate(tpl_path)
    
    contact_info = []
    if emp.email: contact_info.append(f"Email: {emp.email}")
    if emp.linkedin_url: contact_info.append(f"LinkedIn: {emp.linkedin_url}")
    contact_str = " | ".join(contact_info)
    
    ed_list = []
    for ed in educations:
        ed_list.append({
            'degree': ed.degree,
            'institution': ed.institution,
            'graduation_year': str(ed.graduation_year) if ed.graduation_year else ''
        })
        
    cert_list = [c.cert_name for c in certifications]
    
    # Prioritize LLM-generated/mapped skills string
    llm_skills = llm_out.get('skills', [])
    if llm_skills:
        skills_string = " | ".join(llm_skills)
    else:
        skills_string = " | ".join([s.skill.skill_name for s in emp_skills])
    
    context = {
        'emp_name': emp.emp_name,
        'designation': emp.designation or 'Software Engineer',
        'contact_info': contact_str,
        'profile_summary': llm_out.get('profile_summary', ''),
        'skills_string': skills_string,
        'experiences': llm_out.get('experiences', []),
        'projects': llm_out.get('projects', []),
        'education': ed_list,
        'certifications': cert_list
    }
    
    tpl.render(context)
    
    file_stream = BytesIO()
    tpl.save(file_stream)
    file_stream.seek(0)
    
    response = HttpResponse(
        file_stream.read(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename="{emp.emp_name}_CV.docx"'
    return response


@iam_required('HR')
def add_employee_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # ── Auto ID ───────────────────────────────────────────
            last_emp = Employee.objects.order_by('-emp_id').first()
            new_emp_id = (last_emp.emp_id + 1) if last_emp else 1001

            # ── Basic Info ────────────────────────────────────────
            emp = Employee.objects.create(
                emp_id=new_emp_id,
                emp_name=data.get('emp_name', '').strip(),
                password=make_password(data.get('password', '').strip()),
                email=data.get('email', '').strip() or None,
                designation=data.get('designation', '').strip() or None,
                IAM=data.get('IAM', 'Employee').strip(),
                experience=data.get('experience', '').strip() or None,
                joining_date=data.get('joining_date', '').strip() or None,
                linkedin_url=data.get('linkedin_url', '').strip() or None,
                github_portfolio_url=data.get('github_portfolio_url', '').strip() or None,
                profile_summary=data.get('profile_summary', '').strip() or None,
                manager_id=data.get('manager_id') or None,
                total_utilization=0,
            )

            # ── Education ─────────────────────────────────────────
            for ed in data.get('educations', []):
                edu_id = 'E' + str(uuid.uuid4().int)[:8]
                Education.objects.create(
                    edu_id=edu_id,
                    employee=emp,
                    institution=ed.get('institution', '').strip() or None,
                    degree=ed.get('degree', '').strip() or None,
                    field_of_study=ed.get('field_of_study', '').strip() or None,
                    graduation_year=int(ed['graduation_year']) if ed.get('graduation_year') else None,
                    cgpa_or_percentage=float(ed['cgpa_or_percentage']) if ed.get('cgpa_or_percentage') else None,
                )

            # ── Certifications ────────────────────────────────────
            for cert in data.get('certifications', []):
                cert_name = cert.get('cert_name', '').strip()
                if cert_name:
                    cert_id = 'C' + str(uuid.uuid4().int)[:8]
                    Certification.objects.create(
                        cert_id=cert_id,
                        employee=emp,
                        cert_name=cert_name,
                    )

            # ── Previous Experience ───────────────────────────────
            for ex in data.get('previous_experiences', []):
                role = ex.get('role', '').strip()
                company = ex.get('company_name', '').strip()
                if role or company:
                    past_exp_id = 'P' + str(uuid.uuid4().int)[:8]
                    PreviousExperience.objects.create(
                        past_exp_id=past_exp_id,
                        employee=emp,
                        company_name=company or None,
                        role=role or None,
                        duration=ex.get('duration', '').strip() or None,
                        description=ex.get('description', '').strip() or None,
                    )

            # ── Skills ────────────────────────────────────────────
            for sk in data.get('skills', []):
                skill_name = sk.get('skill_name', '').strip()
                rating = sk.get('rating')
                if not skill_name:
                    continue
                skill_obj = Skill.objects.filter(skill_name__iexact=skill_name).first()
                if not skill_obj:
                    skill_obj = Skill.objects.create(
                        skill_id='S' + str(uuid.uuid4().int)[:6],
                        skill_name=skill_name,
                    )
                EmployeeSkill.objects.update_or_create(
                    employee=emp,
                    skill=skill_obj,
                    defaults={'aggregate_rating': float(rating) if rating else None},
                )

            threading.Thread(target=categorize_skills_if_needed).start()
            return JsonResponse({'success': True, 'emp_id': emp.emp_id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # GET ─────────────────────────────────────────────────────────
    all_employees = list(Employee.objects.values('emp_id', 'emp_name', 'designation', 'total_utilization').order_by('emp_name'))
    all_skills = list(Skill.objects.values_list('skill_name', flat=True).order_by('skill_name'))
    last_emp = Employee.objects.order_by('-emp_id').first()
    next_emp_id = (last_emp.emp_id + 1) if last_emp else 1001
    current_emp = Employee.objects.filter(emp_id=request.session.get('emp_id')).first()

    return render(request, 'records/add_employee.html', {
        'all_employees': all_employees,
        'all_skills_list': all_skills,   # raw list — json_script will encode it
        'next_emp_id': next_emp_id,
        'current_emp': current_emp,
    })


@iam_required('HR')
def delete_employee_view(request, emp_id):
    emp = get_object_or_404(Employee, emp_id=emp_id)
    if request.method == 'POST':
        emp.delete()
        messages.success(request, 'Employee deleted successfully.')
        return redirect('records:employee_list')
    return redirect('records:employee_detail', emp_id=emp_id)

@iam_required('HR', 'Manager')
def edit_employee_view(request, emp_id):
    emp = get_object_or_404(Employee, emp_id=emp_id)
    user_iam = get_session_iam(request)
    session_emp_id = str(request.session.get('emp_id'))
    
    if user_iam == 'Manager':
        # Verify manager scope - manager can only edit their direct reports
        if str(emp.manager_id) != session_emp_id and str(emp.emp_id) != session_emp_id:
            logger_project_ids = list(Project.objects.filter(manager_id__icontains=str(session_emp_id)).values_list('project_id', flat=True))
            emp_project_ids = list(Work.objects.filter(employee=emp).values_list('project_id', flat=True))
            if not any(pid in logger_project_ids for pid in emp_project_ids):
                return JsonResponse({'success': False, 'error': 'Access denied. You can only edit employees on your team.'})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # ── Basic Info ────────────────────────────────────────
            emp.emp_name = data.get('emp_name', '').strip()
            
            # Protect IAM and Password for Managers
            if user_iam == 'HR':
                if data.get('password', '').strip():
                    emp.password = make_password(data.get('password', '').strip())
                if 'IAM' in data:
                    emp.IAM = data.get('IAM').strip()
                    
            emp.email = data.get('email', '').strip() or None
            emp.designation = data.get('designation', '').strip() or None
            emp.experience = data.get('experience', '').strip() or None
            emp.joining_date = data.get('joining_date', '').strip() or None
            emp.linkedin_url = data.get('linkedin_url', '').strip() or None
            emp.github_portfolio_url = data.get('github_portfolio_url', '').strip() or None
            emp.profile_summary = data.get('profile_summary', '').strip() or None
            emp.manager_id = data.get('manager_id') or None
            emp.save()

            # ── Education ─────────────────────────────────────────
            Education.objects.filter(employee=emp).delete()
            for ed in data.get('educations', []):
                edu_id = 'E' + str(uuid.uuid4().int)[:8]
                Education.objects.create(
                    edu_id=edu_id,
                    employee=emp,
                    institution=ed.get('institution', '').strip() or None,
                    degree=ed.get('degree', '').strip() or None,
                    field_of_study=ed.get('field_of_study', '').strip() or None,
                    graduation_year=int(ed['graduation_year']) if ed.get('graduation_year') else None,
                    cgpa_or_percentage=float(ed['cgpa_or_percentage']) if ed.get('cgpa_or_percentage') else None,
                )

            # ── Certifications ────────────────────────────────────
            Certification.objects.filter(employee=emp).delete()
            for cert in data.get('certifications', []):
                cert_name = cert.get('cert_name', '').strip()
                if cert_name:
                    cert_id = 'C' + str(uuid.uuid4().int)[:8]
                    Certification.objects.create(
                        cert_id=cert_id,
                        employee=emp,
                        cert_name=cert_name,
                    )

            # ── Previous Experience ───────────────────────────────
            PreviousExperience.objects.filter(employee=emp).delete()
            for ex in data.get('previous_experiences', []):
                role = ex.get('role', '').strip()
                company = ex.get('company_name', '').strip()
                if role or company:
                    past_exp_id = 'P' + str(uuid.uuid4().int)[:8]
                    PreviousExperience.objects.create(
                        past_exp_id=past_exp_id,
                        employee=emp,
                        company_name=company or None,
                        role=role or None,
                        duration=ex.get('duration', '').strip() or None,
                        description=ex.get('description', '').strip() or None,
                    )

            # ── Skills ────────────────────────────────────────────
            EmployeeSkill.objects.filter(employee=emp).delete()
            for sk in data.get('skills', []):
                skill_name = sk.get('skill_name', '').strip()
                rating = sk.get('rating')
                if not skill_name:
                    continue
                skill_obj = Skill.objects.filter(skill_name__iexact=skill_name).first()
                if not skill_obj:
                    skill_obj = Skill.objects.create(
                        skill_id='S' + str(uuid.uuid4().int)[:6],
                        skill_name=skill_name,
                    )
                EmployeeSkill.objects.create(
                    employee=emp,
                    skill=skill_obj,
                    aggregate_rating=float(rating) if rating else None,
                )

            threading.Thread(target=categorize_skills_if_needed).start()
            messages.success(request, 'Employee updated successfully.')
            return JsonResponse({'success': True, 'emp_id': emp.emp_id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # GET ─────────────────────────────────────────────────────────
    all_employees = list(Employee.objects.values('emp_id', 'emp_name', 'designation', 'total_utilization').order_by('emp_name'))
    all_skills = list(Skill.objects.values_list('skill_name', flat=True).order_by('skill_name'))
    current_emp = Employee.objects.filter(emp_id=request.session.get('emp_id')).first()
    
    educations = list(Education.objects.filter(employee=emp).values())
    certifications = list(Certification.objects.filter(employee=emp).values())
    previous_experiences = list(PreviousExperience.objects.filter(employee=emp).values())
    skills = list(EmployeeSkill.objects.filter(employee=emp).values('skill__skill_name', 'aggregate_rating'))

    return render(request, 'records/edit_employee.html', {
        'emp': emp,
        'educations': educations,
        'certifications': certifications,
        'previous_experiences': previous_experiences,
        'emp_skills': skills,
        'all_employees': all_employees,
        'all_skills_list': all_skills,
        'current_emp': current_emp,
    })


@login_required_custom
def api_get_employees(request):
    """Secure endpoint to get the employee directory list for team builders."""
    employees_list = list(Employee.objects.values('emp_id', 'emp_name', 'designation', 'total_utilization'))
    return JsonResponse(employees_list, safe=False)


@login_required_custom
def api_get_project_team(request, project_id):
    """Secure endpoint to fetch a project's current team dynamically."""
    project = get_object_or_404(Project, project_id=project_id)
    current_team = []
    for work in project.works.all():
        skills = []
        for wa in work.skill_analyses.all():
            skills.append({
                'skill_name': wa.skill.skill_name,
                'rating': wa.rating
            })
            
        current_team.append({
            'emp_id': work.employee.emp_id,
            'emp_name': work.employee.emp_name,
            'role': work.role_in_project or '',
            'summary': work.work_summary or '',
            'utilization': work.utilization or 0,
            'base_util': (work.employee.total_utilization or 0) - (work.utilization or 0),
            'skills': skills
        })
    return JsonResponse(current_team, safe=False)


@login_required_custom
def api_get_employee_meta(request, emp_id):
    """Secure endpoint to get education, certs, and skills arrays for the edit employee form."""
    emp = get_object_or_404(Employee, emp_id=emp_id)
    return JsonResponse({
        'educations': list(Education.objects.filter(employee=emp).values()),
        'certifications': list(Certification.objects.filter(employee=emp).values()),
        'previous_experiences': list(PreviousExperience.objects.filter(employee=emp).values()),
        'emp_skills': list(EmployeeSkill.objects.filter(employee=emp).values('skill__skill_name', 'aggregate_rating'))
    })
