import asyncio
import random
import os
from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, RichLog, Header, Footer
from textual import work

from fastapi import FastAPI, Body
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from ingestion.agent import root_agent
from google.genai import types

# Load environment variables from .env file
load_dotenv()

_APP_NAME = "ingestion_agent"
_USER_ID = "6506806306"  #"minhazav@gmail.com"
_SESSION_ID = "default"
app = FastAPI()
session_service = InMemorySessionService()
session = asyncio.run(session_service.create_session(
    app_name=_APP_NAME, user_id=_USER_ID, session_id=_SESSION_ID
))

@app.post("/chat")
async def _chat_with_agent(message: str = Body(...), session_id: str = _SESSION_ID):
    # The Runner orchestrates the conversation state and tools
    runner = Runner(agent=root_agent, app_name=_APP_NAME,
                session_service=session_service)
    # run_async yields events, we collect the text from them
    response_text = ""
    message_final = f"user_id={_USER_ID}: {message}"
    content = types.Content(role="user", parts=[types.Part(text=message_final)])
    async for event in runner.run_async(
            user_id=_USER_ID, session_id=_SESSION_ID, new_message=content
        ):
        pass
        has_specific_part = False
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.executable_code:
                    print(
                            f"  Debug: Agent generated code:\n```python\n{part.executable_code.code}\n```"
                        )
                elif part.code_execution_result:
                    # Access outcome and output correctly
                    print(
                        f"  Debug: Code Execution Result: {part.code_execution_result.outcome} - Output:\n{part.code_execution_result.output}"
                    )
                    has_specific_part = True
                elif part.text and not part.text.isspace():
                    print(f"  Text: '{part.text.strip()}'")
                    response_text += part.text.strip()

    return response_text


class TaskTUI(App):
    """A Textual app to demonstrate a split-screen TUI for task processing."""

    CSS = """
    Screen {
        background: #1a1b26;
    }

    #output-container {
        height: 60%;
        border: solid #3b4261;
        background: #16161e;
        margin: 1;
        padding: 1;
    }

    #input-container {
        height: 30%;
        border: solid #3b4261;
        background: #16161e;
        margin: 1;
        padding: 1;
        align: center middle;
    }

    Input {
        width: 80%;
        border: double #7aa2f7;
    }

    Input.-disabled {
        border: double #414868;
        color: #565f89;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="output-container"):
            yield RichLog(id="output", highlight=True, markup=True)
        with Vertical(id="input-container"):
            yield Input(placeholder="Enter your request...", id="user-input")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#user-input").focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_input = event.input
        if not user_input.value.strip():
            return

        if user_input.value == "exit":
            self.exit()

        # Disable input and clear it
        input_widget = event.input
        input_widget.disabled = True
        query = input_widget.value
        input_widget.value = ""

        # Log the request
        output = self.query_one("#output", RichLog)
        output.write(f"[bold cyan]>[/bold cyan] Processing: [italic]{query}[/italic]")

        # Run the task in a worker
        self._run_task(query)

    def _log(self, message: str, prefix: str = ""):
        output = self.query_one("#output", RichLog)
        prefix_final = ""
        if prefix.strip():
            prefix_final = f"[bold green]{prefix}:[/bold green] "

        message_final = f"{prefix_final}{message}"
        output.write(message_final)

    @work(exclusive=True)
    async def _run_task(self, query: str) -> None:
        output = self.query_one("#output", RichLog)
        self._log("Processing: " + query, prefix="$")
        self._log("Connecting to ingestion agent.", prefix="$")
        response = await _chat_with_agent(query)
        self._log("Response from ingestion agent.", prefix="$")
        self._log(response, prefix="RESPONSE")
        self._log("Done!", prefix="TASK_COMPLETED")
        
        # Re-enable input
        input_widget = self.query_one("#user-input", Input)
        input_widget.disabled = False
        input_widget.focus()

if __name__ == "__main__":
    app = TaskTUI()
    app.run()
