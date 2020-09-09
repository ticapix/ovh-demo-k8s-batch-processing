TEST_FILE:=videos/PRIVATE 1/AVCHD/BDMV/STREAM/00104.MTS

docker-test-task: docker-build-task ## test task docker image
	env | grep OS_ > vars.env
	docker run --env-file ./vars.env $(REPO)-task batch_processing "$(TEST_FILE)" batch_processing_result

k8s-test-task: docker-push-task ## test task k8s job
	echo "[k8s]" > k8s.ini
	echo "docker_image=$(REPO)-task" >> k8s.ini
	echo "bucket_in=batch_processing" >> k8s.ini
	echo "filepath=$(TEST_FILE)" >> k8s.ini
	echo "bucket_out=batch_processing_result" >> k8s.ini
	echo "timestamp=`date +%s%N`" >> k8s.ini
	. ./activate && j2 --import-env env_vars --format=ini task/k8s-template.yml.j2 k8s.ini > k8s-task.yml
	. ./activate && kubectl apply -f k8s-task.yml
