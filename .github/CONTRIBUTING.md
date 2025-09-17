# Contributing Guide

Thanks for your interest in contributing to the Kali Security MCP Server! This project packages a Kali-flavoured toolset for the Model Context Protocol, and we rely on community input to keep it useful and safe.

## Ways to Help

- Report bugs or usability issues
- Suggest new Kali tools or workflows to expose through the MCP API
- Improve documentation and examples
- Contribute code for new features or fixes

If you are unsure where to start, check the issue tracker for tickets labelled `good first issue` or open a discussion describing the improvements you have in mind.

## Development Environment

This repository mixes Python (for the MCP server) and Node.js (for the release tooling). The typical setup looks like this:

```bash
# Python dependencies via Poetry
pipx install poetry
poetry install

# Node.js dependencies for semantic-release
npm install
```

- Launch the server locally with `poetry run python kali_server.py`.
- Regenerate the Docker build requirements with `poetry export --without-hashes -f requirements.txt -o requirements.txt` whenever dependencies change.
- Use `docker build -t kali--mcp-server .` to test the container image.

## Coding Standards

- Follow the existing code style in the project.
- Keep documentation and inline comments concise and actionable.
- Add or update unit/integration tests when introducing behaviour changes.

### Commit Messages & Releases

We use [Conventional Commits](https://www.conventionalcommits.org/) to drive automated releases with `semantic-release`. Please structure your commit messages accordingly (`feat:`, `fix:`, `chore:`, etc.). The release pipeline will bump versions, publish changelog entries, and push git tags.

### Pull Request Checklist

Before requesting a review, please:

- Run relevant tests or manual checks for the area you changed
- Update documentation, the README, or `registry.yaml` as needed
- Ensure `CHANGELOG.md` stays untouched; semantic-release updates it during publishing
- Add context in the PR description (what changed, how it was tested, any follow-up work)

## Communication

We primarily coordinate through GitHub issues and pull requests. For larger proposals, open a GitHub discussion so the community can weigh in before significant implementation work begins.

## License

By contributing, you agree that your contributions will be licensed under the MIT License, the same as the rest of the project.
