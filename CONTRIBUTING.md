# Contributing to MCQ Format Standardizer

Thank you for considering contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/keyenhuang/MCQ-Format-Standardizer.git
cd MCQ-Format-Standardizer
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -r requirements.txt
```

## Code Style

- Follow PEP 8
- Run `black` before committing
- Use type hints for all public functions

## Testing

```bash
pytest
```

Make sure all tests pass before submitting a PR.

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-name/description`
2. Make your changes
3. Run tests and lint checks
4. Commit with descriptive messages
5. Push and open a Pull Request

## Reporting Issues

Use the GitHub issue tracker with the appropriate template.
