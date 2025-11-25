from typing import List, Optional
from ..models.banner import Banner


class BannerService:

    @staticmethod
    async def create_banner(image_url: str, title: Optional[str] = None):
        try:
            print("try mein bhi aa gaye hai laLA")
            banner = Banner(
                title=title,
                image_url=image_url
            )
            await banner.insert()
            print("banner create ho chuka hai ")
            return banner
        except Exception as e:
            print(e)
            raise e

    @staticmethod
    async def get_all_banners() -> List[Banner]:
        banners = (
            await Banner.find(Banner.is_active == True)
            .sort("+position", "-created_at")
            .to_list()
        )
        return banners

    @staticmethod
    async def get_banner_by_id(banner_id: str) -> Optional[Banner]:
        return await Banner.get(banner_id)

    @staticmethod
    async def delete_banner(banner_id: str) -> bool:
        banner = await Banner.get(banner_id)

        if not banner:
            raise ValueError("Banner not found")

        await banner.delete()
        return True

    @staticmethod
    async def toggle_banner(banner_id: str):
        banner = await Banner.get(banner_id)

        if not banner:
            raise ValueError("Banner not found")

        banner.is_active = not banner.is_active
        await banner.save()

        return banner

    @staticmethod
    async def reorder(banner_id: str, new_position: int):
        banner = await Banner.get(banner_id)
        if not banner:
            raise ValueError("Banner not found")

        banner.position = new_position
        await banner.save()

        return banner
