init:
	pip install -r requirements.txt

coverage:
	py.test --verbose --cov-report term --cov=betelgeuse tests.py

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
