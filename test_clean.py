content = "```json\n{\n  \"test\": \"hello\"\n}\n```"
content = content.strip()
if content.startswith("```"):
    lines = content.split("\n")
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    content = "\n".join(lines)
print("Cleaned:", repr(content))
import json
parsed = json.loads(content)
print("Parsed:", parsed)