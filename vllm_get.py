from openai import OpenAI
import sys

BASE_URL = "http://222.95.84.214:30003/v1"
API_KEY = "ds-v3.2"
MODEL_NAME = "Deepseek-V3.2"

# 初始化客户端
client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

# ================= 对话逻辑 =================
print("输入 'exit' 或 'quit' 结束对话。")
print("=" * 60)

# 初始化历史记录，保留上下文记忆
chat_history = [
    {"role": "system", "content": "你是一个聪明、严谨的 AI 助手。请在给出最终答案前，先进行充分的逻辑推导。"}
]

EXTRA_BODY = {
    "chat_template_kwargs": {"thinking": True}
}

while True:
    try:
        user_input = input("\n\033[1;32m用户:\033[0m ")

        if user_input.strip().lower() in ['exit', 'quit']:
            print("结束对话，再见！")
            break

        if not user_input.strip():
            continue

        # 将用户输入加入历史
        chat_history.append({"role": "user", "content": user_input})

        # 发起流式请求
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=chat_history,
            temperature=0.6,
            max_tokens=4096,
            stream=True,
            stream_options={"include_usage": True},
            extra_body=EXTRA_BODY
        )

        print("\n\033[1;36m模型思考中:\033[0m\n\033[90m", end="")

        full_assistant_reply = ""
        is_thinking_done = False

        # 遍历流式返回的数据块
        for chunk in response:
            if hasattr(chunk, 'usage') and chunk.usage is not None:
                print("\n\n\033[1;33m[Token 消耗统计]\033[0m")
                print(f"提示词 (Prompt): {chunk.usage.prompt_tokens} tokens")
                print(f"生成 (Completion): {chunk.usage.completion_tokens} tokens")
                print(f"总计 (Total): {chunk.usage.total_tokens} tokens")
                continue

            # 正常处理包含文本的 chunk
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta

                # 1. 提取官方标准的思考过程
                reasoning = getattr(delta, 'reasoning', None)
                if reasoning:
                    print(reasoning, end="", flush=True)

                # 2. 提取正式回复内容
                content = getattr(delta, 'content', None)
                if content:
                    # 第一次遇到正式内容，说明思考结束，切换终端颜色
                    if not is_thinking_done:
                        print("\033[0m")  # 恢复默认颜色
                        print("\n\033[1;36m最终回复:\033[0m ", end="")
                        is_thinking_done = True

                    print(content, end="", flush=True)
                    full_assistant_reply += content

        print("\n" + "-" * 60)

        # 将纯净的最终回复（不含思考过程）追加到上下文，避免历史记录过度膨胀
        chat_history.append({"role": "assistant", "content": full_assistant_reply})

    # 优雅退出处理（Ctrl+C）
    except KeyboardInterrupt:
        print("\n检测到中断信号，退出程序。")
        break
    except Exception as e:
        print(f"\n[错误] API 请求异常: {e}")