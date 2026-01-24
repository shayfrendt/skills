# Hooks

Claude Code hooks that add safety guardrails and automation.

## gmail-guard.py

A safety hook that blocks Gmail send and delete operations, requiring explicit user approval.

### What it does

- **ALLOWS**: Reading emails, creating drafts, listing labels (safe, reversible operations)
- **BLOCKS**: Sending emails, deleting emails, trashing threads (requires explicit approval)

When a dangerous operation is attempted, Claude Code will show a permission dialog that you must explicitly approve.

### Blocked operations

- `GMAIL_SEND_EMAIL`
- `GMAIL_CREATE_DRAFT_AND_SEND`
- `GMAIL_REPLY_TO_EMAIL`
- `GMAIL_REPLY_TO_THREAD`
- `GMAIL_DELETE_EMAIL`
- `GMAIL_TRASH_EMAIL`
- `GMAIL_DELETE_THREAD`
- `GMAIL_TRASH_THREAD`
- `GMAIL_MARK_AS_SPAM`

### Installation

1. Copy `gmail-guard.py` to `.claude/hooks/` in your project
2. Add the hook configuration to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__rube__RUBE_MULTI_EXECUTE_TOOL",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/gmail-guard.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

### Why use this?

This hook enforces the principle: **drafting is safe, sending requires confirmation**.

It's particularly useful when:
- Using Gmail through MCP integrations (like Composio/Rube)
- You want Claude to help draft emails but never send without explicit approval
- You want an extra layer of protection against accidental email sends or deletions
