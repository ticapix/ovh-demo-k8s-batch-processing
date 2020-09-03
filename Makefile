ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
NAME=$(shell basename $(ROOT_DIR))
REPO?=ticapix/$(NAME)
TAG?=latest
RM=rm -rf

TEST_FILE=videos/PRIVATE 1/AVCHD/BDMV/STREAM/00103.MTS

.PHONY: help

help:
	@echo "$(NAME)"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m=> %s\n", $$1, $$2}'

venv3: # create venv folder
	python3 -m venv venv3
	./venv3/bin/pip install -Ur requirements.txt

deps: venv3

docker-build: deps ## build docker image
	docker build -f task/Dockerfile -t $(REPO):master task
	docker tag $(REPO):master $(REPO):$(TAG)

docker-push: docker-build ## push docker image to hub.docker.io
	docker push $(REPO)

docker-test: docker-build ## docker image test
	env | grep OS_ > vars.env
	docker run --env-file ./vars.env $(REPO) batch_processing "$(TEST_FILE)" batch_processing_result

k8s-test: docker-push ## k8s job test
	echo "[job]" > job-template.ini
	echo "bucket_in=batch_processing" >> job-template.ini
	echo "filepath=$(TEST_FILE)" >> job-template.ini
	echo "bucket_out=batch_processing_result" >> job-template.ini
	echo "timestamp=`date +%s%N`" >> job-template.ini
	j2 --import-env env_vars --format=ini job-template.yml.j2 job-template.ini > job.yml
	kubectl apply -f job.yml

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
