import pytest
from matlab_mcp_server.tools.registry import ToolRegistry


def test_register_and_list():
    reg = ToolRegistry()

    @reg.register("test_tool", "A test tool", {"type": "object", "properties": {}})
    async def handler(params):
        return "ok"

    assert "test_tool" in reg.list_names()
    assert reg.get_handler("test_tool") is handler


def test_get_handler_unknown():
    reg = ToolRegistry()
    assert reg.get_handler("nonexistent") is None


def test_register_multiple():
    reg = ToolRegistry()

    @reg.register("tool_a", "Tool A", {"type": "object", "properties": {}})
    async def handler_a(params):
        return "a"

    @reg.register("tool_b", "Tool B", {"type": "object", "properties": {}})
    async def handler_b(params):
        return "b"

    assert set(reg.list_names()) == {"tool_a", "tool_b"}
    assert reg.get_handler("tool_a") is handler_a
    assert reg.get_handler("tool_b") is handler_b


def test_get_all():
    reg = ToolRegistry()

    @reg.register("my_tool", "Desc", {"type": "object", "properties": {}})
    async def handler(params):
        return "ok"

    all_tools = reg.get_all()
    assert "my_tool" in all_tools
    assert all_tools["my_tool"]["name"] == "my_tool"
    assert all_tools["my_tool"]["description"] == "Desc"
    assert all_tools["my_tool"]["handler"] is handler


def test_get_tool():
    reg = ToolRegistry()

    @reg.register("x", "X tool", {"type": "object", "properties": {"a": {"type": "string"}}})
    async def handler(params):
        return "x"

    tool = reg.get_tool("x")
    assert tool is not None
    assert tool["input_schema"]["properties"]["a"]["type"] == "string"


def test_get_tool_unknown():
    reg = ToolRegistry()
    assert reg.get_tool("nonexistent") is None


def test_clear():
    reg = ToolRegistry()

    @reg.register("t1", "T1", {"type": "object", "properties": {}})
    async def h(params):
        return "ok"

    assert len(reg.list_names()) == 1
    reg.clear()
    assert len(reg.list_names()) == 0


def test_list_names_empty():
    reg = ToolRegistry()
    assert reg.list_names() == []


def test_overwrite_same_name():
    reg = ToolRegistry()

    @reg.register("dup", "V1", {"type": "object", "properties": {}})
    async def handler_v1(params):
        return "v1"

    @reg.register("dup", "V2", {"type": "object", "properties": {}})
    async def handler_v2(params):
        return "v2"

    assert len(reg.list_names()) == 1
    assert reg.get_handler("dup") is handler_v2
    assert reg.get_tool("dup")["description"] == "V2"
