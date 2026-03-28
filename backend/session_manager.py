import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class Message:
    """Represents a single message in a conversation"""
    role: str     # "user" or "assistant"
    content: str  # The message content

class SessionManager:
    """Manages conversation sessions and message history"""

    def __init__(self, max_history: int = 5, persist_path: str = "sessions.json"):
        self.max_history = max_history
        self.persist_path = persist_path
        self._sessions: Dict[str, dict] = {}
        self.session_counter = 0
        self._load()

    def create_session(self) -> str:
        """Create a new conversation session"""
        self.session_counter += 1
        session_id = f"session_{self.session_counter}"
        self._sessions[session_id] = {
            "title": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "messages": []
        }
        self._save()
        return session_id

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the conversation history"""
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "title": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "messages": []
            }

        message = Message(role=role, content=content)
        self._sessions[session_id]["messages"].append(message)

        # Keep conversation history within limits
        messages = self._sessions[session_id]["messages"]
        if len(messages) > self.max_history * 2:
            self._sessions[session_id]["messages"] = messages[-self.max_history * 2:]

    def add_exchange(self, session_id: str, user_message: str, assistant_message: str):
        """Add a complete question-answer exchange"""
        self.add_message(session_id, "user", user_message)
        self.add_message(session_id, "assistant", assistant_message)

        # Set title from first user message
        if session_id in self._sessions and not self._sessions[session_id]["title"]:
            self._sessions[session_id]["title"] = user_message[:50]

        self._save()

    def get_conversation_history(self, session_id: Optional[str]) -> Optional[str]:
        """Get formatted conversation history for a session"""
        if not session_id or session_id not in self._sessions:
            return None

        messages = self._sessions[session_id]["messages"]
        if not messages:
            return None

        # Format messages for context
        formatted_messages = []
        for msg in messages:
            formatted_messages.append(f"{msg.role.title()}: {msg.content}")

        return "\n".join(formatted_messages)

    def clear_session(self, session_id: str):
        """Clear all messages from a session"""
        if session_id in self._sessions:
            self._sessions[session_id]["messages"] = []
            self._save()

    def get_all_sessions(self) -> List[dict]:
        """Return metadata for the last 10 sessions that have messages"""
        result = []
        for session_id, data in self._sessions.items():
            if data["messages"]:
                result.append({
                    "session_id": session_id,
                    "title": data["title"] or "Untitled",
                    "created_at": data["created_at"],
                    "message_count": len(data["messages"])
                })
        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result[:10]

    def get_session_messages(self, session_id: str) -> Optional[List[dict]]:
        """Return all messages for a session as dicts, or None if not found"""
        if session_id not in self._sessions:
            return None
        return [
            {"role": m.role, "content": m.content}
            for m in self._sessions[session_id]["messages"]
        ]

    def _save(self):
        """Persist sessions to disk"""
        data = {
            "session_counter": self.session_counter,
            "sessions": {
                sid: {
                    "title": d["title"],
                    "created_at": d["created_at"],
                    "messages": [{"role": m.role, "content": m.content} for m in d["messages"]]
                }
                for sid, d in self._sessions.items()
            }
        }
        with open(self.persist_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        """Load sessions from disk if the file exists"""
        if not os.path.exists(self.persist_path):
            return
        try:
            with open(self.persist_path, "r") as f:
                data = json.load(f)
            self.session_counter = data.get("session_counter", 0)
            for sid, d in data.get("sessions", {}).items():
                self._sessions[sid] = {
                    "title": d.get("title", ""),
                    "created_at": d.get("created_at", ""),
                    "messages": [Message(**m) for m in d.get("messages", [])]
                }
        except Exception as e:
            print(f"Warning: could not load sessions from {self.persist_path}: {e}")
