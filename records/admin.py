from django.contrib import admin
from .models import (
    Employee, Project, Skill, Work, Certification,
    Education, EmployeeSkill, WorkSkillAnalysis, ProjectTech
)

admin.site.register(Employee)
admin.site.register(Project)
admin.site.register(Skill)
admin.site.register(Work)
admin.site.register(Certification)
admin.site.register(Education)
admin.site.register(EmployeeSkill)
admin.site.register(WorkSkillAnalysis)
admin.site.register(ProjectTech)
