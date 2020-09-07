ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
ROOT_NAME:=$(shell basename $(ROOT_DIR))
REPO?=ticapix/$(ROOT_NAME)
TAG?=latest
RM=rm -rf

DOCKERFILES=$(shell find * -type f -name Dockerfile)
BUILD_IMAGES=$(addprefix docker-build-, $(subst /,\:,$(subst /Dockerfile,,$(DOCKERFILES))))
PUSH_IMAGES=$(addprefix docker-push-, $(subst /,\:,$(subst /Dockerfile,,$(DOCKERFILES))))

.PHONY: help

help:
	@echo "$(ROOT_NAME)"
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m=> %s\n", $$1, $$2}'

venv3: # create venv folder
	python3 -m venv venv3
	./venv3/bin/pip install -Ur requirements.txt

deps: venv3

$(BUILD_IMAGES): deps
	$(eval image=$(subst docker-build-,,$@))
	docker build -f $(image)/Dockerfile -t $(REPO)-$(image):master $(image)
	docker tag $(REPO)-$(image):master $(REPO)-$(image):$(TAG)

docker-build: $(BUILD_IMAGES) ## build dockers images

$(PUSH_IMAGES): docker-build
	$(eval image=$(subst docker-push-,,$@))
	docker push $(REPO)-$(image)

docker-push: docker-build $(PUSH_IMAGES) ## push docker images

# docker-enter-image: docker-build  ## for local manual testing
# 	docker run -it --entrypoint sh $(REPO):master

# deploy: ## deploy plugin on the cluster
# 	kubectl apply -f setup/service-account.yaml
# 	kubectl apply -f setup/storageos-monitoring.yaml

# undeploy: ## remove plugin from the cluster
# 	kubectl delete -f setup/storageos-monitoring.yaml || true
# 	kubectl delete -f setup/service-account.yaml || true

# watch-log:
# 	kubectl -n storageos-operator logs -f `kubectl -n storageos-operator get pod -l app=storageos-monitoring -o jsonpath='{.items[0].metadata.name}'`
	
clean: ## remove development files
	$(RM) ./venv3
	$(RM) job.*
	$(RM) vars.env

include task/Makefile
include monitor/Makefile