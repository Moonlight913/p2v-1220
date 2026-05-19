import os
import json
import base64
import hashlib
import requests
from config import SILICONFLOW_API_KEY, SILICONFLOW_API_URL

# 缓存相关
CACHE_FILE = "cache/image_desc.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

# 图片编码 
def encode_image_base64(image_path):
    if not os.path.exists(image_path):
        print(f"图片不存在: {image_path}")
        return None
    with open(image_path, "rb") as f:
        img_data = f.read()
        img_b64 = base64.b64encode(img_data).decode("utf-8")
    ext = os.path.splitext(image_path)[1].lower()
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".bmp": "image/bmp"
    }.get(ext, "image/png")
    return f"data:{mime_type};base64,{img_b64}"

# 图片哈希 
def get_image_hash(image_path):
    with open(image_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# 单图视觉API调用（带重试）
def call_vision_api_single(image_path, retries=2):
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json"
    }
    img_url = encode_image_base64(image_path)
    if not img_url:
        return None

    prompt = (
    "直接输出图片内容的描述，不要有任何引导词、解释或分析，不要出现'如图所示'、'图中显示'等词语。"
    "例如：'一只白色猫躺在沙发上' 或 '柱状图显示Q3销售额增长20%'。"
    "描述不超过30字。"
)

    data = {
        "model": "Qwen/Qwen3-VL-8B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": img_url}}
                ]
            }
        ],
        "max_tokens": 100,
        "temperature": 0.5
    }

    for attempt in range(retries):
        try:
            response = requests.post(SILICONFLOW_API_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            ai_response = response.json()
            content = ai_response["choices"][0]["message"]["content"]
            return content.strip()
        except Exception as e:
            print(f"视觉API调用失败 {os.path.basename(image_path)} (尝试 {attempt+1}/{retries}): {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(e.response.text)
            if attempt == retries - 1:
                return None
            import time
            time.sleep(1)
    return None

#  从 extract_pic.json 提取每页图片路径 
def get_slide_images(extract_json_path):
    if not os.path.exists(extract_json_path):
        print(f"未找到JSON文件: {extract_json_path}")
        return {}
    with open(extract_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    slide_images = {}
    for slide in data.get("slides", []):
        slide_num = int(slide.get("slide_number", 0))
        if slide_num == 0:
            continue
        images = []
        for elem in slide.get("animated_elements", []):
            img_path = elem.get("image_path")
            if img_path and os.path.exists(img_path):
                images.append(img_path)
        if images:
            slide_images[slide_num] = images
    return slide_images
def ask_page_by_page(slide_images, total_pages):
    """
    逐页：
    1. 选择需要理解的图片
    2. AI先理解图片
    3. 展示理解结果
    4. 用户再决定哪些图片融入讲稿

    返回：
    {
        page_num: [
            {
                "path": xxx,
                "desc": xxx
            }
        ]
    }
    """

    selected = {}

    print("\n" + "=" * 50)
    print("🖼️ 图片理解设置")
    print("=" * 50)

    cache = load_cache()

    for page_num in range(1, total_pages + 1):

        if page_num not in slide_images:
            continue

        images = slide_images[page_num]

        print(f"\n第{page_num}页检测到 {len(images)} 张图片:")

        for i, img_path in enumerate(images):
            print(f"  {i+1}. {os.path.basename(img_path)}")

        choice = input(
            f"是否理解第{page_num}页的图片？(y/n, 默认n): "
        ).strip().lower()

        if choice != "y":
            continue

        # 第一步：选择需要理解的图片

        print(
            "请输入需要理解的图片编号"
            "（多个用逗号分隔，如1,3）"
            "；输入 all 选择全部："
        )

        selection = input(">>> ").strip().lower()

        selection = selection.replace("，", ",").replace(" ", "")

        if selection == "none":

            print("跳过本页")
            continue

        elif selection == "all":

            selected_paths = images[:]

        else:

            indices = []

            for part in selection.split(","):

                try:

                    idx = int(part) - 1

                    if 0 <= idx < len(images):
                        indices.append(idx)

                except:
                    pass

            indices = sorted(set(indices))

            selected_paths = [images[i] for i in indices]

        if not selected_paths:

            print("未选择有效图片")
            continue

        # 第二步：立即AI理解

        understood_images = []

        print("\n正在理解图片内容...\n")

        for img_path in selected_paths:

            img_hash = get_image_hash(img_path)

            # 缓存命中
            if img_hash in cache:

                desc = cache[img_hash]

                print(
                    f"缓存命中: "
                    f"{os.path.basename(img_path)}"
                )

            else:

                print(
                    f"调用视觉API: "
                    f"{os.path.basename(img_path)}"
                )

                desc = call_vision_api_single(img_path)

                if desc:

                    cache[img_hash] = desc

                else:

                    desc = "[图片理解失败]"

            understood_images.append({
                "path": img_path,
                "desc": desc,
                "original_index": images.index(img_path) + 1
            })

        save_cache(cache)

        # 第三步：展示理解结果

        print("\n图片理解结果：")
        for i, item in enumerate(understood_images):

            print(
                f"{i+1}. "
                f"(原图{item['original_index']}) "
                f"{item['desc']}"
            )
        # 第四步：选择哪些融入讲稿

        print(
            "\n请输入需要融入讲稿的图片编号"
            "（多个用逗号分隔，如1,3）"
            "；输入 all 全部融入"
            "；输入 none 全不融入："
        )

        integrate_input = input(">>> ").strip().lower()

        integrate_input = (
            integrate_input
            .replace("，", ",")
            .replace(" ", "")
        )

        if integrate_input == "none":

            print("本页图片不会融入讲稿")
            continue

        elif integrate_input == "all":

            selected[page_num] = understood_images

        else:

            integrate_indices = []

            for part in integrate_input.split(","):

                try:

                    idx = int(part) - 1

                    if 0 <= idx < len(understood_images):
                        integrate_indices.append(idx)

                except:
                    pass

            integrate_indices = sorted(set(integrate_indices))

            final_images = [
                understood_images[i]
                for i in integrate_indices
            ]

            if final_images:

                selected[page_num] = final_images

        print(f"第{page_num}页设置完成")

    return selected

def build_descriptions_for_selected(selected):
    """
    将最终需要融入讲稿的图片描述
    拼接成 prompt 文本
    """
    new_descriptions = {}
    for page_num, image_infos in selected.items():
        desc_parts = []

        for i, item in enumerate(image_infos):
            desc = item["desc"]
            desc_parts.append(
                f"图{i+1}：{desc}"
            )

        formatted = "；".join(desc_parts)
        new_descriptions[page_num] = formatted

    return new_descriptions

# 主入口函数 
def run_image_understanding(ppt_path, extract_json_path, total_pages):
    slide_images = get_slide_images(extract_json_path)
    if not slide_images:
        print("该PPT中没有检测到独立图片元素，跳过图片理解步骤")
        return {}

    selected = ask_page_by_page(slide_images, total_pages)
    if not selected:
        print("\n未选择任何图片进行理解")
        return {}

    cache = load_cache()
    image_descriptions = build_descriptions_for_selected(selected)


    print(f"\n✅ 共理解了 {len(image_descriptions)} 页的图片")
    return image_descriptions

#  辅助函数（供外部使用，可选）
def build_image_context(image_descriptions):
    if not image_descriptions:
        return ""
    parts = ["\n各页PPT中的图片内容："]
    for page_num in sorted(image_descriptions.keys()):
        parts.append(f"第{page_num}页图片: {image_descriptions[page_num]}")
    return "\n".join(parts)