TEST_FILE:=videos/PRIVATE 1/AVCHD/BDMV/STREAM/00103.MTS

docker-test-task: docker-build-task ## test task docker image
	env | grep OS_ > vars.env
	docker run --env-file ./vars.env $(REPO)-task batch_processing "$(TEST_FILE)" batch_processing_result

k8s-test-task: docker-push-task ## test task k8s job
	echo "[job]" > job.ini
	echo "docker_image=$(REPO)-task" >> job.ini
	echo "bucket_in=batch_processing" >> job.ini
	echo "filepath=$(TEST_FILE)" >> job.ini
	echo "bucket_out=batch_processing_result" >> job.ini
	echo "timestamp=`date +%s%N`" >> job.ini
	j2 --import-env env_vars --format=ini task/job-template.yml.j2 job.ini > job.yml
	kubectl apply -f job.yml
