from django.contrib import admin

from core.models import Role, User, Project, Module, ProjectModule, MiseAJour, Alert


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "role"]
    list_filter = ["role"]
    search_fields = ["name", "email"]


class ProjectModuleInline(admin.TabularInline):
    """
    Permet d'ajouter/modifier les modules d'un projet directement
    depuis la page du projet, sans naviguer ailleurs.
    """
    model = ProjectModule
    extra = 1
    fields = ["module", "status", "local_commit", "github_commit"]
    readonly_fields = ["status", "local_commit", "github_commit"]  # remplis par scan_modules, pas à la main


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "github_url", "reference_branch", "nb_modules"]
    search_fields = ["name"]
    inlines = [ProjectModuleInline]

    def nb_modules(self, obj):
        return obj.project_modules.count()
    nb_modules.short_description = "Modules intégrés"


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ["name", "criticality", "is_custom_fork", "github_url", "nb_projects"]
    list_filter = ["criticality", "is_custom_fork"]
    search_fields = ["name", "github_url"]

    def nb_projects(self, obj):
        return obj.project_modules.count()
    nb_projects.short_description = "Utilisé dans"


@admin.register(ProjectModule)
class ProjectModuleAdmin(admin.ModelAdmin):
    list_display = ["project", "module", "status", "local_commit", "github_commit"]
    list_filter = ["status", "module__criticality"]
    search_fields = ["project__name", "module__name"]


@admin.register(MiseAJour)
class MiseAJourAdmin(admin.ModelAdmin):
    list_display = ["project_module", "status", "scanned_at"]
    list_filter = ["status", "scanned_at"]
    date_hierarchy = "scanned_at"


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["type", "channel", "mise_a_jour", "sent_at"]
    list_filter = ["type", "channel"]
    date_hierarchy = "sent_at"
