import os
import asyncio
from typing import Literal


class AssetStore:

    def __init__(self):
        self.provider: Literal["r2", "s3", "local"] = os.getenv("ASSET_STORE_PROVIDER", "local")
        self.bucket = os.getenv("ASSET_STORE_BUCKET", "ad-machine-assets")
        self.endpoint = os.getenv("ASSET_STORE_ENDPOINT", "")
        self.access_key = os.getenv("ASSET_STORE_ACCESS_KEY", "")
        self.secret_key = os.getenv("ASSET_STORE_SECRET_KEY", "")
        self.public_base_url = os.getenv("ASSET_STORE_PUBLIC_BASE_URL", "")
        self._s3_client = None

    async def upload(self, data: bytes, key: str, content_type: str = "image/png") -> str:
        if self.provider == "local":
            return await self._upload_local(data, key)
        return await asyncio.get_event_loop().run_in_executor(
            None, self._upload_s3_sync, data, key, content_type
        )

    def _upload_s3_sync(self, data: bytes, key: str, content_type: str) -> str:
        import boto3
        from botocore.config import Config

        if self._s3_client is None:
            kwargs = dict(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(signature_version="s3v4"),
            )
            if self.endpoint:
                kwargs["endpoint_url"] = self.endpoint
            self._s3_client = boto3.client("s3", **kwargs)

        self._s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

        base = self.public_base_url.rstrip("/") if self.public_base_url else f"https://{self.bucket}.s3.amazonaws.com"
        return f"{base}/{key}"

    async def _upload_local(self, data: bytes, key: str) -> str:
        import aiofiles
        local_dir = os.getenv("LOCAL_ASSET_DIR", "/tmp/ad-machine-assets")
        path = os.path.join(local_dir, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return f"file://{path}"

    async def get_url(self, key: str) -> str:
        if self.public_base_url:
            return f"{self.public_base_url.rstrip('/')}/{key}"
        return f"file://{os.path.join(os.getenv('LOCAL_ASSET_DIR', '/tmp/ad-machine-assets'), key)}"
