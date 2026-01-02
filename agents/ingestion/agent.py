import time

from google.adk.agents.llm_agent import Agent
from tinydb import TinyDB, Query

_db = TinyDB('db.json')

_SYSTEM_INSTRUCTION = """\
You are an AI Assistant helping users manage their personal lives around topics like health, fitness, finance, travel etc.

## High Level Goals

1. You try to understand if the user query is a task or information. Any form of question can be considered as a task as well.
2. If it's an information you try to save the information into an unstructured storage and forward the information to storage structuring agent.
3. If it's a task you try to break it down into smaller subtasks and forward the information to task execution agent.

## Guidelines

1. If you execute a tool, you should return the tool output as a string.
2. Every user query must have a user id in form of `user_id=<some id>`. You should extract and pass this during the tool calls.
"""

def _add_content(user_id: str, content: dict) -> bool:
	current_timestamp = int(time.time())
	if not 'timestamp' in content:
		content['timestamp'] = current_timestamp


	existing_data = _db.search((Query().user_id == user_id))
	if not existing_data:
		existing_data = {'user_id': user_id, 'content': []}
		_db.insert(existing_data)
	else:
		existing_data = existing_data[0]
	
	print(f"{existing_data=}")
	existing_data['content'].append(content)
	_db.update(existing_data, (Query().user_id == user_id))
	return True


def _ingest_task(user_id: str, task: str, task_steps: list[str]) -> bool:
	new_data = {'type': 'task', 'task': task, 'task_steps': task_steps}
	return _add_content(user_id, new_data)


def _ingest_information(user_id: str, information: str) -> bool:
	new_data = {'type': 'information', 'information': information}
	return _add_content(user_id, new_data)


def ingest_task(user_id: str, task: str, task_steps: list[str]) -> str:
	"""Ingest a task and its steps.
	
	Args:
		task (str): The task to ingest.
		task_steps (list[str]): The steps of the task to ingest.
	
	Returns:
		str: The ingested task.
	"""
	print(f"Ingesting task: {task}")
	if not _ingest_task(user_id, task, task_steps):
		return f"Failed to ingest task: {task}"
	# Generate a response for the LLM.
	task_steps_str = "\n".join(task_steps)
	return f"""\
[Task Ingestion]

Task: {task}
Task Steps:

{task_steps_str}
"""

def ingest_information(user_id: str, information: str) -> str:
	"""Ingest information.
	
	Args:
		information (str): The information to ingest.
	
	Returns:
		str: The ingested information.
	"""
	print(f"Ingesting information: {information}")
	if not _ingest_information(user_id, information):
		return f"Failed to ingest information: {information}"
	
	# Generate a response for the LLM.
	return f"""\
[Information Ingestion]

Information:

{information}
"""

root_agent = Agent(
    model='gemini-3-flash-preview',
    name='ingestion_agent',
    description="AI Assistant for ingesting information and tasks.",
    instruction=_SYSTEM_INSTRUCTION,
    tools=[ingest_task, ingest_information],
)