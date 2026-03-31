"""命令行入口。"""

from __future__ import annotations

import argparse
import sys

from chat_app.chat import ChatSession
from chat_app.config import load_config


def build_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="最小 LangChain 对话示例（system prompt 默认从文件读取）"
    )
    parser.add_argument(
        "--message",
        type=str,
        help="单轮对话内容；不传时进入交互模式。",
    )
    return parser


def configure_console_encoding() -> None:
    """尽量确保 Windows 终端按 UTF-8 输出。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def run_interactive_chat() -> int:
    """运行简单的交互式对话。"""
    session = ChatSession(load_config())
    print("已连接到模型，输入内容开始对话，输入 quit / exit 结束。")

    while True:
        user_input = input("你: ").strip()
        if user_input.lower() in {"quit", "exit"}:
            print("已退出。")
            return 0

        if not user_input:
            print("请输入有效内容。")
            continue

        answer = session.ask(user_input)
        print(f"助手: {answer}")


def main() -> int:
    """程序主入口。"""
    configure_console_encoding()
    parser = build_parser()
    args = parser.parse_args()
    session = ChatSession(load_config())

    if args.message:
        print(session.ask(args.message))
        return 0

    return run_interactive_chat()


if __name__ == "__main__":
    raise SystemExit(main())
