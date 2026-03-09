#!/bin/bash
# Hook: Block Read/Edit/Write access to .env files
# Note: The FRED skill accesses .env via its Bash script (fred_fetch.sh),
# which is not intercepted by this hook. Only Claude's Read/Edit/Write tools are blocked.
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ "$FILE_PATH" == *.env* ]]; then
  echo "Blocked: .env files are protected. API keys must not be read or modified." >&2
  exit 2
fi

exit 0
