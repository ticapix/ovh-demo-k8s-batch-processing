docker-test-autoscale: docker-build-autoscale ## test autoscale docker image
	docker run --env NODEPOOL_NAME=compute --env LOGLEVEL=DEBUG --env KUBECONFIG=/config/$(shell basename $(KUBECONFIG)) -v $(shell dirname $(KUBECONFIG)):/config $(REPO)-autoscale

k8s-test-autoscale: docker-push-autoscale ## test autoscale k8s job
	. ./activate && kubectl delete -f k8s-autoscale.yml || true
	echo "[k8s]" > k8s.ini
	echo "docker_image=$(REPO)-autoscale" >> k8s.ini
	echo "nodepool_name=compute" >> k8s.ini
	echo "log_level=info" >> k8s.ini
	. ./activate && j2 --import-env env_vars --format=ini autoscale/k8s-template.yml.j2 k8s.ini > k8s-autoscale.yml
	. ./activate && kubectl create -f k8s-autoscale.yml
	. ./activate && kubectl auth reconcile -f k8s-autoscale.yml
	kubectl auth can-i --as system:serviceaccount:default:nodepool-autoscale --list
	kubectl auth can-i --all-namespaces --as system:serviceaccount:default:nodepool-autoscale list pods
	kubectl auth can-i --all-namespaces --as system:serviceaccount:default:nodepool-autoscale list nodes
	kubectl auth can-i --all-namespaces --as system:serviceaccount:default:nodepool-autoscale get nodepools/compute
	kubectl auth can-i --all-namespaces --as system:serviceaccount:default:nodepool-autoscale patch nodepools/compute
