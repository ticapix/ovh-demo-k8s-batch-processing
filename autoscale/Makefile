docker-test-autoscale: docker-build-autoscale ## test autoscale docker image
	docker run --env NODEPOOL_NAME=compute --env KUBECONFIG=/config/$(shell basename $(KUBECONFIG)) -v $(shell dirname $(KUBECONFIG)):/config $(REPO)-autoscale

# k8s-test-monitor: docker-push-monitor ## test monitor k8s job
# 	echo "[job]" > job.ini
# 	echo "docker_image=$(REPO)-task" >> job.ini
# 	echo "bucket_in=batch_processing" >> job.ini
# 	echo "filepath=$(TEST_FILE)" >> job.ini
# 	echo "bucket_out=batch_processing_result" >> job.ini
# 	echo "timestamp=`date +%s%N`" >> job.ini
# 	. ./activate && j2 --import-env env_vars --format=ini task/job-template.yml.j2 job.ini > job.yml
# 	. ./activate && kubectl apply -f job.yml
