"""
DigitalOcean Spaces storage service for file uploads
"""

import boto3
import uuid
from datetime import datetime
from typing import Optional, Tuple
from PIL import Image
import io
from botocore.exceptions import ClientError, NoCredentialsError

from ..config import settings


class StorageService:
    """Service for handling file uploads to DigitalOcean Spaces"""

    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.DO_SPACES_ENDPOINT,
            aws_access_key_id=settings.DO_SPACES_KEY,
            aws_secret_access_key=settings.DO_SPACES_SECRET,
            region_name=settings.DO_SPACES_REGION,
        )
        print("DO_SPACES_ENDPOINT =", settings.DO_SPACES_ENDPOINT)
        print("DO_SPACES_CDN_ENDPOINT =", settings.DO_SPACES_CDN_ENDPOINT)
        print("DO_SPACES_BUCKET =", settings.DO_SPACES_BUCKET)

        self.bucket_name = settings.DO_SPACES_BUCKET
        self.cdn_endpoint = (
            settings.DO_SPACES_CDN_ENDPOINT or settings.DO_SPACES_ENDPOINT
        )

    def _generate_file_path(self, file_type: str, original_filename: str) -> str:
        """Generate a unique file path for upload"""
        timestamp = datetime.now().strftime("%Y/%m/%d")
        file_extension = (
            original_filename.split(".")[-1] if "." in original_filename else ""
        )
        unique_id = str(uuid.uuid4())

        if file_extension:
            return f"{file_type}/{timestamp}/{unique_id}.{file_extension}"
        else:
            return f"{file_type}/{timestamp}/{unique_id}"

    # def _get_public_url(self, file_path: str) -> str:
    #     """Get the public URL for a file"""
    #     if self.cdn_endpoint:
    #         return f"{self.cdn_endpoint}/{self.bucket_name}/{file_path}"
    #     return f"{settings.DO_SPACES_ENDPOINT}/{self.bucket_name}/{file_path}"
    def _get_public_url(self, file_path: str) -> str:
        return f"{self.cdn_endpoint}/{file_path}"


    async def upload_file(
        self,
        file_content: bytes,
        original_filename: str,
        file_type: str = "images",
        content_type: Optional[str] = None,
    ) -> Tuple[str, dict]:
        """
        Upload a file to DigitalOcean Spaces

        Args:
            file_content: The file content as bytes
            original_filename: Original name of the file
            file_type: Type of file (images, pdfs, documents, etc.)
            content_type: MIME type of the file

        Returns:
            Tuple of (public_url, metadata)
        """
        try:
            file_path = self._generate_file_path(file_type, original_filename)

            # Determine content type if not provided
            if not content_type:
                if original_filename.lower().endswith((".jpg", ".jpeg")):
                    content_type = "image/jpeg"
                elif original_filename.lower().endswith(".png"):
                    content_type = "image/png"
                elif original_filename.lower().endswith(".gif"):
                    content_type = "image/gif"
                elif original_filename.lower().endswith(".webp"):
                    content_type = "image/webp"
                elif original_filename.lower().endswith(".pdf"):
                    content_type = "application/pdf"
                else:
                    content_type = "application/octet-stream"

            # Upload to DigitalOcean Spaces
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=file_content,
                ContentType=content_type,
                ACL="public-read",  # Make file publicly accessible
            )
            # inside upload handler, after upload or before put_object
            print("UPLOAD generated file_path:", file_path)

            public_url = self._get_public_url(file_path)

            # Generate metadata
            metadata = {
                "url": public_url,
                "file_path": file_path,
                "original_filename": original_filename,
                "file_size": len(file_content),
                "content_type": content_type,
                "uploaded_at": datetime.now().isoformat(),
            }

            return public_url, metadata

        except NoCredentialsError:
            raise Exception("DigitalOcean Spaces credentials not configured")
        except ClientError as e:
            raise Exception(f"Failed to upload file: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error during upload: {str(e)}")

    async def upload_image(
        self,
        file_content: bytes,
        original_filename: str,
        max_width: int = 1920,
        max_height: int = 1080,
        quality: int = 85,
    ) -> Tuple[str, dict]:
        """
        Upload and optimize an image file

        Args:
            file_content: The image file content as bytes
            original_filename: Original name of the file
            max_width: Maximum width for resizing
            max_height: Maximum height for resizing
            quality: JPEG quality (1-100)

        Returns:
            Tuple of (public_url, metadata)
        """
        try:
            # Open and process image
            image = Image.open(io.BytesIO(file_content))
            original_width, original_height = image.size

            # Convert to RGB if necessary (for JPEG)
            if image.mode in ("RGBA", "LA", "P"):
                # Create a white background
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(
                    image, mask=image.split()[-1] if image.mode == "RGBA" else None
                )
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            # Resize if necessary
            if original_width > max_width or original_height > max_height:
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # Save optimized image
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True)
            optimized_content = output.getvalue()

            # Upload optimized image
            return await self.upload_file(
                optimized_content, original_filename, "images", "image/jpeg"
            )

        except Exception as e:
            # If image processing fails, upload original file
            return await self.upload_file(file_content, original_filename, "images")

    async def upload_pdf(
        self, file_content: bytes, original_filename: str
    ) -> Tuple[str, dict]:
        """
        Upload a PDF file

        Args:
            file_content: The PDF file content as bytes
            original_filename: Original name of the file

        Returns:
            Tuple of (public_url, metadata)
        """
        return await self.upload_file(
            file_content, original_filename, "pdfs", "application/pdf"
        )

    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from DigitalOcean Spaces

        Args:
            file_path: The file path in the bucket

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError as e:
            print(f"Error deleting file {file_path}: {str(e)}")
            return False
        except Exception as e:
            print(f"Unexpected error deleting file {file_path}: {str(e)}")
            return False

    async def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Get information about a file

        Args:
            file_path: The file path in the bucket

        Returns:
            File metadata or None if not found
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name, Key=file_path
            )
            return {
                "size": response["ContentLength"],
                "content_type": response["ContentType"],
                "last_modified": response["LastModified"].isoformat(),
                "etag": response["ETag"],
            }
        except ClientError:
            return None
        except Exception as e:
            print(f"Error getting file info for {file_path}: {str(e)}")
            return None
        
    # async def list_files(self, prefix: str = "") -> list[dict]:
    #     """
    #     List all files in a given prefix (folder)

    #     Args:
    #         prefix: Folder path prefix (e.g. "pdfs/2025/09/19/")

    #     Returns:
    #         List of files with metadata
    #     """
    #     try:
    #         # print(f"DEBUG: listing prefix={prefix}")
    #         print("Bucket name:", self.bucket_name)
    #         print("Prefix:", prefix)
    #         response = self.s3_client.list_objects_v2(
    #         Bucket=self.bucket_name,   # sirf bucket name
    #         Prefix=prefix,             # yahan par bucket repeat mat karna
    #     )
    #         print("Raw S3 response:", response)  # 👈 yeh add kar
    #         return response.get("Contents", [])
    #         print(f"DEBUG: raw response={response}")

    #         files = []
    #         for obj in response.get("Contents", []):
    #             files.append({
    #                 "name": obj["Key"].split("/")[-1],   # sirf filename
    #                 "path": obj["Key"],                  # pura path
    #                 "url": self._get_public_url(obj["Key"]),  # yahan sahi URL banega
    #                 "last_modified": obj["LastModified"].isoformat(),
    #                 "size": obj["Size"],
    #             })

    #         return files   # yeh hona chahiye
    #     except ClientError as e:
    #         print(f"Error listing files with prefix {prefix}: {str(e)}")
    #         return []
    #     except Exception as e:
    #         print(f"Unexpected error listing files: {str(e)}")
    #         return []
    
    async def list_files(self, prefix: str = "") -> list[dict]:
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                # 👇 prefix hata do filhaal
                # Prefix=prefix,
            )

            print("ALL OBJECTS IN BUCKET:")
            if "Contents" not in response:
                print("  (empty)")
                return []

            for obj in response["Contents"]:
                print(" -", obj["Key"])

            return []
        except Exception as e:
            print("REAL ERROR in list_files:", type(e), e)
            return []











# Global instance
storage_service = StorageService()
