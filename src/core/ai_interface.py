from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Dict, List
import json
from src.core.history import QueryHistory

class AIInterface:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.history = QueryHistory()
        self.conversation_context = []
        self.current_scan_data = None

    def add_scan_context(self, file_data: List[Dict]):
        """Summarize scan results and store them as system context."""
        if not file_data:
            # Truncate for token safety
            top_files = sorted(file_data, key=lambda f: f['size'], reverse=True)[:10]
            top_exts = {}
            for f in file_data:
                ext = f.get("extension", "unknown")
                top_exts[ext] = top_exts.get(ext, 0) + f.get("size", 0)

            top_exts_str = "\n".join([f"{ext}: {size / 1e6:.2f} MB" for ext, size in sorted(top_exts.items(), key=lambda x: -x[1])[:5]])
            top_file_str = "\n".join([f"{f['path']} ({f['size'] / 1e6:.2f} MB)" for f in top_files])

            self.conversation_context = [{
                "role": "system",
                "content": f"""
            You are a smart storage assistant.
            Here's the current scan data:

            Top file extensions by total size:
            {top_exts_str}

            Top 10 largest files:
            {top_file_str}

            Only answer based on this scan data.
            """
            }]

            return

        self.current_scan_data = file_data
        total_size_bytes = sum(f.get("size", 0) for f in file_data)
        total_size_gb = total_size_bytes / (1024 ** 3)
        extensions = list({f.get("extension", "") for f in file_data if f.get("extension")})
        sample_paths = [f.get("path") for f in file_data[:3]]

        system_prompt = (
            "You are a helpful AI assistant that helps users manage files on their computer.\n"
            f"Scan Summary:\n"
            f"- Total files: {len(file_data)}\n"
            f"- Total size: {total_size_gb:.2f} GB\n"
            f"- Common extensions: {', '.join(extensions[:5]) or 'None'}\n"
            f"- Sample paths: {json.dumps(sample_paths, indent=2)}\n"
            "Provide helpful responses or actions based on this scan."
        )

        self.conversation_context = [{"role": "system", "content": system_prompt}]

    def chat_query(self, message: str) -> str:
        """Send a chat query with real-time scan data injected for deeper context."""
        try:
            # Fallback if no scan data available
            if not self.current_scan_data:
                fallback_context = [
                    {"role": "system", "content": "You are a filesystem assistant, but no scan data is currently available."},
                    {"role": "user", "content": message}
                ]
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=fallback_context,
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()

            # Process scan data for injection
            file_data = self.current_scan_data
            top_files = sorted(file_data, key=lambda f: f['size'], reverse=True)[:10]
            
            ext_summary = {}
            for f in file_data:
                ext = f.get("extension", "unknown")
                ext_summary[ext] = ext_summary.get(ext, 0) + f.get("size", 0)
            top_exts = sorted(ext_summary.items(), key=lambda x: -x[1])[:5]

            # Format for context
            extension_breakdown = "\n".join([f"- {ext}: {size / 1e6:.2f} MB" for ext, size in top_exts])
            file_breakdown = "\n".join([f"- {f['path']} ({f['size'] / 1e6:.2f} MB)" for f in top_files])

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a smart desktop file assistant. The following file scan has been loaded:\n\n"
                        f"📦 **Total files**: {len(file_data)}\n"
                        f"💾 **Top extensions by space**:\n{extension_breakdown}\n\n"
                        f"📁 **Top 10 largest files**:\n{file_breakdown}\n\n"
                        "Answer the user’s request using only the context above."
                    )
                },
                {"role": "user", "content": message}
            ]

            # Make the request
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.3
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"⚠️ Error during AI query: {str(e)}"

    def parse_query(self, query: str, file_data: List[Dict]) -> Dict:
        """Convert a natural language query into a structured file operation command."""
        try:
            context = {
                "file_count": len(file_data),
                "total_size_mb": sum(f["size"] for f in file_data) / (1024 * 1024),
                "extensions": list({f.get("extension", "") for f in file_data})
            }

            prompt = (
                f"You are a smart assistant that helps turn file-related questions into commands.\n"
                f"Context:\n"
                f"- Files: {context['file_count']}\n"
                f"- Total size: {context['total_size_mb']:.2f} MB\n"
                f"- Extensions: {', '.join(context['extensions'])}\n\n"
                f"Query: \"{query}\"\n"
                "Respond with a JSON object:\n"
                "{\n"
                "  \"action\": \"list|delete|find_duplicates|analyze_space\",\n"
                "  \"parameters\": { ... }\n"
                "}"
            )

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You turn user file queries into structured JSON commands."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )

            raw_content = response.choices[0].message.content.strip()
            command_json = json.loads(raw_content)
            return command_json

        except json.JSONDecodeError as je:
            return {
                "action": "error",
                "parameters": {
                    "message": f"Invalid JSON response from model: {str(je)}"
                }
            }
        except Exception as e:
            return {
                "action": "error",
                "parameters": {
                    "message": str(e)
                }
            }
