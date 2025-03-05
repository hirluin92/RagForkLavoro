import pytest
from models.apis.prompt_template_request_body import TemplateResolveRequest


def test_template_resolve_request_initialization():
    template = "Hello, {name}!"
    context = {"name": "World"}
    request = TemplateResolveRequest(template, context)

    assert request.template == template
    assert request.context == context


def test_template_resolve_request_initialization_no_context():
    template = "Hello, {name}!"
    request = TemplateResolveRequest(template)

    assert request.template == template
    assert request.context is None


def test_template_resolve_request_to_dict():
    template = "Hello, {name}!"
    context = {"name": "World"}
    request = TemplateResolveRequest(template, context)
    result = request.to_dict()

    assert result == {
        "template": template,
        "context": context
    }


def test_template_resolve_request_to_dict_no_context():
    template = "Hello, {name}!"
    request = TemplateResolveRequest(template)
    result = request.to_dict()

    assert result == {
        "template": template,
        "context": None
    }
