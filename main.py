# 主程序入口

import sys
import os
import json

from ppt_parser import extract_ppt_text
from ai_script_generator import generate_ai_script
from voice_synthesizer import synthesize_voices
from video_generator import generate_all_ppt_videos
from video_merger import merge_videos
from gen_json import extract_only_images
from delete_image import run_deletion_test
from add_voice import merge_video_audio
from image_understanding import run_image_understanding


def get_ppt_page_count(extract_json_path):
    """从extract_pic.json获取PPT总页数"""
    try:
        with open(extract_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return len(data.get("slides", []))
    except:
        return 0


def main():

    if len(sys.argv) < 2:

        print("使用方法:")
        print("python main.py <ppt文件路径>")
        print("python main.py <ppt文件路径> --no-interactive")

        sys.exit(1)

    ppt_path = sys.argv[1]

    enable_interactive = True

    if len(sys.argv) > 2 and sys.argv[2] == "--no-interactive":
        enable_interactive = False

    if not os.path.exists(ppt_path):

        print(f"文件不存在: {ppt_path}")

        sys.exit(1)

    print("=" * 50)
    print("开始PPT转视频")
    print("=" * 50)

    # Step1 PPT解析
    print("\n[步骤1] 解析PPT...")

    try:

        ppt_text = extract_ppt_text(ppt_path)

        print("PPT解析完成")

    except Exception as e:

        print(f"PPT解析失败: {e}")

        sys.exit(1)

    # Step2 提前提取图片元素（原步骤4提前到这里）
    # 目的：让图片可供AI理解，同时为后续步骤准备好数据
    print("\n[步骤2] 提取图片元素...")

    if not extract_only_images(
        ppt_path,
        "extract_pic.json"
    ):

        print("图片提取失败")

        sys.exit(1)

    total_pages = get_ppt_page_count("extract_pic.json")

    # Step3 图片理解（新增）
    # 逐页询问用户是否需要对图片进行AI理解
    # 理解的图片描述将融入讲稿生成
    image_descriptions = {}

    if enable_interactive:

        print("\n[步骤3] 图片理解（可选）...")

        image_descriptions = run_image_understanding(
            ppt_path,
            "extract_pic.json",
            total_pages
        )

    else:

        print("\n[步骤3] 跳过图片理解（非交互模式）")

    # Step4 AI生成讲稿（融入图片描述）
    print("\n[步骤4] AI生成讲稿...")

    if not generate_ai_script(
        ppt_text,
        enable_interactive=enable_interactive,
        image_descriptions=image_descriptions
    ):

        print("AI讲稿生成失败")

        sys.exit(1)

    # Step5 语音生成
    print("\n[步骤5] 语音生成...")

    if not synthesize_voices():

        print("语音生成失败")

        sys.exit(1)

    # Step6 删除图片元素（图片已在步骤2提取，现在只执行删除）
    print("\n[步骤6] 删除图片元素...")

    if not run_deletion_test(
        "extract_pic.json",
        ppt_path
    ):

        print("删除图片失败")

        sys.exit(1)

    # Step7 生成动画视频
    print("\n[步骤7] 生成动画视频...")

    if not generate_all_ppt_videos():

        print("动画视频生成失败")

        sys.exit(1)

    # Step8 合并音频
    print("\n[步骤8] 合并音频...")

    if not merge_video_audio():

        print("音频合并失败")

        sys.exit(1)

    # Step9 合并最终视频
    print("\n[步骤9] 合并最终视频...")

    success, final_video = merge_videos()

    if success:

        print("\n" + "=" * 50)
        print(f"处理完成！")
        print(f"最终视频: {final_video}")
        print("=" * 50)

    else:

        print("视频合并失败")

        sys.exit(1)


if __name__ == "__main__":
    main()