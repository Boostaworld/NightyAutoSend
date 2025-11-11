# Line-by-line explanation of `main.py` updates (commit 4f8f9c2 vs c392bf2)

This document walks through every line of the rewritten `main.py`, explaining how it differs from the previous version and why each change was made.

## Decorator and function signature (lines 1-8)
- **1** `@nightyScript(` — unchanged decorator, shown for context.
- **2-4** `name`, `author`, `description` remain the same as the prior script.
- **5** `usage=".sendmessages <name>, triple_quoted_message, <channel>, <delay_seconds>"` updates the placeholder to accept either a channel mention or raw ID, reflecting the new parsing logic that strips `<#...>`.
- **6** closing the decorator call, unchanged.
- **7** `def send_message_script():` still defines the Nighty entry point; kept to anchor following changes.
- **8** Docstring replaced with a concise summary instead of the previous multi-line help block, because the detailed help now lives in runtime messages.

## Local imports (lines 10-13)
- **10** `import asyncio` remains; still needed for scheduling tasks.
- **11** blank line for readability.
- **12-13** `from dataclasses import dataclass` and `from typing import Dict, Optional` add structured typing support introduced in this rewrite.

## Data model definitions (lines 15-54)
- **15-17** Section comment `# ---------------------------------------------------------------------` to visually separate helpers.
- **18-24** `@dataclass class ScheduledTask` replaces the old tuple-like returns, bundling task properties into a typed object.
- **25-31** `to_config` method serializes `ScheduledTask` into the shape stored in config, replacing inline dict creation in the old code.
- **33-39** `class TaskManager` introduced to encapsulate persistence and running task handling; replaces scattered dictionaries.
- **34-36** `__init__` stores runtime tasks and loads persisted tasks once on startup.
- **38-52** `_load_tasks` loads saved data from Nighty config, casting values safely and skipping malformed entries (previous version blindly trusted data).
- **54-58** `save` centralizes writing back to config, replacing repeated `updateConfigData` calls.

## Runtime helpers (lines 60-96)
- **60-67** `start` method now owns launching send loops, replacing the free function `send_loop`; it validates channel access and restarts tasks if renamed duplicates existed in memory.
- **69-78** Nested `send_loop` coroutine keeps retrying and logs errors to stdout instead of using `print(..., type_="ERROR")` (not supported); ensures consistent delay handling.
- **80-87** Cancels existing running task with the same name, registers the new task, caches metadata, and persists it.
- **89-99** `stop`, `get`, and `list` methods consolidate logic for removing tasks and querying their state, replacing scattered dictionary operations.

## Manager instance and icon constants (lines 101-109)
- **101** Instantiates a single `TaskManager` for use across commands instead of reloading config every time.
- **103-109** Define emoji constants for consistent messaging (replaces raw emoji literals sprinkled through previous responses).

## Message building utility (lines 111-140)
- **111-123** `build_message` helper composes Markdown-friendly responses with optional body, highlight table, and footer. This supersedes repeated string concatenations.
- **125-134** Loops through highlight entries, formatting single-line values inline and multi-line values as blockquotes for readability.
- **136-139** Appends footer guidance (defaults to pointing users to `.sendmessages help`).

## Delay formatting helper (lines 142-150)
- **142-150** `format_delay` converts seconds into human-readable units (seconds/minutes/hours), replacing the raw `X s` output in previous code.

## Parser (lines 152-175)
- **152-154** `parse_definition` keeps the comma split but now limits to 4 parts with `split(",", 3)`; ensures message field may include commas inside triple quotes.
- **156-158** Raises a formatted error message that mirrors the decorator usage.
- **160-166** Extracts and cleans each argument; triple quotes are enforced just like before, but stored as `message`.
- **168-170** Accepts `<#channel>` mentions by removing wrappers before converting to int.
- **172** Casts delay with `float(parts[3])` (previous code used `.strip()` but `split` already trimmed; we rely on later validation).
- **174-175** Returns a `ScheduledTask` instance instead of tuple, aligning with the new TaskManager.

## Help message builder (lines 177-191)
- **177-183** `help_message` collects each command string (including the new `.taskinfo`).
- **184-191** Returns the formatted help message using `build_message` with a "Commands" highlight block; replaces static docstring instructions.

## Command registration (lines 195 onward)

### `.sendmessages` command (lines 195-250)
- **195-199** Decorator remains but description unchanged.
- **200** Deletes invoking message (same behavior).
- **202-204** Adds inline help trigger when users pass `help` or `?`, returning the formatted help message.
- **206-214** Parses arguments into `ScheduledTask`; checks manager for existing task by name instead of fetching raw config.
- **215-224** If task exists, builds a warning message showing the current channel/delay (with highlights) rather than plain text.
- **226** Starts the task via `manager.start`, which handles config updates and cancellation.
- **228-235** Previews the message content with Markdown code block (up to 150 chars) and reports channel/interval using the helper; this replaces the single-line success message.
- **237-244** On errors, sends formatted error message with icon and message body instead of raw `⚠️ Error: ...` string.

### `.stoptask` command (lines 246-272)
- **246-248** Same decorator, deletes triggering message.
- **250-256** Validates name presence, using helper to show proper usage on failure.
- **258-267** Calls `manager.stop` which cancels runtime task and updates config; success path uses consistent messaging and icons.
- **268-272** Not-found branch also uses helper with warning styling.

### `.listtasks` command (lines 274-296)
- **274-276** Same decorator, message deletion.
- **278-282** Retrieves tasks from manager; no manual config fetch.
- **284-287** If none, send info message using helper.
- **289-293** Builds Markdown bullet list summarizing each task with formatted delay and channel mention.
- **295-296** Sends aggregated message with default footer.

### `.taskinfo` command (lines 298-330)
- **298-301** New command decorator and message deletion.
- **303-309** Validates name input and returns usage hint via helper when missing.
- **311-317** Fetches task from manager; returns warning message if not found.
- **319-329** Formats stored message contents inside code fences along with channel/interval details, enabling users to inspect what will be sent.
- **330** Sends the response with longer expiration (`delete_after=30`).

## Script registration (lines 334-335)
- **334** blank line for clarity.
- **335** `send_message_script()` call remains; required to register commands with Nighty.

