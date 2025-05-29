import os
import boto3
from botocore.config import Config
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 从环境变量中读取配置

ACCESS_KEY = '8dd2b4b3cedbcd606fea84fd5cfc5b08'  # 替换为你的 Access Key
SECRET_KEY = '5014e0600f03029c439a7cd19b9ad74b9548197bdeb5559e915c1f74ae19ed95'  # 替换为你的 Secret Key
ENDPOINT_URL = 'https://fbc0f7bc8a3bdb7d0a20307c4eaf8cde.r2.cloudflarestorage.com'  # 替换为你的 R2 终端点
BUCKET_NAME = 'raw-video'  # 替换为你的存储桶名称
PUB_SUBDOMAIN = 'https://pub-8ea55317b8624238a35e5c73454b9d2d.r2.dev'

def create_r2_client():
    if not all([ENDPOINT_URL, ACCESS_KEY, SECRET_KEY, BUCKET_NAME, PUB_SUBDOMAIN]):
        raise ValueError("Environment variables are not set correctly.")

    return boto3.client(
        's3',
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version='s3v4')
    ), BUCKET_NAME


# 获取相对路径并规范化为正斜杠
def get_relative_path(file_path, base_folder):
    relative_path = os.path.relpath(file_path, base_folder)
    # 使用 os.sep 替换为 /
    return relative_path.replace(os.sep, "/")


# 构造 R2 文件的访问地址 (自定义域名)
def construct_custom_domain_r2_url(object_name):
    subdomain = ENDPOINT_URL.split('//')[1].split('.')[0]
    return f"https://{subdomain}.r2.dev/{object_name}"


# 构造 R2 文件的访问地址 (子域名)
def construct_subdomain_r2_url(object_name):
    return f"{PUB_SUBDOMAIN}/{object_name}"


# 上传单个视频文件到 R2，并返回访问地址
def upload_single_video_to_r2(local_file_path):
    r2_client, bucket_name = create_r2_client()

    try:
        # 获取文件名
        file_name = os.path.basename(local_file_path)  # 提取文件名
        object_name = f"videos/{file_name}"  # 在 R2 中存储的路径

        # 上传文件
        with open(local_file_path, 'rb') as file_data:
            r2_client.upload_fileobj(file_data, bucket_name, object_name, ExtraArgs={'ACL': 'public-read'})

        # 构造文件的访问地址
        video_url = construct_subdomain_r2_url(object_name)
        logging.info(f"Video uploaded successfully: {video_url}")
        return video_url  # 返回视频的访问地址
    except Exception as e:
        logging.error(f"Failed to upload video: {e}")
        raise Exception(f"上传失败: {e}")

import boto3

# 替换为你的实际信息
ACCOUNT_ID = 'your-account-id'
ACCESS_KEY_ID = 'your-access-key-id'
SECRET_ACCESS_KEY = 'your-secret-access-key'
BUCKET_NAME = 'your-bucket-name'

# 初始化 boto3 client
def get_r2_client():
    return boto3.client(
        's3',
        endpoint_url=f'https://{ACCOUNT_ID}.r2.cloudflarestorage.com',
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=SECRET_ACCESS_KEY
    )

# 删除指定 prefix 的所有对象
def delete_folder(folder_prefix):
    # 列出所有匹配的对象
    r2_client, bucket_name = create_r2_client()
    bucket_name = 'raw-video'
    print(bucket_name)
    response = r2_client.list_objects_v2(
        Bucket="raw-video",
        Prefix=folder_prefix
    )

    if 'Contents' not in response:
        print(f"No objects found with prefix: {folder_prefix}")
        return

    # 准备删除请求
    objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]

    # 执行批量删除
    delete_response = r2_client.delete_objects(
        Bucket=bucket_name,
        Delete={'Objects': objects_to_delete}
    )

    print("Deleted objects:", delete_response.get('Deleted', []))
# 上传 HLS 流文件到 R2
def upload_hls_to_r2(local_hls_folder):
    r2_client, bucket_name = create_r2_client()

    try:
        # 遍历本地 HLS 文件夹中的所有文件
        for root, _, files in os.walk(local_hls_folder):
            for file in files:
                local_file_path = os.path.join(root, file)
                relative_path = get_relative_path(local_file_path, local_hls_folder)
                object_name = f"videos/hls/{relative_path}"  # 在 R2 中存储的路径

                # 上传文件
                with open(local_file_path, 'rb') as file_data:
                    r2_client.upload_fileobj(file_data, bucket_name, object_name)

        # 构造播放列表文件的访问地址
        playlist_file = "playlist.m3u8"  # 假设主播放列表文件名为 playlist.m3u8
        playlist_object_name = f"videos/hls/{playlist_file}"
        playlist_custom_domain_url = construct_custom_domain_r2_url(playlist_object_name)
        playlist_subdomain_url = construct_subdomain_r2_url(playlist_object_name)

        logging.info(f"HLS playlist uploaded successfully: {playlist_subdomain_url}")
        return playlist_custom_domain_url, playlist_subdomain_url  # 返回播放列表文件的访问地址
    except Exception as e:
        logging.error(f"Failed to upload HLS files: {e}")
        raise Exception(f"上传失败: {e}")


def test():
    local_file_path = "C:\\Users\\is99z\\Downloads\\WOS_crawler-main.zip"
    #print(upload_single_video_to_r2(local_file_path))

    hls_folder = "C:\\Users\\is99z\\PycharmProjects\\user_login2\\media\\videos\\processed\\2024\\12\\26\\hls\\194_1080p_5000"
    #custom_domain_url, subdomain_url = upload_hls_to_r2(hls_folder)
    #print(f"Custom Domain URL: {custom_domain_url}")
    #print(f"Subdomain URL: {subdomain_url}")

    folder_to_delete = 'videos/hls/ts/'  # 注意结尾的斜杠，确保只删这个“文件夹”
    delete_folder(folder_to_delete)
test()



