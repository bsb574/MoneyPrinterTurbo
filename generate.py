#!/usr/bin/env python3
"""
口播视频生成器 v2.0 — 基于 MoneyPrinterTurbo 引擎

从口播文案（Markdown/纯文本）自动生成竖屏视频：
  文案 → TTS(配音) → 字幕 → 素材(在线/本地/纯色) → 合成

Usage:
  python generate.py --script 口播文案.md
  python generate.py --script 口播文案.md --voice "zh-CN-XiaoxiaoNeural-Female"
  python generate.py --script 口播文案.md --local-materials /path/to/videos/
  python generate.py --script 口播文案.md --background   # 纯色背景，无需API Key
"""

import argparse
import os
import re
import sys
import shutil
import math
import random
from pathlib import Path
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app.services import voice as voice_svc
from app.services import subtitle as subtitle_svc
from app.services import video as video_svc
from app.models.schema import VideoParams, VideoAspect, VideoConcatMode, MaterialInfo
from app.utils import utils
from loguru import logger


# ═══════════════════════════════════════════════════════════════════
#  文案清理
# ═══════════════════════════════════════════════════════════════════

def clean_script(text: str) -> str:
    """清理 Markdown 文案为纯文本。"""
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)
    text = re.sub(r'`{1,3}(.+?)`{1,3}', r'\1', text)
    text = re.sub(r'^>\s?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[\-\*\+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[-=*_]{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'\n(?!\n)', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def read_script(file_path: str) -> str:
    """从文件读取并清理文案。"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    ext = Path(file_path).suffix.lower()
    return clean_script(content) if ext == '.md' else content.strip()


# ═══════════════════════════════════════════════════════════════════
#  纯色背景视频生成（无 API Key 时的兜底方案）
# ═══════════════════════════════════════════════════════════════════

_COLOR_PALETTES = [
    ["#667eea", "#764ba2", "#6c5ce7"],   # Purple gradient
    ["#a8e6cf", "#dcedc1", "#ffd3b6"],   # Pastel green
    ["#74b9ff", "#a29bfe", "#81ecec"],   # Ocean blue
    ["#55efc4", "#00b894", "#00cec9"],   # Teal green
    ["#fd79a8", "#e84393", "#d63031"],   # Rose
    ["#fdcb6e", "#e17055", "#d63031"],   # Sunset
    ["#a29bfe", "#6c5ce7", "#fd79a8"],   # Lavender
    ["#00cec9", "#0984e3", "#6c5ce7"],   # Blue-purple
    ["#ff7675", "#fab1a0", "#81ecec"],   # Coral mint
    ["#dfe6e9", "#b2bec3", "#636e72"],   # Elegant grey
]


def create_background_video(output_path: str, duration: float, aspect: str,
                            width: int = 1080, height: int = 1920):
    """用纯色背景生成视频素材（无需 API Key）。"""
    from moviepy import ColorClip, CompositeVideoClip

    palette = random.choice(_COLOR_PALETTES)
    seg_duration = duration / 3

    clips = []
    for i, color in enumerate(palette[:3]):
        start = i * seg_duration
        # 精确控制每段时长以匹配总 duration
        if i < 2:
            seg_dur = seg_duration
        else:
            seg_dur = duration - start
        if seg_dur <= 0:
            break
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        c = ColorClip(size=(width, height), color=(r, g, b)).with_duration(seg_dur)
        clips.append(c.with_start(start))

    if not clips:
        c = ColorClip(size=(width, height), color=(100, 130, 180)).with_duration(duration)
        clips = [c]

    final = CompositeVideoClip(clips, size=(width, height))
    final.write_videofile(output_path, fps=30, logger=None, audio=False)
    final.close()
    return output_path


def create_image_background(output_path: str, image_paths, duration: float,
                            width: int = 1080, height: int = 1920):
    """用本地图片生成视频素材。"""
    from moviepy import ImageClip, CompositeVideoClip

    clip_duration = max(4.0, duration / max(len(image_paths), 1))
    clips = []
    current_time = 0.0

    for img_path in image_paths:
        if current_time >= duration:
            break
        remaining = duration - current_time
        seg_dur = min(clip_duration, remaining)
        if seg_dur <= 0.1:
            break
        try:
            clip = ImageClip(img_path, duration=seg_dur).with_position("center")
            # 缩放填充
            iw, ih = clip.size
            scale = max(width / iw, height / ih) * 1.05
            clip = clip.resized(new_size=(int(iw * scale), int(ih * scale)))
            # 裁剪
            cx, cy = clip.size
            clip = clip.cropped(x_center=cx // 2, y_center=cy // 2,
                                width=width, height=height)
            clips.append(clip.with_start(current_time))
            current_time += seg_dur
        except Exception as e:
            logger.warning(f"图片加载失败: {img_path}: {e}")
            continue

    if not clips:
        return create_background_video(output_path, duration, "9:16", width, height)

    final = CompositeVideoClip(clips, size=(width, height))
    final.write_videofile(output_path, fps=30, logger=None, audio=False)
    final.close()
    return output_path


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="口播视频生成器 — 从文案自动生成竖屏短视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python generate.py --script 口播文案.md
  python generate.py --script 口播文案.md --voice "zh-CN-XiaoxiaoNeural-Female" --output my_video.mp4
  python generate.py --script 口播文案.md --background   # 纯色背景，无需API Key
  python generate.py --script 口播文案.md --local-materials ./素材/  --bgm none
        """,
    )
    parser.add_argument("--script", required=True, help="口播文案文件路径 (.md / .txt)")
    parser.add_argument("--output", default="", help="输出视频路径（默认自动生成）")
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural-Female",
                        help="TTS 音色 (默认 zh-CN-XiaoxiaoNeural-Female)")
    parser.add_argument("--voice-rate", type=float, default=1.0,
                        help="语速 0.5-2.0 (默认 1.0)")
    parser.add_argument("--aspect", default="9:16",
                        choices=["9:16", "16:9", "1:1"],
                        help="宽高比 (默认 9:16 竖屏)")
    parser.add_argument("--bgm", default="random",
                        help="背景音乐: random / none / 文件名")
    parser.add_argument("--bgm-volume", type=float, default=0.2, help="BGM 音量")
    parser.add_argument("--subtitle-position", default="bottom",
                        choices=["top", "center", "bottom"], help="字幕位置")
    parser.add_argument("--font-size", type=int, default=60, help="字号")
    parser.add_argument("--no-subtitle", action="store_false", dest="subtitle_enabled",
                        default=True, help="禁用字幕")

    # 视频素材来源
    src = parser.add_argument_group("视频素材来源")
    src.add_argument("--video-source", default="pexels",
                     choices=["pexels", "pixabay", "local", "background", "images"],
                     help="素材来源 (默认 pexels)")
    src.add_argument("--local-materials", default="",
                     help="本地素材目录 (video_source=local 时使用)")
    src.add_argument("--image-dir", default="",
                     help="图片目录 (video_source=images 时使用)")
    src.add_argument("--background", action="store_const", dest="video_source",
                     const="background",
                     help="使用纯色背景（无需 API Key 的快捷方式）")
    src.add_argument("--search-terms", default="",
                     help="搜索关键词，逗号分隔（默认从文案提取）")
    src.add_argument("--max-clip-duration", type=int, default=5,
                     help="单段素材最大时长秒 (默认 5)")
    parser.add_argument("--n-threads", type=int, default=2, help="编码线程数")
    parser.add_argument("--keep-temp", action="store_true", help="保留临时文件")
    return parser.parse_args()


