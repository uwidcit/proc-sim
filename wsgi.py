import warnings

# Flask-Admin 1.x still uses pkg_resources; silence Setuptools deprecation noise on CLI/boot
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*",
)

import click
import sys
from flask.cli import AppGroup

from App.database import get_migrate
from App.main import create_app
from App.controllers import (
    create_user,
    get_all_users_json,
    get_all_users,
    initialize,
)

app = create_app()
migrate = get_migrate(app)


@app.cli.command("init", help="Creates and initializes the database")
def init():
    initialize()
    print("database initialized")


user_cli = AppGroup("user", help="User object commands")


@user_cli.command("create", help="Creates a user")
@click.argument("username", default="rob")
@click.argument("password", default="robpass")
def create_user_command(username, password):
    create_user(username, password)
    print(f"{username} created!")


@user_cli.command("list", help="Lists users in the database")
@click.argument("format", default="string")
def list_user_command(format):
    if format == "string":
        print(get_all_users())
    else:
        print(get_all_users_json())


app.cli.add_command(user_cli)

test = AppGroup("test", help="Testing commands")


@test.command("user", help="Run User tests")
@click.argument("type", default="all")
def user_tests_command(type):
    import pytest

    if type == "unit":
        sys.exit(pytest.main(["-k", "UserUnitTests"]))
    elif type == "int":
        sys.exit(pytest.main(["-k", "UserIntegrationTests"]))
    else:
        sys.exit(pytest.main(["-k", "App"]))


app.cli.add_command(test)
