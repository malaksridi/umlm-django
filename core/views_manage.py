# Destination: core/views_manage.py  (replace the whole file)
from django.shortcuts import render, redirect, get_object_or_404
from .models import Project, Module, Role, User
from .auth import role_required
from .forms_manage import ProjectForm, ModuleForm, RoleForm, UserForm


def _list_view(request, model, title, add_url, edit_url, delete_url, display_fields):
    items = model.objects.all()
    rows = [{"pk": obj.pk, "values": [getattr(obj, f, "") for f in display_fields]} for obj in items]
    return render(request, "core/manage/generic_list.html", {
        "title": title, "fields": display_fields, "rows": rows,
        "add_url": add_url, "edit_url": edit_url, "delete_url": delete_url,
    })


def _form_view(request, form_class, instance, title, list_url_name):
    form = form_class(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect(list_url_name)
    return render(request, "core/manage/generic_django_form.html", {
        "title": title, "form": form, "list_url": list_url_name,
    })


# ---------- PROJETS ----------

@role_required("admin")
def project_list(request):
    return _list_view(request, Project, "Projets", "project_add", "project_edit", "project_delete",
                       ["name", "local_path", "reference_branch"])

@role_required("admin")
def project_add(request):
    return _form_view(request, ProjectForm, None, "Ajouter un projet", "project_list")

@role_required("admin")
def project_edit(request, pk):
    return _form_view(request, ProjectForm, get_object_or_404(Project, pk=pk), "Modifier le projet", "project_list")

@role_required("admin")
def project_delete(request, pk):
    get_object_or_404(Project, pk=pk).delete()
    return redirect("project_list")


# ---------- MODULES ----------

@role_required("admin")
def module_list(request):
    return _list_view(request, Module, "Modules", "module_add", "module_edit", "module_delete",
                       ["name", "github_url", "reference_branch", "criticality"])

@role_required("admin")
def module_add(request):
    return _form_view(request, ModuleForm, None, "Ajouter un module", "module_list")

@role_required("admin")
def module_edit(request, pk):
    return _form_view(request, ModuleForm, get_object_or_404(Module, pk=pk), "Modifier le module", "module_list")

@role_required("admin")
def module_delete(request, pk):
    get_object_or_404(Module, pk=pk).delete()
    return redirect("module_list")


# ---------- ROLES ----------

@role_required("admin")
def role_list(request):
    return _list_view(request, Role, "Rôles", "role_add", "role_edit", "role_delete", ["name"])

@role_required("admin")
def role_add(request):
    return _form_view(request, RoleForm, None, "Ajouter un rôle", "role_list")

@role_required("admin")
def role_edit(request, pk):
    return _form_view(request, RoleForm, get_object_or_404(Role, pk=pk), "Modifier le rôle", "role_list")

@role_required("admin")
def role_delete(request, pk):
    get_object_or_404(Role, pk=pk).delete()
    return redirect("role_list")


# ---------- UTILISATEURS ----------

@role_required("admin")
def user_list(request):
    return _list_view(request, User, "Utilisateurs", "user_add", "user_edit", "user_delete",
                       ["name", "email", "role"])

@role_required("admin")
def user_add(request):
    form = UserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("user_list")
    return render(request, "core/manage/generic_django_form.html", {
        "title": "Ajouter un utilisateur", "form": form, "list_url": "user_list",
    })

@role_required("admin")
def user_edit(request, pk):
    obj = get_object_or_404(User, pk=pk)
    form = UserForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("user_list")
    return render(request, "core/manage/generic_django_form.html", {
        "title": "Modifier l'utilisateur", "form": form, "list_url": "user_list",
    })

@role_required("admin")
def user_delete(request, pk):
    get_object_or_404(User, pk=pk).delete()
    return redirect("user_list")