def main():
    args = parse_args()
    script = read_script(args.script)
    if not script:
        logger.error("文案为空")
        return

    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_dir = utils.task_dir(task_id)
    os.makedirs(task_dir, exist_ok=True)

    if not args.output:
        output_file = os.path.join(PROJECT_DIR, f"{Path(args.script).stem}_output.mp4")
    else:
        output_file = args.output

    logger.info("=" * 50)
    logger.info("  口播视频生成器 v2.0")
    logger.info(f"  文案: {args.script} ({len(script)} 字)")
    logger.info(f"  音色: {args.voice}")
    logger.info(f"  来源: {args.video_source}")
    logger.info("=" * 50)

    # ═══ 1. TTS ═══
    logger.info("\n[1/4] 生成配音...")
    audio_file = os.path.join(task_dir, "audio.mp3")
    sub_maker = voice_svc.tts(
        text=script,
        voice_name=voice_svc.parse_voice_name(args.voice),
        voice_rate=args.voice_rate,
        voice_file=audio_file,
    )
    if sub_maker is None:
        logger.error("TTS 失败，请检查网络或音色名称")
        return

    audio_duration = math.ceil(voice_svc.get_audio_duration(sub_maker))
    logger.info(f"  配音时长: {audio_duration}s")

    # ═══ 2. 字幕 ═══
    subtitle_path = ""
    if args.subtitle_enabled:
        logger.info("\n[2/4] 生成字幕...")
        subtitle_path = os.path.join(task_dir, "subtitle.srt")
        voice_svc.create_subtitle(text=script, sub_maker=sub_maker,
                                  subtitle_file=subtitle_path)
        if os.path.exists(subtitle_path):
            logger.info(f"  字幕已生成: {subtitle_path}")
        else:
            logger.warning("  字幕生成失败，继续...")
            subtitle_path = ""

    # ═══ 3. 素材 ═══
    logger.info("\n[3/4] 获取视频素材...")
    downloaded_videos = []

    if args.video_source == "local":
        if not args.local_materials or not os.path.isdir(args.local_materials):
            logger.error("  请指定有效的 --local-materials 目录")
            return
        exts = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".png", ".jpg", ".jpeg", ".gif")
        files = sorted([os.path.join(args.local_materials, f)
                        for f in os.listdir(args.local_materials)
                        if f.lower().endswith(exts)])
        if not files:
            logger.error(f"  目录内无素材文件: {args.local_materials}")
            return
        v_exts = (".mp4", ".mov", ".avi", ".mkv", ".webm")
        img_exts = (".png", ".jpg", ".jpeg", ".gif")
        vids = [f for f in files if f.lower().endswith(v_exts)]
        imgs = [f for f in files if f.lower().endswith(img_exts)]
        logger.info(f"  本地素材: {len(vids)} 视频, {len(imgs)} 图片")
        if vids:
            downloaded_videos = vids
        elif imgs:
            # 图片 -> 视频
            bg_path = os.path.join(task_dir, "bg_material.mp4")
            create_image_background(bg_path, imgs, audio_duration,
                                    1080, 1920 if args.aspect == "9:16" else 1080)
            if os.path.exists(bg_path):
                downloaded_videos = [bg_path]
        else:
            logger.error("  无有效素材")
            return

    elif args.video_source == "background":
        bg_path = os.path.join(task_dir, "bg_material.mp4")
        w, h = (1080, 1920) if args.aspect == "9:16" else (1920, 1080) if args.aspect == "16:9" else (1080, 1080)
        logger.info(f"  生成纯色背景视频 ({audio_duration}s)...")
        create_background_video(bg_path, audio_duration, args.aspect, w, h)
        if os.path.exists(bg_path):
            downloaded_videos = [bg_path]

    elif args.video_source == "images":
        img_dir = args.image_dir or args.local_materials
        if not img_dir or not os.path.isdir(img_dir):
            logger.error("  请指定 --image-dir 或 --local-materials")
            return
        img_exts = (".png", ".jpg", ".jpeg")
        imgs = sorted([os.path.join(img_dir, f) for f in os.listdir(img_dir)
                       if f.lower().endswith(img_exts)])
        if not imgs:
            logger.error(f"  目录内无图片: {img_dir}")
            return
        bg_path = os.path.join(task_dir, "bg_material.mp4")
        w, h = (1080, 1920) if args.aspect == "9:16" else (1920, 1080) if args.aspect == "16:9" else (1080, 1080)
        logger.info(f"  用 {len(imgs)} 张图片生成背景...")
        create_image_background(bg_path, imgs, audio_duration, w, h)
        if os.path.exists(bg_path):
            downloaded_videos = [bg_path]

    elif args.video_source in ("pexels", "pixabay", "coverr"):
        from app.services import material as material_svc
        search_terms = [t.strip() for t in args.search_terms.split(",") if t.strip()]
        if not search_terms:
            sentences = [s.strip() for s in re.split(r'[。！？\n]', script) if len(s.strip()) > 5]
            search_terms = sentences[:5] if sentences else [script[:50]]
        try:
            downloaded_videos = material_svc.download_videos(
                task_id=task_id, search_terms=search_terms,
                source=args.video_source,
                video_aspect=VideoAspect(args.aspect),
                video_concat_mode=VideoConcatMode.sequential,
                audio_duration=audio_duration,
                max_clip_duration=args.max_clip_duration,
            )
        except ValueError as e:
            logger.error(f"  素材下载失败: {e}")
            logger.error("  提示: 请在 config.toml 中配置 API Key，或使用 --background 纯色背景模式")
            return

    if not downloaded_videos:
        logger.error("  无可用视频素材")
        return
    logger.info(f"  共 {len(downloaded_videos)} 个素材片段")

    # ═══ 4. 合成 ═══
    logger.info("\n[4/4] 合成最终视频...")

    # 对于 background/images 模式，背景视频已经是完整时长，直接用于最终合成
    if args.video_source in ("background", "images") and len(downloaded_videos) == 1:
        logger.info("  使用现有背景视频直接合成...")
        combined_path = downloaded_videos[0]
    else:
        combined_path = os.path.join(task_dir, "combined.mp4")
        try:
            video_svc.combine_videos(
                combined_video_path=combined_path,
                video_paths=downloaded_videos,
                audio_file=audio_file,
                video_aspect=VideoAspect(args.aspect),
                video_concat_mode=VideoConcatMode.sequential,
                max_clip_duration=args.max_clip_duration,
                threads=args.n_threads,
            )
        except Exception as e:
            logger.error(f"  视频合成失败: {e}")
            return

        if not os.path.exists(combined_path):
            logger.error("  合成视频文件未生成")
            return

    params = VideoParams(
        video_subject=Path(args.script).stem,
        video_script=script,
        video_aspect=args.aspect,
        video_concat_mode=VideoConcatMode.sequential.value,
        video_clip_duration=args.max_clip_duration,
        video_count=1,
        video_source=args.video_source,
        voice_name=args.voice,
        voice_rate=args.voice_rate,
        bgm_type=args.bgm if args.bgm != "none" else "",
        bgm_volume=args.bgm_volume,
        subtitle_enabled=args.subtitle_enabled,
        subtitle_position=args.subtitle_position,
        font_name="STHeitiMedium.ttc",
        text_fore_color="#FFFFFF",
        text_background_color=True,
        font_size=args.font_size,
        stroke_color="#000000",
        stroke_width=1.5,
        n_threads=args.n_threads,
    )

    try:
        video_svc.generate_video(
            video_path=combined_path,
            audio_path=audio_file,
            subtitle_path=subtitle_path,
            output_file=output_file,
            params=params,
        )
    except Exception as e:
        logger.error(f"  最终视频生成失败: {e}")
        return

    if os.path.exists(output_file):
        size_mb = os.path.getsize(output_file) / (1024 * 1024)
        logger.info("\n" + "=" * 50)
        logger.success(f"  ✅ 视频生成成功!")
        logger.success(f"     输出: {output_file}")
        logger.success(f"     大小: {size_mb:.1f} MB")
        logger.success(f"     时长: ~{audio_duration}s")
        logger.success(f"     分辨率: {args.aspect}")
        logger.info("=" * 50)
    else:
        logger.error("  最终视频文件未生成")

    if not args.keep_temp:
        shutil.rmtree(task_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
