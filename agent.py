"""
AI Coding Agent – Assignment Solution
======================================
Uses the official Google Generative AI SDK (google-genai) with function
calling to autonomously explore the node-easy-notes-app repository and
implement improvements for organising and searching notes.

Usage:
    pip install google-genai python-dotenv
    python agent.py

Requirements:
    GEMINI_API_KEY must be set in .env or as an environment variable.
"""

import asyncio
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from dotenv import load_dotenv
import google.genai as genai
from google.genai import types


# Bootstrap
load_dotenv()

REPO_URL  = "https://github.com/callicoder/node-easy-notes-app"
WORKSPACE = Path(__file__).parent / "workspace" / "node-easy-notes-app"


# Tool implementations
def list_files(path: str) -> str:
    """Recursively list all files in a directory inside the workspace."""
    target = WORKSPACE / path
    if not target.exists():
        return f"ERROR: Path does not exist: {target}"
    result = []
    for p in sorted(target.rglob("*")):
        if ".git" in p.parts:
            continue
        rel = p.relative_to(WORKSPACE)
        result.append(str(rel) + ("/" if p.is_dir() else ""))
    return "\n".join(result) if result else "(empty directory)"


def read_file(path: str) -> str:
    """Read the full contents of a file inside the cloned repository."""
    target = WORKSPACE / path
    if not target.exists():
        return f"ERROR: File does not exist: {target}"
    if not target.is_file():
        return f"ERROR: Not a file: {target}"
    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR reading file: {e}"


def write_file(path: str, content: str) -> str:
    """Write (or overwrite) a file inside the cloned repository."""
    target = WORKSPACE / path
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"OK: Written {len(content)} bytes to {path}"
    except Exception as e:
        return f"ERROR writing file: {e}"


def run_shell(command: str) -> str:
    """Run a shell command in the repository root and return its output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout.strip()
        err    = result.stderr.strip()
        parts  = []
        if output:
            parts.append(output)
        if err:
            parts.append(f"[stderr] {err}")
        return "\n".join(parts) if parts else "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out after 60 seconds"
    except Exception as e:
        return f"ERROR running command: {e}"


def create_plan(plan_text: str) -> str:
    """Record the agent's execution plan to disk and print it."""
    plan_path = Path(__file__).parent / "execution_plan.txt"
    plan_path.write_text(plan_text, encoding="utf-8")
    print("\n" + "=" * 60)
    print("📋  AGENT EXECUTION PLAN")
    print("=" * 60)
    print(plan_text)
    print("=" * 60 + "\n")
    return f"Plan saved to {plan_path}"


def summarise_changes(summary_text: str) -> str:
    """Record a summary of all changes made to disk and print it."""
    summary_path = Path(__file__).parent / "changes_summary.txt"
    summary_path.write_text(summary_text, encoding="utf-8")
    print("\n" + "=" * 60)
    print("✅  CHANGES SUMMARY")
    print("=" * 60)
    print(summary_text)
    print("=" * 60 + "\n")
    return f"Summary saved to {summary_path}"



# Tool dispatcher
TOOL_FUNCTIONS = {
    "list_files":       list_files,
    "read_file":        read_file,
    "write_file":       write_file,
    "run_shell":        run_shell,
    "create_plan":      create_plan,
    "summarise_changes": summarise_changes,
}

def dispatch_tool(name: str, args: dict) -> str:
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return f"ERROR: Unknown tool '{name}'"
    try:
        return fn(**args)
    except Exception as e:
        return f"ERROR calling {name}: {e}"



# Tool declarations for the Gemini API
TOOL_DECLARATIONS = types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="list_files",
        description="Recursively list all files in a directory inside the cloned repository. Use '.' for the root.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "path": types.Schema(type=types.Type.STRING,
                    description="Relative path inside the cloned repo, e.g. '.' or 'app'")
            },
            required=["path"]
        )
    ),
    types.FunctionDeclaration(
        name="read_file",
        description="Read the full contents of a file inside the cloned repository.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "path": types.Schema(type=types.Type.STRING,
                    description="Relative file path, e.g. 'server.js' or 'app/models/note.model.js'")
            },
            required=["path"]
        )
    ),
    types.FunctionDeclaration(
        name="write_file",
        description="Write or overwrite a file inside the cloned repository with the given content.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "path":    types.Schema(type=types.Type.STRING,
                    description="Relative file path inside the cloned repo"),
                "content": types.Schema(type=types.Type.STRING,
                    description="Full content to write to the file")
            },
            required=["path", "content"]
        )
    ),
    types.FunctionDeclaration(
        name="run_shell",
        description="Run a shell command in the repository root and return stdout/stderr. Use for git and node --check.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "command": types.Schema(type=types.Type.STRING,
                    description="Shell command to run, e.g. 'git status' or 'node --check server.js'")
            },
            required=["command"]
        )
    ),
    types.FunctionDeclaration(
        name="create_plan",
        description="Save the execution plan before making any file changes. Call this once after exploration.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "plan_text": types.Schema(type=types.Type.STRING,
                    description="Numbered list of every planned change with rationale")
            },
            required=["plan_text"]
        )
    ),
    types.FunctionDeclaration(
        name="summarise_changes",
        description="Save a complete summary of all changes made. Call this after all modifications are done.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "summary_text": types.Schema(type=types.Type.STRING,
                    description="Markdown-formatted summary of every file changed and feature added")
            },
            required=["summary_text"]
        )
    ),
])



