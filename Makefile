all: test-coverage lint docs-html package

docs-clean:
	@cd docs; $(MAKE) clean

docs-html:
	@cd docs; $(MAKE) html

init:
	pip install -r requirements.txt

init-dev:
	pip install -r requirements-dev.txt

lint:
	flake8 betelgeuse/ tests/

package: package-clean
	python setup.py --quiet sdist bdist_wheel

package-clean:
	rm -rf build dist Betelgeuse.egg-info

publish: package
	twine upload dist/*

test-publish:
	python setup.py register -r testpypi
	python setup.py sdist upload -r testpypi
	python setup.py bdist_wheel upload -r testpypi

test:
	py.test -vv tests

test-coverage:
	py.test -vv --cov-report term --cov=betelgeuse tests

test-watch:
	ptw tests

.PHONY: all docs-clean docs-html init init-dev lint publish test-publish test \
        test-coverage
