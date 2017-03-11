import os

from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)


jinja_env = Environment(
    loader=FileSystemLoader('%s/templates/' % os.path.dirname(__file__)),
    trim_blocks=True,
    lstrip_blocks=True
)


def render(template_name, data):
    template = jinja_env.get_template(template_name)
    return template.render(**data)
