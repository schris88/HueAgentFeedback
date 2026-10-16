Use the hue-task MCP tools for these notifications:
- Immediately before the final answer for a successfully completed task, call task_done once (two gentle blue color blends).
- Immediately before asking a question that needs my reply, call needs_input once (two gentle red color blends).
- Do not blink for progress updates, rhetorical questions, or intermediate subtasks.
- If the light tool fails, continue the conversation and briefly report that the notification failed. Do not repeatedly retry or let a light failure prevent asking an important question.

This is agent behavior guidance. MCP provides tools, not automatic access to every client lifecycle event. Approval dialogs displayed by the client before a tool runs may not be visible to the agent. Guaranteed lifecycle notifications require client-specific hooks.
