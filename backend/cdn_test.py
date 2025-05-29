import asyncio
import re
import subprocess
import time

#VIDEO_URL = "https://lancet.im/videos/hls/playlist_local.m3u8"  # 你的 CDN 视频地址
VIDEO_URL = "https://pub-8ea55317b8624238a35e5c73454b9d2d.r2.dev/videos/hls/playlist_local.m3u8" #非 cdn
CONCURRENT_USERS = 10 # 并发用户数
TEST_DURATION = 15     # 每个任务持续时间（秒）

async def run_ffmpeg_test(index):
    cmd = [
        "ffmpeg",
        "-v", "error",
        "-stats",
        "-i", VIDEO_URL,
        "-t", str(TEST_DURATION),
        "-f", "null",
        "-"  # 不保存输出，只拉流测试
    ]
    print(f"User {index}: Starting FFmpeg stream test...")
    start_time = time.time()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    duration = time.time() - start_time
    print(f"User {index}: Done in {duration:.2f}s with return code {proc.returncode}")

    stderr_decoded = stderr.decode()

    # 正则提取 speed 和 fps
    speed_match = re.findall(r"speed=\s*([\d\.]+)x", stderr_decoded)
    fps_match = re.findall(r"fps=\s*(\d+)", stderr_decoded)

    speed = float(speed_match[-1]) if speed_match else None
    fps = int(fps_match[-1]) if fps_match else None

    print(f"User {index}: Speed = {speed}x, FPS = {fps}")

    if proc.returncode != 0:
        print(f"User {index} ERROR:\n{stderr.decode()}")

async def main():
    tasks = [run_ffmpeg_test(i + 1) for i in range(CONCURRENT_USERS)]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
