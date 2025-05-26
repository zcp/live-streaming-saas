# app/services/stream.py
import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.stream import LiveStream, StreamStatus, StreamCategory, StreamTag, StreamStatistics, StreamPermission, \
    StreamPermissionRule
from app.schemas.stream import StreamCreate, StreamUpdate, StreamStatusUpdate, StreamSearch, StreamPermissionCreate, \
    StreamPermissionUpdate, StreamPermissionRuleCreate, StreamPermissionRuleUpdate


class StreamService:
    def __init__(self, db: Session):
        self.db = db
        self.active_streams = {}  # 存储活跃的推流进程


    def get_stream(self, stream_id: UUID) -> Optional[LiveStream]:
        return self.db.query(LiveStream).filter(LiveStream.id == stream_id).first()

    def get_user_streams(self, user_id: int) -> List[LiveStream]:
        return self.db.query(LiveStream).filter(LiveStream.user_id == user_id).all()

    def update_stream(self, stream_id: UUID, stream: StreamUpdate) -> Optional[LiveStream]:
        db_stream = self.get_stream(stream_id)
        if db_stream:
            for key, value in stream.dict(exclude_unset=True).items():
                setattr(db_stream, key, value)
            self.db.commit()
            self.db.refresh(db_stream)
        return db_stream

    def delete_stream(self, stream_id: UUID) -> bool:
        db_stream = self.get_stream(stream_id)
        if db_stream:
            self.db.delete(db_stream)
            self.db.commit()
            return True
        return False

    def update_stream_status(self, stream_id: UUID, status_update: StreamStatusUpdate) -> Optional[LiveStream]:
        db_stream = self.get_stream(stream_id)
        if db_stream:
            db_stream.status = status_update.status
            if status_update.start_time:
                db_stream.start_time = status_update.start_time
            if status_update.end_time:
                db_stream.end_time = status_update.end_time
            self.db.commit()
            self.db.refresh(db_stream)
        return db_stream

    def search_streams(self, search: StreamSearch) -> tuple[List[LiveStream], int]:
        query = self.db.query(LiveStream)

        if search.title:
            query = query.filter(LiveStream.title.ilike(f"%{search.title}%"))
        if search.status:
            query = query.filter(LiveStream.status == search.status)
        if search.category_id:
            query = query.filter(LiveStream.category_id == search.category_id)
        if search.is_private is not None:
            query = query.filter(LiveStream.is_private == search.is_private)
        if search.start_time_from:
            query = query.filter(LiveStream.start_time >= search.start_time_from)
        if search.start_time_to:
            query = query.filter(LiveStream.start_time <= search.start_time_to)

        total = query.count()
        streams = query.offset((search.page - 1) * search.page_size).limit(search.page_size).all()

        return streams, total

    def create_stream_permission(self, permission: StreamPermissionCreate) -> StreamPermission:
        db_permission = StreamPermission(
            stream_id=permission.stream_id,
            user_id=permission.user_id,
            permission_type=permission.permission_type,
            is_public=permission.is_public
        )
        self.db.add(db_permission)
        self.db.commit()
        self.db.refresh(db_permission)
        return db_permission

    def update_stream_permission(self, permission_id: UUID, permission: StreamPermissionUpdate) -> Optional[
        StreamPermission]:
        db_permission = self.db.query(StreamPermission).filter(StreamPermission.id == permission_id).first()
        if db_permission:
            for key, value in permission.dict(exclude_unset=True).items():
                setattr(db_permission, key, value)
            self.db.commit()
            self.db.refresh(db_permission)
        return db_permission

    def create_stream_permission_rule(self, rule: StreamPermissionRuleCreate) -> StreamPermissionRule:
        db_rule = StreamPermissionRule(
            rule_type=rule.rule_type,
            rule_value=rule.rule_value.dict(),
            permission_type=rule.permission_type
        )
        self.db.add(db_rule)
        self.db.commit()
        self.db.refresh(db_rule)
        return db_rule

    def update_stream_permission_rule(self, rule_id: UUID, rule: StreamPermissionRuleUpdate) -> Optional[
        StreamPermissionRule]:
        db_rule = self.db.query(StreamPermissionRule).filter(StreamPermissionRule.id == rule_id).first()
        if db_rule:
            for key, value in rule.dict(exclude_unset=True).items():
                setattr(db_rule, key, value)
            self.db.commit()
            self.db.refresh(db_rule)
        return db_rule



    def create_stream(self, stream: StreamCreate, user_id: int) -> LiveStream:
            """创建直播流对象"""
            try:
                # 生成推流密钥
                stream_key = self._generate_stream_key()
                print(stream_key)
                # 创建直播流对象
                db_stream = LiveStream(
                    user_id=user_id,
                    title=stream.title,
                    description=stream.description,
                    cover_url=stream.cover_url,
                    is_private=stream.is_private,
                    is_recorded=stream.is_recorded,
                    category_id=stream.category_id,
                    stream_key=stream_key,
                    storage_type=stream.storage_type,
                    region=stream.region,
                    provider=stream.provider,
                    status=StreamStatus.CREATED,
                    is_streaming=False
                )

                self.db.add(db_stream)
                self.db.commit()
                self.db.refresh(db_stream)

                return db_stream
            except Exception as e:
                self.db.rollback()
                raise e

    async def start_streaming(self, stream_id: UUID) -> bool:
            """开始推流"""
            try:
                # 获取直播流对象
                print("1")
                stream = self.get_stream(stream_id)
                if not stream:
                    return False
                print("2")
                # 检查直播流状态
                if stream.is_streaming:
                    raise ValueError("直播流已经在推流中")
                print("3")
                # 更新推流开始时间
                stream.start_time = datetime.now(timezone.utc)
                stream.status = StreamStatus.STREAMING
                stream.is_streaming = True
                #stream.stream_count += 1  # 增加推流次数
                print("4")
                # 构建推流命令
                rtmp_url = self._build_rtmp_url(stream)
                print(rtmp_url)
                ffmpeg_cmd = self._build_ffmpeg_command(stream, rtmp_url)
                print(ffmpeg_cmd)
                print("5")
                # 启动推流进程
                process = await asyncio.create_subprocess_shell(
                    ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                print("6")
                # 存储进程信息
                self.active_streams[str(stream_id)] = {
                    'process': process,
                    'rtmp_url': rtmp_url
                }
                print("7")
                self.db.commit()
                print("7")
                return True
            except Exception as e:
                self.db.rollback()
                print(f"启动推流失败: {str(e)}")
                return False

    async def stop_streaming(self, stream_id: UUID) -> bool:
            """停止推流"""
            try:
                if str(stream_id) not in self.active_streams:
                    return False

                # 获取进程信息
                stream_info = self.active_streams[str(stream_id)]
                process = stream_info['process']

                # 停止进程
                process.terminate()
                await process.wait()

                # 更新直播流状态
                stream = self.get_stream(stream_id)
                if stream:
                    # 更新推流结束时间
                    stream.end_time = datetime.now(timezone.utc)
                    # 计算本次推流时长
                    stream.duration = int((stream.end_time - stream.start_time).total_seconds())
                    # 更新总推流时长
                    stream.total_stream_time += stream.duration
                    # 更新状态
                    stream.status = StreamStatus.ENDED
                    stream.is_streaming = False

                    self.db.commit()

                # 清理进程信息
                del self.active_streams[str(stream_id)]

                return True
            except Exception as e:
                self.db.rollback()
                print(f"停止推流失败: {str(e)}")
                return False

    def _build_rtmp_url(self, stream: LiveStream) -> str:
        return f"rtmp://124.220.235.226:1935/live/{stream.stream_key}"
        if stream.provider == "aliyun":
            return f"rtmp://{stream.region}.live.aliyuncs.com/live/{stream.stream_key}"
        elif stream.provider == "aws":
            return f"rtmp://{stream.region}.live.aws.com/live/{stream.stream_key}"
        elif stream.provider == "local":  # 添加本地 SRS 服务器选项
            return f"rtmp://124.220.235.226:1935/live/{stream.stream_key}"
        else:
            raise ValueError(f"不支持的推流提供商: {stream.provider}")

    def _build_ffmpeg_command(self, stream: LiveStream, rtmp_url: str) -> str:
        if stream.storage_type == "local":
            input_path = f"file://{stream.stream_path}"
        else:
            input_path = "D:\\test.mp4"

        return (
            f"ffmpeg -re "  # 以实时速率读取输入
            f"-i {input_path} "
            f"-c:v libx264 "  # 使用 H.264 编码
            f"-preset veryfast "  # 编码速度预设
            f"-b:v 500k "  # 视频比特率
            f"-maxrate 1000k "  # 最大比特率
            f"-bufsize 5000k "  # 缓冲区大小
            f"-g 50 "  # GOP 大小
            f"-c:a aac "  # 音频编码
            f"-b:a 128k "  # 音频比特率
            f"-ar 44100 "  # 音频采样率
            f"-f flv {rtmp_url}"
        )

    async def upload_video(self, stream_id: UUID, file_path: str) -> bool:
        """上传视频文件"""
        try:
            stream = self.get_stream(stream_id)
            if not stream:
                return False

            # 更新直播流信息
            stream.stream_path = file_path
            stream.status = StreamStatus.CREATED
            self.db.commit()

            return True
        except Exception as e:
            print(f"上传视频失败: {str(e)}")
            return False

    def _generate_stream_key(self) -> str:
        """
        生成唯一的流密钥
        Returns:
            str: 生成的 UUID4 字符串
        """
        return str(uuid.uuid4())