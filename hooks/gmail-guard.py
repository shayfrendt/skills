#!/usr/bin/env python3
"""
Gmail Guard Hook - BLOCKS all Gmail send/delete operations.

This hook enforces a critical safety rule:
- Drafting emails: ALLOWED (safe, reversible)
- Sending emails: BLOCKED (requires explicit user approval via Claude Code prompt)
- Deleting emails: BLOCKED (requires explicit user approval via Claude Code prompt)

This is a systemic safeguard. The hook returns "ask" which forces Claude Code
to show a permission dialog that the user must explicitly approve.
"""
import json
import sys

# Tools that are DANGEROUS and require explicit approval
# These are the actual MCP tool names from the Composio Gmail integration
DANGEROUS_OPERATIONS = {
    # Sending operations
    "GMAIL_SEND_EMAIL",
    "GMAIL_CREATE_DRAFT_AND_SEND",
    "GMAIL_REPLY_TO_EMAIL",
    "GMAIL_REPLY_TO_THREAD",

    # Delete operations
    "GMAIL_DELETE_EMAIL",
    "GMAIL_TRASH_EMAIL",
    "GMAIL_DELETE_THREAD",
    "GMAIL_TRASH_THREAD",

    # Other destructive operations
    "GMAIL_MARK_AS_SPAM",
}

# Tools that are SAFE (read-only or draft creation)
SAFE_OPERATIONS = {
    "GMAIL_FETCH_EMAILS",
    "GMAIL_LIST_THREADS",
    "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID",
    "GMAIL_FETCH_MESSAGE_BY_THREAD_ID",
    "GMAIL_CREATE_EMAIL_DRAFT",  # Creating a draft is safe
    "GMAIL_GET_DRAFT",
    "GMAIL_LIST_DRAFTS",
    "GMAIL_ADD_LABEL_TO_EMAIL",
    "GMAIL_MODIFY_THREAD_LABELS",
    "GMAIL_LIST_LABELS",
}

def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # If we can't parse input, fail open but log the error
        print(f"Gmail Guard: JSON parse error: {e}", file=sys.stderr)
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Check if this is a Gmail MCP tool
    # MCP tools come through as mcp__rube__RUBE_MULTI_EXECUTE_TOOL
    # with the actual Gmail tool in the payload

    # First check: direct Gmail tool call (in case of direct MCP)
    is_dangerous = False
    matched_tool = None

    for dangerous_tool in DANGEROUS_OPERATIONS:
        if dangerous_tool in tool_name:
            is_dangerous = True
            matched_tool = dangerous_tool
            break

    # Second check: RUBE_MULTI_EXECUTE_TOOL wrapping Gmail operations
    if "RUBE_MULTI_EXECUTE_TOOL" in tool_name:
        tools_list = tool_input.get("tools", [])
        for tool in tools_list:
            tool_slug = tool.get("tool_slug", "")
            for dangerous_tool in DANGEROUS_OPERATIONS:
                if dangerous_tool in tool_slug:
                    is_dangerous = True
                    matched_tool = tool_slug
                    break
            if is_dangerous:
                break

    if is_dangerous:
        # Build a clear message about what's being blocked
        recipient = ""
        subject = ""

        if "RUBE_MULTI_EXECUTE_TOOL" in tool_name:
            for tool in tool_input.get("tools", []):
                args = tool.get("arguments", {})
                recipient = args.get("to", args.get("recipient", ""))
                subject = args.get("subject", "")
                if recipient or subject:
                    break
        else:
            recipient = tool_input.get("to", tool_input.get("recipient", ""))
            subject = tool_input.get("subject", "")

        details = []
        if recipient:
            details.append(f"To: {recipient}")
        if subject:
            details.append(f"Subject: {subject}")
        detail_str = " | ".join(details) if details else "See details above"

        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": (
                    f"GMAIL SAFETY CHECK: {matched_tool}\n"
                    f"{detail_str}\n\n"
                    f"This operation requires your EXPLICIT approval.\n"
                    f"Drafting is safe. Sending/deleting requires confirmation."
                )
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Safe operation or non-Gmail tool - proceed without blocking
    sys.exit(0)

if __name__ == "__main__":
    main()
