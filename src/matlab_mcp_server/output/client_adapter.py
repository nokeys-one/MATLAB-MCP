class ClientAdapter:
    def __init__(self, client_vision: bool = True, context_limit: int = 200000):
        self.client_vision = client_vision
        self.context_limit = context_limit

    def get_capabilities(self) -> dict:
        return {
            "client_vision": self.client_vision,
            "context_limit": self.context_limit,
        }

    def truncate_output(self, output: str, max_length: int | None = None) -> str:
        limit = max_length or self.context_limit
        if len(output) <= limit:
            return output
        return output[:limit] + f"\n... (truncated, {len(output) - limit} chars omitted)"
