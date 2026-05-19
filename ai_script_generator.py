# AI讲稿生成模块
"""
AI讲稿生成模块 - 调用硅基流动API生成每页讲稿
支持自动生成和手动编辑两种模式
"""

import requests
import os
from datetime import datetime
from config import SILICONFLOW_API_KEY, SILICONFLOW_API_URL, SCRIPT_DIR

def call_ai_api(messages):
    """
    调用硅基流动API

    参数:
        messages: 对话消息列表

    返回:
        str: AI响应内容
    """

    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "Qwen/Qwen3-8B",
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7
    }

    try:

        response = requests.post(
            SILICONFLOW_API_URL,
            headers=headers,
            json=data
        )

        response.raise_for_status()

        ai_response = response.json()

        return ai_response["choices"][0]["message"]["content"]

    except requests.exceptions.RequestException as e:

        print(f"API调用失败: {e}")
        return None

    except (KeyError, IndexError) as e:

        print(f"解析AI响应失败: {e}")
        return None

def backup_script(page_num, current_content):
    """
    备份旧版本讲稿
    """

    history_dir = os.path.join(
        SCRIPT_DIR,
        "history",
        f"page_{page_num}"
    )

    os.makedirs(history_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_file = os.path.join(
        history_dir,
        f"backup_{timestamp}.txt"
    )

    with open(backup_file, "w", encoding="utf-8") as f:
        f.write(current_content)

    print(f"已备份历史版本: {backup_file}")

def clean_ai_script(raw_text):
    """
    清理AI返回内容，提取纯讲稿
    """

    if not raw_text:
        return ""

    # 去除首尾空白
    raw_text = raw_text.strip()

    # 按行拆分
    lines = raw_text.split('\n')

    for line in lines:

        line = line.strip()

        # 跳过空行
        if not line:
            continue

        # 去掉常见前缀
        prefixes = [
            "修改后的讲稿：",
            "修改后的讲稿:",
            "好的，",
            "好的",
            "以下是"
        ]

        for prefix in prefixes:
            if line.startswith(prefix):
                line = line.replace(prefix, "").strip()

        # 去掉 “第3页：”
        if line.startswith("第") and "页" in line:

            try:
                line = line.split("：", 1)[1].strip()
            except:
                pass

        if line:
            return line[:70]

    return raw_text[:70]

def generate_ai_script(ppt_text, enable_interactive=True, image_descriptions=None):
    """
    AI生成讲稿

    参数:
        ppt_text: PPT文本内容
        enable_interactive: 是否启用交互模式
        image_descriptions: {page_num: "图片描述"}，可选
    """

    image_context = ""
    if image_descriptions:
        parts = ["\n各页PPT中的图片内容："]
        for pn in sorted(image_descriptions.keys()):
            parts.append(f"第{pn}页图片: {image_descriptions[pn]}")
        image_context = "\n".join(parts)

    prompt = f"""
你是一位专业老师。

请根据以下PPT内容，
为每一页生成课堂讲稿。
{image_context}

PPT内容：
{ppt_text}

要求：
1. 每页生成一句真实讲稿，每页不超过70字。
2. 语言自然，适合课堂讲解。
3. 对于提供了“图片内容”的页面，必须将图片描述自然地融入到讲稿中。例如：如果图片描述是“一只白猫”，可以写成“图中展示了一只白猫……”或“我们看到的是一只白猫……”。
4. 不要输出“讲稿内容”“示例”等占位词。
5. 严格按照下面格式输出：

第1页：这里填写真实讲稿
第2页：这里填写真实讲稿
第3页：这里填写真实讲稿

不要添加任何解释。
"""
    print("正在调用AI生成讲稿...")

    messages = [
        {
            "role": "system",
            "content": "你是一位专业教师，负责生成课堂讲稿。"
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    script_content = call_ai_api(messages)

    if script_content is None:
        print("AI讲稿生成失败")
        return False

    if not validate_and_extract_script(script_content):
        print("AI返回格式错误")
        return False

    print("\n✅ AI讲稿生成完成！")

    # 启用交互编辑
    if enable_interactive:
        interactive_edit()

    return True


def interactive_edit():
    """
    交互式编辑模式
    """

    print("\n" + "=" * 50)
    print("📝 进入讲稿编辑模式")
    print("=" * 50)

    script_files = sorted(
        [
            f for f in os.listdir(SCRIPT_DIR)
            if f.startswith("page_") and f.endswith(".txt")
        ],
        key=lambda x: int(x.split("_")[1].split(".")[0])
    )

    if not script_files:
        print("未找到讲稿文件")
        return

    while True:

        print("\n请选择操作：")
        print("1. 查看所有讲稿")
        print("2. 手动编辑指定页面")
        print("3. AI对话式优化讲稿")
        print("4. 查看历史版本")
        print("5. 退出编辑模式")

        choice = input("请输入选项 (1-5): ").strip()

        if choice == "1":
            view_all_scripts(script_files)

        elif choice == "2":
            edit_single_page(script_files)

        elif choice == "3":
            chat_edit_script(script_files)

        elif choice == "4":
            view_history_versions()

        elif choice == "5":
            print("退出编辑模式")
            break

        else:
            print("无效输入，请重新输入")


def view_all_scripts(script_files):
    """
    查看所有讲稿
    """

    print("\n" + "=" * 50)

    for script_file in script_files:

        page_num = int(script_file.split("_")[1].split(".")[0])

        file_path = os.path.join(SCRIPT_DIR, script_file)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        print(f"第{page_num}页：{content}")

    print("=" * 50)


def edit_single_page(script_files):
    """
    手动编辑指定页面
    """

    try:

        page_num = int(input("请输入页码: ").strip())

        script_file = f"page_{page_num}.txt"

        if script_file not in script_files:
            print("未找到该页")
            return

        file_path = os.path.join(SCRIPT_DIR, script_file)

        with open(file_path, "r", encoding="utf-8") as f:
            current_content = f.read().strip()
        backup_script(page_num, current_content)  

        print("\n当前内容：")
        print(current_content)

        print("\n请输入新的讲稿内容（最多70字）")
        print("输入完成后连续按两次回车结束：")

        lines = []

        while True:

            line = input()

            if line == "":
                break

            lines.append(line)

        new_content = "".join(lines).strip()

        if not new_content:
            print("未修改")
            return

        new_content = clean_ai_script(new_content)
        if len(new_content) > 70:
            print("内容超过70字，已自动截断")
            new_content = new_content[:70]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print("✅ 修改完成")

    except ValueError:
        print("页码输入错误")

def chat_edit_script(script_files):
    """
    AI多轮对话优化讲稿
    """

    try:

        page_num = int(input("请输入页码: ").strip())

        script_file = f"page_{page_num}.txt"

        if script_file not in script_files:

            print("未找到该页")
            return

        file_path = os.path.join(SCRIPT_DIR, script_file)
        
        with open(file_path, "r", encoding="utf-8") as f:
            current_content = f.read().strip()
        backup_script(page_num, current_content)

        print("\n当前讲稿：")
        print(current_content)

        print("\n进入AI对话优化模式")
        print("输入 exit 结束优化")

        conversation_history = [
            {
                "role": "system",
                "content": (
                    "你是一位专业教师，"
                    "负责优化课堂讲稿。"
                    "讲稿必须："
                    "1. 不超过70字"
                    "2. 适合课堂讲解"
                    "3. 语言自然"
                    "4. 只返回修改后的讲稿"
                )
            },
            {
                "role": "user",
                "content": f"当前讲稿：{current_content}"
            }
        ]

        latest_script = current_content

        while True:

            feedback = input("\n你：").strip()

            if feedback.lower() == "exit":

                break

            if not feedback:

                continue

            conversation_history.append(
                {
                    "role": "user",
                    "content": feedback
                }
            )

            print("\nAI正在优化讲稿...")

            ai_response = call_ai_api(conversation_history)

            if ai_response is None:

                print("AI生成失败")
                continue

            ai_response = clean_ai_script(ai_response)

            if len(ai_response) > 70:

                ai_response = ai_response[:70]

            latest_script = ai_response

            conversation_history.append(
                {
                    "role": "assistant",
                    "content": ai_response
                }
            )

            print(f"\nAI：{ai_response}")

        save_choice = input("\n是否保存最终讲稿？(y/n): ").strip().lower()

        if save_choice == "y":

            with open(file_path, "w", encoding="utf-8") as f:

                f.write(latest_script)

            print("✅ 讲稿已保存")

        else:

            print("未保存修改")

    except ValueError:

        print("页码输入错误")

def view_history_versions():
    """
    查看历史版本
    """

    history_root = os.path.join(SCRIPT_DIR, "history")

    if not os.path.exists(history_root):

        print("暂无历史版本")
        return

    for page_dir in os.listdir(history_root):

        page_path = os.path.join(history_root, page_dir)

        if not os.path.isdir(page_path):
            continue

        print(f"\n{page_dir} 历史版本：")

        backups = sorted(os.listdir(page_path))

        for backup_file in backups:

            backup_path = os.path.join(page_path, backup_file)

            with open(backup_path, "r", encoding="utf-8") as f:

                content = f.read().strip()

            print(f"{backup_file} -> {content}")
def validate_and_extract_script(ai_response):
    """
    验证AI返回格式并保存讲稿
    """

    os.makedirs(SCRIPT_DIR, exist_ok=True)

    lines = ai_response.strip().split("\n")

    page_scripts = {}

    for line in lines:

        line = line.strip()

        if line.startswith("第") and "页：" in line:

            try:

                page_part, script_part = line.split("：", 1)

                page_num = int(
                    page_part.replace("第", "").replace("页", "")
                )

                if len(script_part) > 70:
                    script_part = script_part[:70]

                page_scripts[page_num] = clean_ai_script(script_part)

            except:
                print(f"格式错误: {line}")
                return False

    if not page_scripts:
        print("未找到有效讲稿")
        return False

    for page_num, script in page_scripts.items():

        script_file = os.path.join(
            SCRIPT_DIR,
            f"page_{page_num}.txt"
        )

        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script)

        print(f"已保存第{page_num}页讲稿")

    return True