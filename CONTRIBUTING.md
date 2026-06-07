# Contributing to AI Privacy Gateway

Thank you for your interest in contributing!

## Development Setup

```bash
# Fork and clone
git clone https://github.com/your-username/ai-privacy-gateway
cd ai-privacy-gateway

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_gateway.py -v
```

## Code Style

- Follow PEP 8
- Use type hints where possible
- Add docstrings for public functions/classes
- Keep lines under 120 characters

## Making Changes

1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes** and commit: `git commit -m 'Add some feature'`
4. **Push to your fork**: `git push origin feature/your-feature-name`
5. **Open a Pull Request**

## Pull Request Guidelines

- Fill out the PR template completely
- Reference any related issues
- Ensure all tests pass
- Update documentation if needed
- Keep changes focused and atomic

## Reporting Bugs

Please report bugs via [GitHub Issues](https://github.com/your-repo/ai-privacy-gateway/issues) with:

- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Python version, OS, and any relevant configuration

## Suggesting Features

Feature requests are welcome! Open an issue with:

- Clear description of the feature
- Use case / motivation
- Any alternative solutions considered

## Code of Conduct

- Be respectful and inclusive
- Accept constructive criticism gracefully
- Focus on what's best for the community

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
