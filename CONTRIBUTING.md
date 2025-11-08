# Contributing to Chronicle

Thank you for your interest in contributing to Chronicle! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/chronicle.git
   cd chronicle
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your preferences
   ```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_algos.py

# Run with verbose output
pytest -v
```

## Code Quality

We use several tools to maintain code quality:

### Formatting
```bash
# Format code with Black
black chronicle apps tests

# Check formatting without changes
black --check chronicle apps tests
```

### Linting
```bash
# Lint with Ruff
ruff check chronicle apps tests

# Auto-fix issues
ruff check --fix chronicle apps tests
```

### Type Checking
```bash
# Type check with mypy
mypy chronicle apps
```

### Run All Checks
```bash
# Before committing, run:
black chronicle apps tests && \
ruff check chronicle apps tests && \
mypy chronicle apps && \
pytest
```

## Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, descriptive commit messages
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests and quality checks**
   ```bash
   pytest && black --check . && ruff check .
   ```

4. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub

5. **PR Requirements**
   - All tests must pass
   - Code coverage should not decrease
   - Code must pass linting and formatting checks
   - Include a clear description of changes
   - Reference any related issues

## Coding Standards

### Python Style
- Follow PEP 8
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use meaningful variable and function names

### Documentation
- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Update README.md for user-facing changes
- Update CHANGELOG.md for all changes

### Testing
- Write tests for new features
- Aim for >80% code coverage
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

## Project Structure

```
chronicle/
├── apps/               # Application entry points
│   ├── api/           # FastAPI application
│   └── collector/     # Data collection
├── chronicle/          # Core library
│   ├── cluster/       # Clustering algorithms
│   ├── nlp/          # NLP and embeddings
│   ├── storage/      # Database operations
│   └── timeline/     # Summarization
└── tests/             # Test suite
```

## Reporting Issues

### Bug Reports
Include:
- Chronicle version
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

### Feature Requests
Include:
- Use case description
- Proposed solution
- Alternative solutions considered
- Impact on existing functionality

## Questions?

- Open a [GitHub Discussion](https://github.com/dukeblue1994-glitch/chronicle/discussions)
- Check existing [Issues](https://github.com/dukeblue1994-glitch/chronicle/issues)
- Review the [README](README.md) and documentation

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to Chronicle! 🎉
