parse_definition now locates the triple-quoted message by searching for the closing """ marker, so commas, newlines, and symbols inside the body no longer break `.sendmessages`.
After slicing out the message block, the parser trims the remainder, enforces the trailing comma, and splits out channel and delay tokens before normalizing channel mentions and converting the delay to a float.
