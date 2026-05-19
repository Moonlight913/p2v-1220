# AI讲稿生成模块
"""
AI讲稿生成模块 - 调用硅基流动API生成每页讲稿
支持自动生成和手动编辑两种模式
"""

import requests
import os
from config import SILICONFLOW_API_KEY, SILICONFLOW_API_URL, SCRIPT_DIR


def call_ai_api(prompt):
    """
    调用硅基流动API

    参数:
        prompt: 提示词

    返回:
        str: AI响应内容
    """

    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "Qwen/Qwen3-8B",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
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
            "以下是",
            "讲稿：",
            "讲稿:"
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
            return line[:50]

    return raw_text[:50]

def generate_ai_script(ppt_text, enable_interactive=True):
    """
    AI生成讲稿

    参数:
        ppt_text: PPT文本内容
        enable_interactive: 是否启用交互模式
    """

    prompt = f"""
你是一位专业老师。

请根据以下PPT内容，
为每一页生成简短自然的课堂讲稿。

PPT内容：
{ppt_text}

要求：
1. 每页讲稿不超过50字
2. 语言自然，适合口语表达
3. 可适当幽默
4. 必须严格按以下格式返回：

第1页：讲稿内容
第2页：讲稿内容
第3页：讲稿内容

不要返回任何额外解释。
"""

    print("正在调用AI生成讲稿...")

    script_content = call_ai_api(prompt)

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
        print("2. 编辑指定页面讲稿")
        print("3. AI重新生成指定页面讲稿")
        print("4. 退出编辑模式")

        choice = input("请输入选项 (1-4): ").strip()

        if choice == "1":
            view_all_scripts(script_files)

        elif choice == "2":
            edit_single_page(script_files)

        elif choice == "3":
            regenerate_with_feedback(script_files)

        elif choice == "4":
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

        print("\n当前内容：")
        print(current_content)

        print("\n请输入新的讲稿内容（最多50字）")
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
        if len(new_content) > 50:
            print("内容超过50字，已自动截断")
            new_content = new_content[:50]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print("✅ 修改完成")

    except ValueError:
        print("页码输入错误")


def regenerate_with_feedback(script_files):
    """
    AI重新生成指定页面讲稿
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

        print("\n当前讲稿：")
        print(current_content)

        feedback = input("\n请输入修改意见: ").strip()

        if not feedback:
            print("未输入修改意见")
            return

        prompt = f"""
请根据用户意见修改讲稿。

当前讲稿：
{current_content}

用户修改意见：
{feedback}

要求：
1. 不超过50字
2. 更适合课堂讲解
3. 语言自然
4. 只返回修改后的讲稿
"""

        print("\n正在重新生成...")

        new_content = call_ai_api(prompt)

        if new_content is None:
            print("AI重新生成失败")
            return

        # 清理AI返回内容
        new_content = clean_ai_script(new_content)

        if len(new_content) > 50:
            new_content = new_content[:50]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print("\n✅ 新讲稿：")
        print(new_content)

    except ValueError:
        print("页码输入错误")


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

                if len(script_part) > 50:
                    script_part = script_part[:50]

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