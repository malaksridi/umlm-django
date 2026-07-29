"""
Commande : python manage.py create_user email nom role motdepasse

Aucun utilisateur n'est créé automatiquement par import_data (qui ne peuple
que Project/Module) — cette commande sert à créer les comptes de connexion
au dashboard (section 3 : Admin / Chef de projet / Développeur / Direction
technique), utilisable pour chaque personne du staff.

Exemple :
    python manage.py create_user malak@nachdit.com "Malak" admin "un-bon-mot-de-passe"

Rôles valides : admin, chef_de_projet, developpeur, direction_technique
"""
from django.core.management.base import BaseCommand, CommandError

from core.models import Role, User


class Command(BaseCommand):
    help = "Crée ou met à jour un utilisateur du dashboard avec un mot de passe"

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("name")
        parser.add_argument("role", choices=["admin", "chef_de_projet", "developpeur", "direction_technique"])
        parser.add_argument("password")

    def handle(self, *args, **options):
        role, _ = Role.objects.get_or_create(name=options["role"])

        user, created = User.objects.get_or_create(
            email=options["email"],
            defaults={"name": options["name"], "role": role},
        )
        user.name = options["name"]
        user.role = role
        user.set_password(options["password"])
        user.save()

        action = "créé" if created else "mis à jour"
        self.stdout.write(self.style.SUCCESS(f"Utilisateur {user.email} ({role.name}) {action}."))
