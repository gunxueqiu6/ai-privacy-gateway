# Contributing to AI Privacy Gateway

Thank you for your interest in contributing to AI Privacy Gateway. This document provides guidelines and instructions for setting up a development environment, running tests, writing code, and submitting changes.

**Table of Contents**

- [Project Overview](#project-overview)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Code Style Guide](#code-style-guide)
- [Making Changes](#making-changes)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Commit Message Convention](#commit-message-convention)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)
- [Code of Conduct](#code-of-conduct)
- [License](#license)

---

## Project Overview

AI Privacy Gateway is an HTTP reverse proxy that intercepts AI API requests (OpenAI, DeepSeek, Anthropic, etc.) and automatically detects and masks PII (personally identifiable information) before it leaves your machine. It is built with:

- **Backend**: Python / FastAPI (core proxy, masking engine, admin dashboard)
- **Website**: Astro (public website at `website-astro/`)
- **SDKs**: JavaScript, Flutter/Dart, Android (Kotlin), iOS (Swift)
- **Native modules**: Rust (AC automaton via PyO3 for fast multi-pattern matching)

---

## Development Environment Setup

### Prerequisites

- **Python 3.11+**
- **Git**
- (Optional) Node.js 20+ for website development
- (Optional) Rust toolchain for native module development

### Step-by-Step Setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/your-username/ai-privacy-gateway
cd ai-privacy-gateway

# 2. Create and activate a virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS / Linux:
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. (Optional) Install optional dependencies for full functionality
pip install jieba  # NER engine support
pip install onnxruntime  # NER model inference

# 5. Verify the setup
python main.py --help
```

### Running the Server Locally

```bash
python main.py
```

The server starts on `http://localhost:9999` by default. Open it in a browser to access the admin dashboard.

### Website Development

```bash
cd website-astro
npm install
npm run dev
```

The website runs on `http://localhost:4321` by default.

---

## Project Structure

```
ai-privacy-gateway/
├── main.py                 # FastAPI entry point
├── config.py               # Configuration management
├── mask_engine.py          # Regex masking engine (14+ PII types)
├── ner_engine.py           # NER entity recognition engine
├── gateway_core.py         # HTTP proxy core
├── stream_buffer.py        # SSE streaming buffer
├── database.py             # SQLite encrypted vault
├── vault_crypto.py         # AES-256-GCM vault encryption
├── load_balancer.py        # Multi-upstream load balancer
├── audit.py                # Pub/sub audit event bus
├── routers/                # FastAPI route modules
│   ├── proxy.py            # Core proxy routes
│   ├── api.py              # Mask/restore API
│   ├── admin.py            # Admin dashboard routes
│   └── auth.py             # Authentication routes
├── static/                 # Admin dashboard UI assets
├── sdk/                    # Client SDKs
│   ├── browser-extension/  # Chrome/Edge browser extension
│   ├── js/                 # JavaScript/TypeScript SDK
│   ├── flutter/            # Flutter/Dart SDK
│   ├── android/            # Android (Kotlin) SDK
│   └── ios/                # iOS (Swift) SDK
├── tests/                  # Test suite
├── website-astro/          # Public-facing website (Astro)
├── installer/              # Installer scripts
├── scripts/                # Build and utility scripts
├── rust_src/               # Rust native modules (PyO3)
├── requirements.txt        # Python dependencies
├── pytest.ini              # Pytest configuration
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Docker image build
└── .env.example            # Environment variable template
```

---

## Running Tests

### Python Backend Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=term-missing

# Run with HTML coverage report
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_gateway.py -v

# Run tests matching a keyword
pytest tests/ -v -k "mask"

# Run with verbose output and no capture
pytest tests/ -v -s
```

### Test Configuration

The test configuration is in `pytest.ini`:

- Test discovery path: `tests/`
- File pattern: `test_*.py`
- Class pattern: `Test*`
- Function pattern: `test_*`
- Async mode: `auto` (`pytest-asyncio`)
- Default flags: `-v --tb=short`

### SDK Tests

Each SDK has its own test suite in its respective directory:

```bash
# JavaScript SDK
cd sdk/js
npm install
npm test

# Flutter SDK
cd sdk/flutter
flutter test
```

---

## Code Style Guide

### Python Backend

- Follow **PEP 8** conventions
- Use **type hints** on all function signatures
- Keep functions under 50 lines, files under 800 lines
- Add docstrings for public functions and classes using Google-style format
- Use `black` for formatting (line length: 120)
- Use `isort` for import sorting
- Use `ruff` for linting

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class MaskResult:
    """Result of a PII masking operation."""

    text: str
    entities: list[dict]
    mappings: dict[str, str]


def mask_text(text: str, entity_types: list[str] | None = None) -> MaskResult:
    """Detect and mask PII entities in the given text.

    Args:
        text: The input text to mask.
        entity_types: Optional list of entity types to detect.
                      If None, all supported types are used.

    Returns:
        A MaskResult containing the masked text, detected entities,
        and mapping of placeholders to original values.
    """
    ...
```

### Astro Website

- Follow standard TypeScript/React conventions
- Use `prettier` for formatting
- Keep components focused and reusable
- Use semantic HTML elements

### SDK Code

Each SDK follows the conventions of its language:

- **JavaScript/TypeScript**: ESLint + Prettier
- **Flutter/Dart**: `dart format`
- **Android/Kotlin**: ktlint
- **iOS/Swift**: SwiftFormat

### General Principles

- **Immutability**: Prefer creating new objects over mutating existing ones
- **Error handling**: Handle errors explicitly at every level; never silently swallow exceptions
- **Logging**: Use the `logging` module over `print()` statements
- **Security**: No hardcoded secrets; validate all inputs; use parameterized queries
- **Testing**: Maintain 80%+ test coverage; write tests before implementation (TDD)

---

## Making Changes

### Workflow

1. **Fork** the repository on GitHub
2. **Create a feature branch** from `master`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** — keep commits focused and atomic (one logical change per commit)
4. **Write or update tests** to cover your changes
5. **Run the full test suite** and ensure it passes
6. **Update documentation** if your changes affect the public API or behavior
7. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
8. **Open a Pull Request** against the `master` branch

### Before Committing

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] No `print()` or debug statements left
- [ ] No hardcoded secrets or credentials
- [ ] New code has corresponding tests
- [ ] Documentation is updated if needed
- [ ] Changes follow the code style guide

---

## Pull Request Guidelines

- Fill out the PR template completely
- Reference any related issues (e.g., "Closes #42")
- Keep changes focused and atomic — one feature or fix per PR
- Ensure all CI checks pass (tests, lint, build)
- Include screenshots or logs for UI or behavior changes
- Tag maintainers for review if the change is time-sensitive

### PR Title Format

```
<type>: <short description>
```

See [Commit Message Convention](#commit-message-convention) for valid types.

---

## Commit Message Convention

The project uses **Conventional Commits** for all commit messages.

### Format

```
<type>: <description>

[optional body]

[optional footer(s)]
```

### Types

| Type     | Usage                                              |
|----------|----------------------------------------------------|
| `feat`   | A new feature                                      |
| `fix`    | A bug fix                                          |
| `refactor` | Code change without feature or fix              |
| `docs`   | Documentation changes                              |
| `test`   | Adding or updating tests                           |
| `chore`  | Build, CI, dependencies, tooling                   |
| `perf`   | Performance improvement                            |
| `ci`     | CI/CD configuration changes                        |

### Examples

```
feat: add AES-256-GCM vault encryption for PII mappings
fix: handle SSE streaming double-prefix in proxy responses
docs: update deployment guide with Docker Compose example
test: add integration tests for load balancer strategies
chore: bump pytest to 8.2.0 for Python 3.13 support
```

---

## Reporting Issues

Report bugs via [GitHub Issues](https://github.com/gunxueqiu6/ai-privacy-gateway/issues).

### Bug Reports

Include the following information:

- **Clear description** of the problem
- **Steps to reproduce** — minimal, complete, verifiable example
- **Expected behavior** vs **actual behavior**
- **Environment**: Python version, OS, dependencies version
- **Configuration**: relevant `.env` settings (remove secrets)
- **Logs**: relevant error output or log entries

### Feature Requests

Feature requests are welcome via [GitHub Issues](https://github.com/gunxueqiu6/ai-privacy-gateway/issues).

Include:

- **Clear description** of the feature
- **Use case / motivation** — what problem does it solve?
- **Alternative solutions** considered (if any)
- **Example usage** (pseudocode or API sketch)

### Security Issues

For security vulnerabilities, **do not open a public issue**. Please contact the maintainers directly through GitHub or the contact information on the project website.

---

## Code of Conduct

- Be respectful and inclusive in all interactions
- Accept constructive criticism gracefully
- Focus on what is best for the project and the community
- Help others learn and grow
- Assume good faith intent

---

## License

By contributing to AI Privacy Gateway, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

## Questions?

If you have questions or need help getting started, open a [Discussion](https://github.com/gunxueqiu6/ai-privacy-gateway/discussions) or check the [documentation](https://privacygw.pages.dev/docs).
