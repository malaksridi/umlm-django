from rest_framework import serializers

from core.models import Project, Module, ProjectModule, MiseAJour, Alert


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ["id", "name", "github_url", "reference_branch", "criticality", "is_custom_fork"]


class ProjectModuleSerializer(serializers.ModelSerializer):
    module = ModuleSerializer(read_only=True)

    class Meta:
        model = ProjectModule
        fields = ["id", "module", "status", "local_commit", "github_commit"]


class ProjectSerializer(serializers.ModelSerializer):
    project_modules = ProjectModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ["id", "name", "github_url", "reference_branch", "project_modules"]


class MiseAJourSerializer(serializers.ModelSerializer):
    class Meta:
        model = MiseAJour
        fields = ["id", "project_module", "status", "scanned_at"]


class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ["id", "mise_a_jour", "type", "channel", "sent_at"]
