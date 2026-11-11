"""Tool 基础接口(Level 0)。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from tools.protocol import ToolDefinition


class Tool(ABC):
    """白名单工具的最小契约:一份定义,一个同步 execute。

    execute 只允许返回输出字符串或抛 ToolExecutionFailure;
    任何其他异常由 Dispatcher 统一捕获并转为结构化错误,不向模型外泄堆栈。
    """

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition: ...

    @abstractmethod
    def execute(self, arguments: dict) -> str: ...
