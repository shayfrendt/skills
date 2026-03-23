---
name: pr-ready
user_invocable: true
description: Check if a PR is ready to merge by verifying CI checks pass, review comments are resolved, and there are no outstanding requests for changes. Use when the user asks "is this PR ready?", "check PR status", "is this mergeable?", or "pr-ready".
version: 1.0.0
---

# PR Readiness Check

Determine if a pull request is ready to merge by checking three things: CI status, review comments, and review approvals.

## Instructions

1. **Determine the PR.** If the user provides a PR number or URL, use that. Otherwise, detect the current branch and find its open PR via `gh pr view --json number,headRefName,url`.

2. **Gather data in parallel** using `gh` commands:

   ```bash
   # CI checks
   gh pr checks <number>

   # Review status (approvals, requests for changes)
   gh pr view <number> --json reviews,reviewRequests

   # Unresolved review threads
   gh api graphql -f query='
     query($owner:String!, $repo:String!, $number:Int!) {
       repository(owner:$owner, name:$repo) {
         pullRequest(number:$number) {
           reviewThreads(first:100) {
             nodes {
               isResolved
               isOutdated
               comments(first:1) {
                 nodes {
                   body
                   author { login }
                   path
                   line
                 }
               }
             }
           }
         }
       }
     }
   ' -f owner=OWNER -f repo=REPO -F number=NUMBER
   ```

   Extract the owner/repo from `gh repo view --json owner,name`.

3. **Analyze and report** with three sections:

   ### Checks
   - List any failing or pending checks. If all pass, say so briefly.

   ### Reviews
   - Note any "CHANGES_REQUESTED" reviews that haven't been followed by an "APPROVED" from the same reviewer.
   - Note any pending review requests (people who haven't reviewed yet).

   ### Unresolved Threads
   - List each unresolved, non-outdated review thread with: file path, line number, author, and a one-line summary of the comment.
   - If a thread looks like something you can fix (e.g., a specific code change request), offer to fix it.

4. **Verdict**: End with a clear **Ready** / **Not ready** verdict and list the blockers if not ready.

## Important
- Do NOT attempt to fix anything automatically unless the user asks.
- Keep output concise — summarize, don't dump raw JSON.
- If there are unresolved threads with actionable code feedback, ask the user if they'd like you to address them.
