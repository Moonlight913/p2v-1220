# 主程序入口

import sys
import os

from ppt_parser import extract_ppt_text
from ai_script_generator import generate_ai_script
from voice_synthesizer import synthesize_voices
from video_generator import generate_all_ppt_videos
from video_merger import merge_videos
from gen_json import extract_only_images
from delete_image import run_deletion_test
from add_voice import merge_video_audio


def main():

    if len(sys.argv) < 2:

        print("使用方法:")
        print("python main.py <ppt文件路径>")
        print("python main.py <ppt文件路径> --no-interactive")

        sys.exit(1)

    ppt_path = sys.argv[1]

    enable_interactive = True

    # 是否关闭交互模式
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

    # Step2 AI生成讲稿
    print("\n[步骤2] AI生成讲稿...")

    if not generate_ai_script(
        ppt_text,
        enable_interactive=enable_interactive
    ):

        print("AI讲稿生成失败")

        sys.exit(1)

    # Step3 语音生成
    print("\n[步骤3] 语音生成...")

    if not synthesize_voices():

        print("语音生成失败")

        sys.exit(1)

    # Step4 提取图片元素
    print("\n[步骤4] 提取图片元素...")

    if not extract_only_images(
        ppt_path,
        "extract_pic.json"
    ):

        print("图片提取失败")

        sys.exit(1)

    # Step5 删除图片元素
    print("\n[步骤5] 删除图片元素...")

    if not run_deletion_test(
        "extract_pic.json",
        ppt_path
    ):

        print("删除图片失败")

        sys.exit(1)

    # Step6 生成动画视频
    print("\n[步骤6] 生成动画视频...")

    if not generate_all_ppt_videos():

        print("动画视频生成失败")

        sys.exit(1)

    # Step7 合并音频
    print("\n[步骤7] 合并音频...")

    if not merge_video_audio():

        print("音频合并失败")

        sys.exit(1)

    # Step8 合并最终视频
    print("\n[步骤8] 合并最终视频...")

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