# System prompt
SYSTEM_INSTRUCTIONS = textwrap.dedent("""
    You are a senior Node.js developer and an autonomous AI coding agent.

    Your goal is to improve the note-taking REST API in the workspace so that
    users can better organise and search their notes.

    You have six tools: list_files, read_file, write_file, run_shell,
    create_plan, and summarise_changes.

    ## Mandatory Workflow

    1. EXPLORE
       - Call list_files('.') to see all files
       - Call read_file() on every relevant source file (model, controller,
         routes, server.js, package.json)
       - Fully understand the codebase before touching anything

    2. PLAN
       - Call create_plan() with a clear numbered list of every change you
         will make. Do NOT skip this step.

    3. IMPLEMENT
       - Call write_file() for each file that needs changing
       - Always write the COMPLETE file content — never partial content
       - Preserve all existing functionality and route shapes

    4. VALIDATE
       - Call run_shell('node --check <file>') on every modified JS file
       - Fix any syntax errors found before continuing

    5. GIT COMMIT
       - run_shell('git add -A')
       - run_shell('git commit -m "feat: add tags, full-text search, pagination and sort to notes API"')

    6. SUMMARISE
       - Call summarise_changes() with a detailed Markdown summary of every
         file changed and every feature added, including example API calls

    ## What to implement

    A) Tags — Add tags: [String] to the Note model. Accept tags on
       create/update. Add GET /notes/tags/:tag endpoint.

    B) Full-text search — Add a MongoDB text index on title+content.
       Add GET /notes/search?q=<query> endpoint.

    C) Pagination — GET /notes accepts ?page and ?limit params.
       Return { data, total, page, limit, totalPages } envelope.

    D) Sorting — GET /notes accepts ?sort=<field> and ?order=asc|desc params.

    ## Rules
    - Never break existing routes or their response shapes
    - Always write complete file contents in write_file()
    - The app stays Node.js — do not rewrite in Python
    - No new npm packages needed (use native MongoDB/Mongoose features)
    - Declare /notes/search and /notes/tags/:tag BEFORE /notes/:noteId
      in routes to avoid Express treating them as noteId values
""").strip()



# Repository bootstrap
def ensure_repo_cloned() -> None:
    if WORKSPACE.exists() and (WORKSPACE / "server.js").exists():
        print(f"✓  Repository already present at {WORKSPACE}")
        return
    print(f"⬇  Cloning {REPO_URL} …")
    WORKSPACE.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", REPO_URL, str(WORKSPACE)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.exit(f"ERROR: git clone failed:\n{result.stderr}")
    print("✓  Repository cloned successfully.")



# Agentic loop
def run_agent(api_key: str) -> None:
    client = genai.Client(api_key=api_key)
    model  = "gemini-3.5-flash-lite"

    task = (
        "Improve the application so users can better organise and search their notes.\n\n"
        "Start by exploring the repository with list_files and read_file, then "
        "call create_plan, implement all changes, validate JS syntax with node --check, "
        "commit with git, and finally call summarise_changes with a complete Markdown "
        "summary of everything you did."
    )

    print(f"\n📨  Task: {task}\n")
    print("🤖  Agent is running…\n")

    # Build the initial message history
    contents = [
        types.Content(role="user", parts=[types.Part(text=task)])
    ]

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTIONS,
        tools=[TOOL_DECLARATIONS],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.AUTO
            )
        ),
    )

    iteration = 0
    max_iterations = 40  # safety cap

    while iteration < max_iterations:
        iteration += 1
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        candidate   = response.candidates[0]
        finish_reason = str(candidate.finish_reason)

        # Collect all parts from the response
        tool_calls_made = []
        text_parts      = []

        for part in candidate.content.parts:
            if part.function_call:
                tool_calls_made.append(part.function_call)
            elif part.text:
                text_parts.append(part.text)

        # Print any text the model produced
        if text_parts:
            combined = "".join(text_parts).strip()
            if combined:
                print(f"\n🤖  Agent: {combined}\n")

        # Append model response to history
        contents.append(types.Content(
            role="model",
            parts=candidate.content.parts
        ))

        # If no tool calls and model is done, break
        if not tool_calls_made:
            print(f"\n✅  Agent finished (finish_reason={finish_reason})")
            break

        # Execute all tool calls and collect results
        tool_result_parts = []
        for fc in tool_calls_made:
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}

            print(f"🔧  Tool call: {tool_name}({json.dumps(tool_args, ensure_ascii=False)[:120]})")
            result = dispatch_tool(tool_name, tool_args)
            # Show a preview
            preview = result[:300].replace("\n", " ")
            print(f"   → {preview}{'…' if len(result) > 300 else ''}\n")

            tool_result_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=tool_name,
                        response={"result": result}
                    )
                )
            )

        # Append tool results to history
        contents.append(types.Content(
            role="user",
            parts=tool_result_parts
        ))

    if iteration >= max_iterations:
        print(f"\n⚠  Reached max iterations ({max_iterations}). Agent stopped.")



# Entry point
def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit(
            "ERROR: GEMINI_API_KEY is not set.\n"
            "1. Copy .env.example to .env\n"
            "2. Add your key from https://aistudio.google.com/app/api-keys"
        )

    ensure_repo_cloned()
    run_agent(api_key)

    print(f"\n📄  Execution plan : {Path(__file__).parent / 'execution_plan.txt'}")
    print(f"📄  Changes summary: {Path(__file__).parent / 'changes_summary.txt'}")
    print(f"📁  Modified repo  : {WORKSPACE}\n")


if __name__ == "__main__":
    main()
