from django.urls import path
from . import views

app_name = 'records'

urlpatterns = [
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('employees/', views.employee_list_view, name='employee_list'),
    path('employees/add/', views.add_employee_view, name='add_employee'),
    path('employees/<int:emp_id>/', views.employee_detail_view, name='employee_detail'),
    path('employees/<int:emp_id>/edit/', views.edit_employee_view, name='edit_employee'),
    path('employees/<int:emp_id>/delete/', views.delete_employee_view, name='delete_employee'),
    path('employees/<int:emp_id>/resume/', views.download_resume_view, name='download_resume'),
    path('projects/', views.project_list_view, name='project_list'),
    path('projects/add/', views.add_project_view, name='add_project'),
    path('projects/add/generate/', views.generate_project_ai, name='generate_project_ai'),
    path('projects/<int:project_id>/', views.project_detail_view, name='project_detail'),
    path('projects/<int:project_id>/edit/', views.edit_project_view, name='edit_project'),
    path('projects/<int:project_id>/delete/', views.delete_project_view, name='delete_project'),
    path('skills/', views.skills_view, name='skills'),
    path('profile/', views.my_profile_view, name='my_profile'),
    
    # API Endpoints
    path('api/employees/', views.api_get_employees, name='api_employees'),
    path('api/employees/<int:emp_id>/meta/', views.api_get_employee_meta, name='api_employee_meta'),
    path('api/projects/<int:project_id>/team/', views.api_get_project_team, name='api_project_team'),
]
