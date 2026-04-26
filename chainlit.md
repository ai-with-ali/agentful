# Data Analysis Agent

Welcome to the **Data Analysis Agent** — a conversational assistant powered by a local LLM and connected to specialised analysis tools via MCP.

## What can I do?

| Capability | Example |
|---|---|
| Arithmetic | *"What is 123.45 + 678.9?"* |
| Multiplication | *"Multiply 42 by 7."* |
| Multi-step reasoning | *"Add 10 and 20, then multiply the result by 3."* |

## How it works

Each chat session creates a **dedicated thread** — your conversation history is preserved throughout the session, so the agent remembers earlier messages and can build on them.

Starting a new session resets the thread, giving you a clean slate.

## Tips

- Be specific with numbers and operations.
- You can chain multiple operations in a single message.
- If the agent cannot perform an action, it will tell you clearly rather than guessing.
