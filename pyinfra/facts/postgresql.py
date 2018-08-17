# pyinfra
# File: pyinfra/facts/postgresql.py
# Desc: PostgreSQL facts

from pyinfra.api import FactBase
from pyinfra.api.util import try_int

from .util.databases import parse_columns_and_rows


def make_psql_command(
    database=None,
    user=None,
    password=None,
    host=None,
    port=None,
    executable='psql',
):
    target_bits = []

    if password:
        target_bits.append('PGPASSWORD="{0}"'.format(password))

    target_bits.append(executable)

    if database:
        target_bits.append('-d {0}'.format(database))

    if user:
        target_bits.append('-U {0}'.format(user))

    if host:
        target_bits.append('-h {0}'.format(host))

    if port:
        target_bits.append('-p {0}'.format(port))

    return ' '.join(target_bits)


def make_execute_psql_command(command, **postgresql_kwargs):
    return '{0} -Ac "{1}"'.format(
        make_psql_command(**postgresql_kwargs),
        command.replace('"', '\\"'),
    )


class PostgresqlFactBase(FactBase):
    abstract = True

    def command(
        self,
        postgresql_user=None, postgresql_password=None,
        postgresql_host=None, postgresql_port=None,
    ):
        return make_execute_psql_command(
            self.postgresql_command,
            user=postgresql_user,
            password=postgresql_port,
            host=postgresql_host,
            port=postgresql_port,
        )


class PostgresqlRoles(PostgresqlFactBase):
    '''
    Returns a list of PostgreSQL users.

    This fact lists all users registered in PostgreSQL, as well as their basic
    configuration and privileges.

    See PostgreSQL documentation for more information on the fields returned:
    https://www.postgresql.org/docs/current/static/view-pg-user.html
    '''

    default = dict
    postgresql_command = 'SELECT * FROM pg_catalog.pg_roles'

    def process(self, output):
        # Remove the last line of the output (row count)
        output = output[:-1]
        rows = parse_columns_and_rows(
            output, '|',
            # Remove the "rol" prefix on column names
            remove_column_prefix='rol',
        )

        users = {}

        for details in rows:
            for key, value in list(details.items()):
                if key in ('oid', 'connlimit'):
                    details[key] = try_int(value)

                if key in (
                    'super', 'inherit', 'createrole', 'createdb',
                    'canlogin', 'replication', 'bypassrls',
                ):
                    details[key] = value == 't'

            users[details.pop('name')] = details

        return users


class PostgresqlDatabases(PostgresqlFactBase):
    default = dict
    postgresql_command = '''
        SELECT pg_catalog.pg_encoding_to_char(encoding), *
        FROM pg_catalog.pg_database
    '''

    def process(self, output):
        # Remove the last line of the output (row count)
        output = output[:-1]
        rows = parse_columns_and_rows(
            output, '|',
            # Remove the "dat" prefix on column names
            remove_column_prefix='dat',
        )

        databases = {}

        for details in rows:
            details['encoding'] = details.pop('pg_encoding_to_char')

            for key, value in list(details.items()):
                if key.endswith('id') or key in (
                    'dba', 'tablespace', 'connlimit',
                ):
                    details[key] = try_int(value)

                if key in ('istemplate', 'allowconn'):
                    details[key] = value == 't'

            databases[details.pop('name')] = details

        return databases
