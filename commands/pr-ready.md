---
name: pr-ready
user_invocable: true
description: Check if a PR is ready to merge by verifying CI checks pass, review comments are resolved, and there are no outstanding requests for changes. Use when the user asks "is this PR ready?", "check PR status", "is this mergeable?", or "pr-ready". Can also resolve addressed threads with commit citations.
version: 2.1.0
---

# PR Readiness Check

Determine if a pull request is ready to merge by checking CI status, review comments, and review approvals. Optionally resolve addressed threads with commit citations.

## Phase 1: Gather Data

1. **Determine the PR.** If the user provides a PR number or URL, use that. Otherwise, detect the current branch and find its open PR via `gh pr view --json number,headRefName,url`.

2. **Gather data in parallel** using `gh` commands:

   ```bash
   # CI checks
   gh pr checks <number>

   # Review status (approvals, requests for changes)
   gh pr view <number> --json reviews,reviewRequests

   # Unresolved review threads (with thread IDs for later resolution)
   gh api graphql -f query='
     query($owner:String!, $repo:String!, $number:Int!) {
       repository(owner:$owner, name:$repo) {
         pullRequest(number:$number) {
           reviewThreads(first:100) {
             nodes {
               id
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

## Phase 2: Analyze and Report

Gather data for four areas: merge conflicts, CI checks, reviews, and unresolved threads. Then present the results as a **summary grid** followed by a verdict.

### Data gathering

- **Merge Conflicts**: `gh pr view <number> --json mergeable,mergeStateStatus --jq '{mergeable, mergeStateStatus}'`
  - `"CONFLICTING"` = blocker. `"UNKNOWN"` = note GitHub is still computing.
  - Offer to resolve conflicts if the user asks.
- **CI Checks**: `gh pr checks <number>` — note any failing or pending.
- **Reviews**: Note CHANGES_REQUESTED without a follow-up APPROVED. Note pending review requests. Check repo rules for whether approvals are required.
- **Unresolved Threads**: Count unresolved, non-outdated threads. If any exist, list each with file path, line, author, and one-line summary. Categorize as actionable / question / informational.

### Output format

Always present the readout as a grid, then verdict:

```
## PR #NNNN Readiness Check

| Area | Status | Detail |
|------|--------|--------|
| Merge Conflicts | ✅ or ❌ | Detail |
| CI Checks | ✅ or ❌ | Detail |
| Reviews | ✅ or ❌ | Detail |
| Unresolved Threads | ✅ or ❌ | N / M unresolved |

### Verdict: **Ready** or **Not ready** — list blockers if not ready.
```

Use ✅ when the area is clear / passing. Use ❌ when there's a blocker or failure.

If there are unresolved threads, expand them in a separate table below the grid with file, line, author, and summary.

**After the verdict**, if there are unresolved threads that appear addressed by recent commits, ask: "Some of these threads appear to be addressed by recent commits. Would you like me to verify and resolve them with commit citations?"

Do NOT resolve threads without the user's explicit approval.

## Phase 3: Resolve Addressed Threads (when user approves)

### 3a. Deep Verification — The Most Important Step

For EVERY thread you intend to resolve, you must **prove to yourself** that the concern is genuinely addressed. Lip service is worse than leaving a thread open.

For each thread:

1. **Read the full review comment** — understand the *specific* concern, not just the headline. A comment titled "this shouldn't throw" might actually be about error handling strategy, not just removing a throw statement.

2. **Read the current code** at the file/line referenced. Use `Read` tool on the actual file. Don't assume — verify.

3. **Reason through the fix**: Write down (internally) WHY the current code addresses the concern. If you can't articulate a specific reason with a specific line of code, you haven't verified it.

4. **Find the fixing commit and the exact line(s)**:
   ```bash
   # Find which commit last touched the relevant file/area
   git log --oneline -- <file>
   # Or search for a specific change
   git log --oneline -S "functionName"
   ```

5. **Build a GitHub permalink** to the specific line(s) that resolve the concern:
   ```
   https://github.com/OWNER/REPO/blob/COMMIT_SHA/path/to/file.ts#L42
   https://github.com/OWNER/REPO/blob/COMMIT_SHA/path/to/file.ts#L42-L50
   ```

6. **If the fix is NOT present, is incomplete, or you're not confident**: do NOT resolve. Flag it to the user with your analysis of what's missing.

### 3b. Write Resolution Comments

Write a JSON file to `/tmp/pr-thread-resolutions.json` with all verified threads:

```json
[
  {
    "threadId": "PRRT_...",
    "body": "Fixed in abc1234 — description of what changed.\n\nhttps://github.com/owner/repo/blob/abc1234/path/to/file.ts#L42-L50\n\n_This comment was generated automatically._",
    "verified": true
  }
]
```

Rules for resolution comments:
- **Always cite the fixing commit SHA** (short hash) in the first line
- **Be specific** about what changed — not "fixed" but "replaced `new URL()` with `safeURL()` and added Zod validation on the redirect_uri field"
- **Always include a GitHub permalink** to the specific line(s) that resolve the concern. This is the proof. Use the format `https://github.com/OWNER/REPO/blob/COMMIT_SHA/path/to/file.ts#L42` or `#L42-L50` for ranges.
- **End with**: `_This comment was generated automatically._`
- For informational/positive threads (no action needed): use "Acknowledged. _This comment was generated automatically._"
- For threads where the approach differs from the suggestion: explain what was done instead and why, with a permalink to the chosen approach

### 3c. Execute Resolutions

Read the JSON file and resolve each thread. Use piped JSON to avoid shell quoting issues:

```bash
# Reply to thread
echo '{"query":"mutation($t:ID!,$b:String!){addPullRequestReviewThreadReply(input:{pullRequestReviewThreadId:$t,body:$b}){comment{id}}}","variables":{"t":"THREAD_ID","b":"COMMENT_BODY"}}' | gh api graphql --input -

# Resolve thread
echo '{"query":"mutation($t:ID!){resolveReviewThread(input:{threadId:$t}){thread{isResolved}}}","variables":{"t":"THREAD_ID"}}' | gh api graphql --input -
```

**Important API notes:**
- Always pipe JSON via `echo '...' | gh api graphql --input -` — never use `-f` flags for the comment body, as special characters break shell parsing
- Execute one thread at a time (not chained with `&&` or `;`) to avoid cascading failures on network hiccups
- If a call fails with a network error, wait a moment and retry once
- After all resolutions, verify with a count query that 0 unresolved threads remain:
  ```bash
  gh api graphql -f query='...' --jq '[... | select(.isResolved == false and .isOutdated == false)] | length'
  ```

## Important

- Do NOT resolve threads without the user's explicit approval.
- Keep output concise — summarize, don't dump raw JSON.
- If there are unresolved threads with actionable code feedback, ask the user if they'd like you to address them.
- **Never dismiss a review comment without verifying the fix in the actual code.** Read the file. Find the line. Build the permalink. If you can't point to a specific line that resolves the concern, the thread isn't resolved.
