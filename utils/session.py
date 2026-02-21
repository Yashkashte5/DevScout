class SessionMemory:
    """Simple in-memory session state — ADK handles agent context, this handles app-level state."""

    def __init__(self):
        self.last_query: str = ""
        self.last_intent: dict = {}
        self.last_results: list = []
        self.last_raw_data: dict = {}
        self.user_preferences: dict = {
            "prioritize": "balanced"
        }
        self.feedback_history: list = []

    def update_query(self, query: str, intent: dict):
        self.last_query = query
        self.last_intent = intent

    def update_results(self, results: list, raw_data: dict):
        self.last_results = results
        self.last_raw_data = raw_data

    def add_feedback(self, item_name: str, feedback: str):
        """feedback is 'up' or 'down'"""
        self.feedback_history.append({
            "item": item_name,
            "feedback": feedback
        })
        # Adjust preferences based on feedback pattern
        downs = [f for f in self.feedback_history if f["feedback"] == "down"]
        ups = [f for f in self.feedback_history if f["feedback"] == "up"]

        if len(downs) > len(ups):
            self.user_preferences["prioritize"] = "recency"
        elif len(ups) > len(downs):
            self.user_preferences["prioritize"] = "popularity"

    def get_top_two(self) -> list:
        """Return top two results for comparison."""
        return self.last_results[:2] if len(self.last_results) >= 2 else self.last_results

    def is_comparison_request(self, query: str) -> bool:
        """Detect if user is asking to compare previous results."""
        keywords = ["compare", "difference", "vs", "versus", "which one", "top two", "both"]
        return any(k in query.lower() for k in keywords)

    def has_previous_results(self) -> bool:
        return len(self.last_results) > 0

    def clear(self):
        self.__init__()


# Single session instance — one user at a time for this demo
session = SessionMemory()