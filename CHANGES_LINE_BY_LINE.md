# Line-by-line changelog for `parse_definition` updates

This document explains every modified line in `main.py` (commit e84fe18) compared to the previous revision, focusing on the `parse_definition` helper inside the `.sendmessages` command.

| Line(s) | Change | Explanation |
| --- | --- | --- |
| 150 | Added format comment | Documents the expected argument layout so readers immediately understand the parsing contract. |
| 151-154 | New guard for missing commas | Prevents inputs without any comma separators from slipping through, ensuring the user sees the standard usage hint. |
| 156 | Split only once | Captures the task name before the triple-quoted message without being confused by commas in the message body. |
| 157 | Name normalization tweak | Trims surrounding whitespace and stray quotes to match prior behavior. |
| 158 | Left-strip remainder | Removes space before checking for the opening triple quotes. |
| 160-161 | Triple-quote start validation | Fails early with the scheduler-specific error when the message is not wrapped in `"""`. |
| 163-165 | Search for closing triple quotes | Scans for the next `"""` after the opener instead of assuming commas will delimit the message, allowing commas/newlines in the body. |
| 167 | Slice out message | Extracts the text between the triple quotes exactly as written by the user. |
| 168 | Trim following whitespace | Prepares the remainder string for parsing the channel/delay section. |
| 170-174 | Require comma after message | Confirms the message block is followed by a comma and shows the standard usage hint when formatting is wrong. |
| 176 | Skip leading comma | Drops the delimiter before splitting the channel and delay pieces. |
| 177 | Split remaining args once | Allows the delay portion to contain commas (e.g., in future extensions) by limiting the split to one occurrence. |
| 178-181 | Validate split count | Reuses the friendly usage message when the parser cannot find both channel and delay values. |
| 183 | Assign `channel_token`/`delay_token` | Names parts explicitly instead of indexing a list. |
| 184-185 | Channel mention handling | Keeps support for `<#channel>` syntax exactly as before. |
| 187 | Convert delay token | Casts the parsed delay string to a float after the new splitting logic. |
| 189-194 | Return `ScheduledTask` | Unchanged structurally, but now populated with the safely extracted tokens. |

With these adjustments, `.sendmessages` now accepts multi-line messages that contain commas, currency symbols, and URLs without breaking the parser.
