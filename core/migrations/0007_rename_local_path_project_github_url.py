from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_role_created_at"),
    ]

    operations = [
        migrations.RenameField(
            model_name="project",
            old_name="local_path",
            new_name="github_url",
        ),
        migrations.AlterField(
            model_name="project",
            name="github_url",
            field=models.URLField(max_length=500),
        ),
    ]
