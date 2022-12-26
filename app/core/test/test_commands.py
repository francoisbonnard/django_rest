"""
Test custom Django management commands.

"""

from unittest.mock import patch
from psycopg2 import OperationalError as Psycopg2Error
from django.core.management import call_command
from django.db.utils import OperationalError
from django.test import SimpleTestCase


@patch("core.management.commands.wait_for_db.Command.check")
# Command.check is provided by BaseClass
class CommandTests(SimpleTestCase):
    """ Tests for psycopg2 management commands. """

    def test_wait_for_db_ready(self, patched_check):
        """ Test waiting for the database to be ready. """
        patched_check.return_value = True

        call_command("wait_for_db")

        patched_check.assert_called_once_with(databases=['default'])
        # AssertionError: Expected 'check' to be called once. Called 0 times.

    @patch('time.sleep')
    def test_wait_for_db_delay(self, patched_sleep, patched_check):
        '''
        Test that waiting for db when getting operationalError
        the first two times we call the mock method to raise Psycopg2Error
        then we raise three times the operationalError
        '''
        patched_check.side_effect = [Psycopg2Error] * 2 + \
            [OperationalError] * 3 + [True]

        call_command("wait_for_db")

        self.assertEqual(patched_check.call_count, 6)
        patched_check.assert_called_with(databases=['default'])
