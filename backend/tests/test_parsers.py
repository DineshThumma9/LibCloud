from app.parser import DependencyParser, parse_pipfile, parse_workflow


class TestPipfileParser:
    def test_parse_pipfile_ignores_metadata(self):
        content = """
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
requests = "*"
fastapi = ">=0.100.0"

[dev-packages]
pytest = ">=7.0"

[requires]
python_version = "3.11"
"""
        deps = parse_pipfile(content)
        assert "requests" in deps
        assert "fastapi" in deps
        assert "pytest" in deps
        assert "python_version" not in deps


class TestWorkflowParser:
    def test_parse_workflow_actions(self):
        content = """
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v2
      - uses: appleboy/ssh-action@v0.1.10
"""
        raws = parse_workflow(content)
        assert "actions/checkout@v4" in raws
        assert "docker/setup-buildx-action@v2" in raws
        assert "appleboy/ssh-action@v0.1.10" in raws

        parser = DependencyParser()
        pkg_dic = parser.parser(content, ".github/workflows/ci.yml")
        assert "GitHub Actions" in pkg_dic
        assert "Docker" in pkg_dic
        assert "appleboy/ssh-action" in pkg_dic
