# https://www.gnu.org/software/make/manual/html_node/Phony-Targets.html
.PHONY: clean clean-build clean-pyc help
# https://www.gnu.org/software/make/manual/html_node/Special-Variables.html
.DEFAULT_GOAL := help

#
PACKAGE_NAME=$(shell python setup.py --name)
PACKAGE_FULLNAME=$(shell python setup.py --fullname)
PACKAGE_VERSION:=$(shell python setup.py --version | tr + _)
#
PROJECT_NAME?=$(PACKAGE_NAME)
APP_ENTRY_POINT?=$(PACKAGE_NAME)
#
DOCKER_USER?=yoyonel
DOCKER_TAG?=$(DOCKER_USER)/$(PROJECT_NAME):${PACKAGE_VERSION}
#
PYPI_SERVER?=https://test.pypi.org/simple/
PYPI_SERVER_FOR_UPLOAD?=pypitest
PYPI_CONFIG_FILE?=${HOME}/.pypirc
PYPI_REGISTER?=
# https://stackoverflow.com/questions/2019989/how-to-assign-the-output-of-a-command-to-a-makefile-variable
PYPI_SERVER_HOST=$(shell echo $(PYPI_SERVER) | sed -e "s/[^/]*\/\/\([^@]*@\)\?\([^:/]*\).*/\2/")
PYTEST_OPTIONS?=-v
#
TOX_DIR?=${HOME}/.tox/$(PROJECT_NAME)
#
SDIST_PACKAGE=dist/${shell python setup.py --fullname}.tar.gz
SOURCES=$(shell find src/ -type f -name '*.py') setup.py MANIFEST.in

MONGODB_USER?=user
MONGODB_PASSWORD?=password
MONGODB_DBNAME?=pyconfr_2019_grpc_nlp
MONGODB_ADMIN_PASSWORD?=password

# https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help: ## This help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

all: docker

${SDIST_PACKAGE}: ${SOURCES}
	@echo "Building python project..."
	@python setup.py sdist

sdist: ${SDIST_PACKAGE}

docker: ${SDIST_PACKAGE} docker/Dockerfile	## Building docker image for storage server application
	@echo PYPI_SERVER: $(PYPI_SERVER)
	@docker build \
		--build-arg PYPI_SERVER=$(PYPI_SERVER) \
		--build-arg APP_ENTRY_POINT=$(APP_ENTRY_POINT) \
		-t $(DOCKER_TAG) \
		-f docker/Dockerfile \
		.

docker-run:
	@docker run --rm -it ${DOCKER_RUN_OPTIONS} $(DOCKER_TAG)

pypi-register:
	python setup.py register -r ${PYPI_REGISTER}
	
pypi-upload: ${SDIST_PACKAGE}
	twine upload \
		--repository ${PYPI_SERVER_FOR_UPLOAD} \
		--config-file ${PYPI_CONFIG_FILE} \
		dist/*

pip-install:
	@pip install \
		-r requirements_dev.txt \
		--trusted-host $(PYPI_SERVER_HOST) \
		--extra-index-url $(PYPI_SERVER) \
		--upgrade

pytest:
	pytest ${PYTEST_OPTIONS}

tox:
	# http://ahmetdal.org/jenkins-tox-shebang-problem/
	tox --workdir ${TOX_DIR}

clean: clean-build clean-pyc ## remove all build, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
