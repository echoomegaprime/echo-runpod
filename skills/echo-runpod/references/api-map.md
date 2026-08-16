# API / capability map

| Echo tool | Nexus capability | Official MCP | Hint |
|---|---|---|---|
| runpod_status | echo.runpod.status | (compose list+billing) | read |
| runpod_list_pods | echo.runpod.list_pods | list-pods | read |
| runpod_get_pod | echo.runpod.get_pod | get-pod | read |
| runpod_stream_pod_logs | echo.runpod.stream_pod_logs | stream-pod-logs | read |
| runpod_list_gpu_types | echo.runpod.list_gpu_types | catalog | read |
| runpod_gpu_availability | echo.runpod.gpu_availability | catalog | read |
| runpod_gpu_pricing | echo.runpod.gpu_pricing | catalog | read |
| runpod_list_endpoints | echo.runpod.list_endpoints | endpoints | read |
| runpod_get_endpoint | echo.runpod.get_endpoint | endpoints | read |
| runpod_endpoint_health | echo.runpod.endpoint_health | endpoints | read |
| runpod_list_jobs | echo.runpod.list_jobs | jobs | read |
| runpod_get_job | echo.runpod.get_job | jobs | read |
| runpod_stream_job | echo.runpod.stream_job | jobs | read |
| runpod_list_volumes | echo.runpod.list_volumes | network volumes | read |
| runpod_get_volume | echo.runpod.get_volume | network volumes | read |
| runpod_billing | echo.runpod.billing | billing | read |
| runpod_prepare_training | echo.runpod.prepare_training | (local) | read |
| runpod_training_status | echo.runpod.training_status | logs/pods | read |
| runpod_training_checkpoints | echo.runpod.training_checkpoints | storage | read |
| runpod_create_pod | echo.runpod.create_pod | create-pod | mutate |
| runpod_start_pod | echo.runpod.start_pod | start-pod | mutate |
| runpod_stop_pod | echo.runpod.stop_pod | stop-pod | mutate |
| runpod_restart_pod | echo.runpod.restart_pod | restart-pod | mutate |
| runpod_terminate_pod | echo.runpod.terminate_pod | delete-pod | destructive |
| runpod_launch_training | echo.runpod.launch_training | create+exec | mutate |
| runpod_resume_training | echo.runpod.resume_training | start+exec | mutate |
