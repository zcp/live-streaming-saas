import os
import boto3
from botocore.config import Config
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# R2 配置
ACCESS_KEY = '8dd2b4b3cedbcd606fea84fd5cfc5b08'
SECRET_KEY = '5014e0600f03029c439a7cd19b9ad74b9548197bdeb5559e915c1f74ae19ed95'
ENDPOINT_URL = 'https://fbc0f7bc8a3bdb7d0a20307c4eaf8cde.r2.cloudflarestorage.com'
BUCKET_NAME = 'raw-video'
PUB_SUBDOMAIN = 'https://pub-8ea55317b8624238a35e5c73454b9d2d.r2.dev'

# 创建 R2 客户端
def create_r2_client():
    return boto3.client(
        's3',
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version='s3v4')
    ), BUCKET_NAME

# 构造 R2 自定义域名访问地址
def construct_custom_domain_r2_url(object_name):
    subdomain = ENDPOINT_URL.split('//')[1].split('.')[0]
    return f"https://{subdomain}.r2.dev/{object_name}"

# 构造 R2 子域名访问地址
def construct_subdomain_r2_url(object_name):
    return f"{PUB_SUBDOMAIN}/{object_name}"

# 获取相对路径（HLS 上传用）
def get_relative_path(file_path, base_folder):
    relative_path = os.path.relpath(file_path, base_folder)
    return relative_path.replace(os.sep, "/")

# 上传单个视频文件
def upload_single_video_to_r2(local_file_path):
    r2_client, bucket_name = create_r2_client()
    try:
        file_name = os.path.basename(local_file_path)
        object_name = f"videos/{file_name}"
        with open(local_file_path, 'rb') as file_data:
            r2_client.upload_fileobj(
                file_data,
                bucket_name,
                object_name,
                ExtraArgs={
                    'ACL': 'public-read',
                    'CacheControl': 'public, max-age=604800'  # CDN 缓存 7 天
                }
            )
        video_url = construct_subdomain_r2_url(object_name)
        logging.info(f"✅ 视频上传成功: {video_url}")
        return video_url
    except Exception as e:
        logging.error(f"上传失败: {e}")
        raise

# 上传 HLS 文件夹（支持递归）
def upload_hls_to_r2(local_hls_folder):
    r2_client, bucket_name = create_r2_client()
    try:
        for root, _, files in os.walk(local_hls_folder):
            for file in files:
                local_file_path = os.path.join(root, file)
                relative_path = get_relative_path(local_file_path, local_hls_folder)
                object_name = f"videos/hls/{relative_path}"

                with open(local_file_path, 'rb') as file_data:
                    r2_client.upload_fileobj(
                        file_data,
                        bucket_name,
                        object_name,
                        ExtraArgs={
                            'ACL': 'public-read',
                            'CacheControl': 'public, max-age=604800'
                        }
                    )
                logging.info(f"已上传: {object_name}")

        playlist_url = construct_subdomain_r2_url("videos/hls/playlist.m3u8")
        logging.info(f"✅ HLS 主播放列表地址: {playlist_url}")
        return playlist_url
    except Exception as e:
        logging.error(f"HLS 上传失败: {e}")
        raise

# 上传 HLS 文件夹（改用 put_object，一次性上传完整文件，避免 aws-chunked）
def upload_hls_to_r2_no_chunk(local_hls_folder):
    r2_client, bucket_name = create_r2_client()
    try:
        for root, _, files in os.walk(local_hls_folder):
            for file in files:
                local_file_path = os.path.join(root, file)
                relative_path = get_relative_path(local_file_path, local_hls_folder)
                object_name = f"videos/hls/{relative_path}"

                with open(local_file_path, 'rb') as file_data:
                    file_bytes = file_data.read()  # 一次性读取完整文件内容

                # 用 put_object 上传，避免分块上传，防止出现 aws-chunked
                r2_client.put_object(
                    Bucket=bucket_name,
                    Key=object_name,
                    Body=file_bytes,
                    ACL='public-read',
                    CacheControl='public, max-age=604800'
                )

                logging.info(f"已上传: {object_name}")

        playlist_url = construct_subdomain_r2_url("videos/hls/playlist.m3u8")
        logging.info(f"✅ HLS 主播放列表地址: {playlist_url}")
        return playlist_url
    except Exception as e:
        logging.error(f"HLS 上传失败: {e}")
        raise

# 删除指定前缀下的所有对象
def delete_folder(folder_prefix):
    r2_client, bucket_name = create_r2_client()
    response = r2_client.list_objects_v2(Bucket=bucket_name, Prefix=folder_prefix)

    if 'Contents' not in response:
        logging.info(f"📁 无需删除，未找到前缀：{folder_prefix}")
        return

    objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
    delete_response = r2_client.delete_objects(
        Bucket=bucket_name,
        Delete={'Objects': objects_to_delete}
    )
    logging.info(f"🗑️ 已删除对象: {delete_response.get('Deleted', [])}")

# 测试入口
def test():
    # 上传单个视频
    # local_file_path = "C:\\path\\to\\video.mp4"
    # upload_single_video_to_r2(local_file_path)

    #folder_to_delete = 'videos/hls/'
    #delete_folder(folder_to_delete)


    # 上传 HLS 文件夹
    hls_folder = "C:\\Users\\is99z\\PycharmProjects\\user_login2\\media\\videos\\processed\\2024\\12\\26\\hls\\194_1080p_5000"
    upload_hls_to_r2_no_chunk(hls_folder)

    # 删除特定路径下的对象

if __name__ == '__main__':
    test()
