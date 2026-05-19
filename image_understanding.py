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

#  交互：逐页询问，并允许选择该页中的具体图片
def ask_page_by_page(slide_images, total_pages):
    """
    逐页询问用户是否需要添加图片描述，并允许选择该页中的特定图片。
    返回:
        dict: {page_num: [selected_image_paths]}  仅包含用户选中的图片路径
    """
    selected = {}
    print("\n" + "=" * 50)
    print("🖼️  图片理解设置")
    print("=" * 50)
    print("程序将逐页询问是否需要对图片进行AI理解")
    print("理解的图片描述将会融入讲稿中")
    print("=" * 50)

    for page_num in range(1, total_pages + 1):
        if page_num not in slide_images:
            continue
        images = slide_images[page_num]
        print(f"\n第{page_num}页检测到 {len(images)} 张图片:")
        for i, img_path in enumerate(images):
            print(f"  {i+1}. {os.path.basename(img_path)}")

        choice = input(f"是否理解第{page_num}页的图片？(y/n, 默认n): ").strip().lower()
        if choice != "y":
            continue

        # 让用户选择该页中的具体图片
        print("请输入需要描述的图片编号（多个用逗号分隔，如 1,3,5）；输入 'all' 选择全部；输入 'none' 取消本页：")
        selection = input(">>> ").strip().lower()
        selection = selection.replace("，", ",").replace(" ", "")
        if selection == "none":
            continue
        if selection == "all":
            selected_paths = images[:]
        else:
            indices = []
            for part in selection.split(","):
                try:
                    idx = int(part.strip()) - 1
                    if 0 <= idx < len(images):
                        indices.append(idx)
                    else:
                        print(f"  忽略无效编号: {part}")
                except ValueError:
                    print(f"  忽略无效输入: {part}")
            # 去重并保持原顺序
            unique_indices = sorted(set(indices))
            selected_paths = [images[i] for i in unique_indices]
            if not selected_paths:
                print("  未选择有效图片，跳过本页")
                continue

        selected[page_num] = selected_paths
        print(f"  已选择 {len(selected_paths)} 张图片")
    return selected

# 批量推理：利用缓存，逐张调用API，合并描述（结构化）
def build_descriptions_for_selected(selected, cache):
    new_descriptions = {}
    for page_num, image_paths in selected.items():
        desc_parts = []
        for img_path in image_paths:
            img_hash = get_image_hash(img_path)
            if img_hash in cache:
                desc = cache[img_hash]
                print(f"  缓存命中: {os.path.basename(img_path)} -> {desc}")
            else:
                print(f"  调用视觉API: {os.path.basename(img_path)} ...")
                desc = call_vision_api_single(img_path)
                if desc:
                    cache[img_hash] = desc
                    print(f"    -> {desc}")
                else:
                    desc = "[图片理解失败]"
            desc_parts.append(desc)

        # 结构化合并（添加图片序号）
        formatted = "；".join([f"图{i+1}：{desc}" for i, desc in enumerate(desc_parts)])
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
    image_descriptions = build_descriptions_for_selected(selected, cache)
    save_cache(cache)

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