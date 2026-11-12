# Contributing

Contributions are welcome. Open an issue before large changes.

1. Use Python 3.11+.
2. Install development dependencies: python -m pip install -e ".[dev]".
3. Run pytest and ruff check .
4. Add tests for security-sensitive behavior.
5. Never commit credentials or add unreviewed command execution.

Any future remediation executor requires a separately reviewed design for isolation,
strict allow-lists, explicit human approval, backup, rollback, and security tests.
