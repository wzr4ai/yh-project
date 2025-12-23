from minio import Minio
from datetime import timedelta

client = Minio(
    'fnos.dfwzr.com:9000',
    access_key='minioadmin',
    secret_key='minioe5nkp53m',
    secure=False
)

# 生成预签名URL
url = client.presigned_get_object(
    'yhvideos',
    'yh_videos/020_67acf6b4-fc69-4e1a-a2d2-b67343b3860f_0.mp4',
    expires=timedelta(days=7)
)

print(url)