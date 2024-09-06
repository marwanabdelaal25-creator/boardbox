.PHONY: install test cov lint clean

install:
	pip install -e ".[dev]"

test:
	pytest -q

cov:
	pytest --cov=boardbox --cov-report=term-missing

lint:
	ruff check src tests

clean:
	rm -rf build dist .pytest_cache .coverage htmlcov *.egg-info
