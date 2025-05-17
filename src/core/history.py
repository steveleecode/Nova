from typing import List, Dict, Optional
from datetime import datetime
import json

class QueryHistory:
    def __init__(self):
        self.history: List[Dict] = []

    def log_query(
        self,
        query: str,
        action: str,
        parameters: Dict,
        results: List[Dict]
    ) -> None:
        """Log a query and its results to history."""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "action": action,
            "parameters": parameters,
            "results": results
        })

    def get_recent(self, n: int = 3) -> List[Dict]:
        """Get the last `n` queries (default: 3)."""
        return self.history[-n:]

    def clear(self) -> None:
        """Clear the history."""
        self.history.clear() 