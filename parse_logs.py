import json
import os
import sys

transcript_path = r"C:\Users\Admin\.gemini\antigravity\brain\59870d68-babf-46e7-8f2e-29e7b94ebf86\.system_generated\logs\transcript.jsonl"
output_path = r"e:\videosskills\edit_history.json"

edits = []

try:
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                step = json.loads(line)
                tool_calls = step.get('tool_calls', [])
                if not tool_calls:
                    continue
                for call in tool_calls:
                    name = call.get('name')
                    if name in ['replace_file_content', 'multi_replace_file_content', 'write_to_file']:
                        edits.append({
                            'step_index': step.get('step_index'),
                            'tool': name,
                            'arguments': call.get('arguments'),
                        })
            except Exception as line_err:
                pass
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(edits, f, indent=2)
except Exception as e:
    # write error to output file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"Error: {str(e)}")
