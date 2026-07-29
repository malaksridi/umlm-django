# Destination: core/forms_manage.py  (replace the whole file)
from django import forms
from .models import Project, Module, Role, User


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "local_path", "reference_branch"]


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ["name", "github_url", "reference_branch", "criticality", "is_custom_fork"]


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ["name"]


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "email", "role"]
