all: test-coverage lint package

init:
	pip install -r requirements.txt

init-dev:
	pip install -r requirements-dev.txt

lint:
	flake8 betelgeuse.py

package:
	python setup.py --quiet sdist bdist_wheel

package-clean:
	rm -rf build dist Betelgeuse.egg-info

publish:
	python setup.py register
	python setup.py sdist upload
	python setup.py bdist_wheel upload

test-publish:
	python setup.py register -r testpypi
	python setup.py sdist upload -r testpypi
	python setup.py bdist_wheel upload -r testpypi

test:
	py.test tests.py

test-coverage:
	py.test --verbose --cov-report term --cov=betelgeuse tests.py

.PHONY: all init init-dev lint publish test-publish test test-coverage
