"""
Django cooomand to wait for the database to be available
"""
import time
from psycopg2 import OperationalError as Psycopg20pError
from django.db.utils import OperationalError

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Django command to wait for the database"""

    def handle(self, *args, **options):
        """ Entry point for command"""
        self.stdout.write("waiting for database")
        db_up = False
        while db_up is False:
            try:
                self.check(databases=['default'])
                db_up = True
            except (Psycopg20pError, OperationalError):
                self.stdout.write("database unavailable, waiting 1 seconds")
                time.sleep(1)
        self.stdout.write(self.style.SUCCESS("Database available!"))
