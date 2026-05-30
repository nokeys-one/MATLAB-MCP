from typing import Any, Callable


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}

    def register(self, name: str, description: str, input_schema: dict):
        def decorator(func: Callable):
            self._tools[name] = {
                "name": name,
                "description": description,
                "input_schema": input_schema,
                "handler": func,
            }
            return func
        return decorator

    def get_all(self) -> dict[str, dict[str, Any]]:
        return dict(self._tools)

    def get_handler(self, name: str) -> Callable | None:
        tool = self._tools.get(name)
        return tool["handler"] if tool else None

    def get_tool(self, name: str) -> dict[str, Any] | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def clear(self):
        self._tools.clear()


registry = ToolRegistry()
