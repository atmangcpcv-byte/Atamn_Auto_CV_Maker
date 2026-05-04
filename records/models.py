from django.db import models


class Employee(models.Model):
    ROLE_HR = 'HR'
    ROLE_MANAGER = 'Manager'
    ROLE_EMPLOYEE = 'Employee'
    ROLE_CHOICES = [
        ('HR', 'HR'),
        ('Manager', 'Manager'),
        ('Employee', 'Employee'),
    ]

    emp_id = models.IntegerField(primary_key=True)
    emp_name = models.CharField(max_length=200)
    IAM = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Employee')
    password = models.CharField(max_length=100)
    email = models.EmailField(max_length=200, blank=True, null=True)
    profile_summary = models.TextField(blank=True, null=True)
    linkedin_url = models.CharField(max_length=300, blank=True, null=True)
    github_portfolio_url = models.CharField(max_length=300, blank=True, null=True)
    joining_date = models.CharField(max_length=50, blank=True, null=True)
    manager_id = models.IntegerField(blank=True, null=True)
    designation = models.CharField(max_length=200, blank=True, null=True)
    experience = models.CharField(max_length=50, blank=True, null=True)
    total_utilization = models.FloatField(default=0, blank=True, null=True)

    class Meta:
        db_table = 'employee'

    def __str__(self):
        return self.emp_name

    def get_initials(self):
        parts = self.emp_name.split()
        return ''.join(p[0].upper() for p in parts[:2])

    @property
    def manager(self):
        if self.manager_id:
            try:
                return Employee.objects.get(emp_id=self.manager_id)
            except Employee.DoesNotExist:
                return None
        return None


class Project(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Completed', 'Completed'),
        ('On Hold', 'On Hold'),
        ('Cancelled', 'Cancelled'),
    ]
    project_id = models.IntegerField(primary_key=True)
    project_name = models.CharField(max_length=300)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True, choices=STATUS_CHOICES)
    manager_id = models.CharField(max_length=200, blank=True, null=True, db_column='manager_id')

    @property
    def get_managers(self):
        if not self.manager_id:
            return []
        ids = [int(x.strip()) for x in self.manager_id.split(',') if x.strip().isdigit()]
        return Employee.objects.filter(emp_id__in=ids)
        
    @property
    def get_manager_ids_list(self):
        if not self.manager_id:
            return []
        return [int(x.strip()) for x in self.manager_id.split(',') if x.strip().isdigit()]

    class Meta:
        db_table = 'project'

    def __str__(self):
        return self.project_name


class Skill(models.Model):
    skill_id = models.CharField(max_length=20, primary_key=True)
    skill_name = models.CharField(max_length=200)
    category = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        db_table = 'skill'

    def __str__(self):
        return self.skill_name


class Work(models.Model):
    work_id = models.CharField(max_length=20, primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='works', db_column='emp_id')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='works', db_column='project_id')
    role_in_project = models.CharField(max_length=200, blank=True, null=True)
    work_summary = models.TextField(blank=True, null=True)
    utilization = models.FloatField(default=0, blank=True, null=True)

    class Meta:
        db_table = 'work'

    def __str__(self):
        return f"{self.employee.emp_name} - {self.project.project_name}"


class Certification(models.Model):
    cert_id = models.CharField(max_length=20, primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='certifications', db_column='emp_id')
    cert_name = models.CharField(max_length=300)

    class Meta:
        db_table = 'certification'

    def __str__(self):
        return self.cert_name


class Education(models.Model):
    edu_id = models.CharField(max_length=20, primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='educations', db_column='emp_id')
    institution = models.CharField(max_length=300, blank=True, null=True)
    degree = models.CharField(max_length=100, blank=True, null=True)
    field_of_study = models.CharField(max_length=200, blank=True, null=True)
    graduation_year = models.IntegerField(blank=True, null=True)
    cgpa_or_percentage = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = 'education'

    def __str__(self):
        return f"{self.degree} - {self.institution}"


class EmployeeSkill(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='employee_skills', db_column='emp_id')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='employee_skills', db_column='skill_id')
    aggregate_rating = models.FloatField(blank=True, null=True)

    class Meta:
        db_table = 'employee_skill'
        unique_together = ('employee', 'skill')

    def rating_percentage(self):
        if self.aggregate_rating:
            return int((self.aggregate_rating / 5) * 100)
        return 0


class WorkSkillAnalysis(models.Model):
    analysis_id = models.CharField(max_length=20, primary_key=True)
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name='skill_analyses', db_column='work_id')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='work_analyses', db_column='skill_id')
    rating = models.FloatField(blank=True, null=True)
    justification = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'work_skill_analysis'


class ProjectTech(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='technologies', db_column='project_id')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='projects', db_column='skill_id')

    class Meta:
        db_table = 'project_tech'
        unique_together = ('project', 'skill')


class PreviousExperience(models.Model):
    past_exp_id = models.CharField(max_length=20, primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='previous_experiences', db_column='emp_id')
    company_name = models.CharField(max_length=300, blank=True, null=True)
    role = models.CharField(max_length=200, blank=True, null=True)
    duration = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'previous_experience'

    def __str__(self):
        return f"{self.role} at {self.company_name}"
