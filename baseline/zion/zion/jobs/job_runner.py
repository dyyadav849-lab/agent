from zion.jobs.daily_evaluation import JOB_NAME_DAILY_EVALUATION, daily_evaluation
from zion.jobs.sync_agent_plugin import JOB_NAME_SYNC_AGENT_PLUGIN, sync_agent_plugin

# the collection of jobs that we can call from the run job endpoint
job_collection = {
    JOB_NAME_SYNC_AGENT_PLUGIN: sync_agent_plugin,
    JOB_NAME_DAILY_EVALUATION: daily_evaluation,
}


async def job_runner(job_name: str) -> None:
    """Runs job based on the given job name. If the job name is not found, throws valueerrir"""
    import inspect

    job = job_collection.get(job_name)
    if job is None:
        message = f"Job with name {job_name} not found"
        raise ValueError(message)

    # Check if the job is async or sync
    if inspect.iscoroutinefunction(job):
        await job()
    else:
        # For sync jobs, just call them directly
        job()
