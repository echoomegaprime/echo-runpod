# Jobs

Serverless jobs are not training pods.

Read: `runpod_list_jobs`, `runpod_get_job`, `runpod_stream_job` (capped).

Track: id, endpoint, status, retries, GPU, timestamps. Cancel is a mutation.

Do not attach a job from project A to project B.
