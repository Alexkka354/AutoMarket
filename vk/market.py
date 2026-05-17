import aiohttp
from config import VK_TOKEN, VK_GROUP_ID

VK_API = "https://api.vk.com/method"
VERSION = "5.131"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def get_upload_server() -> str | None:
    if not VK_TOKEN or not VK_GROUP_ID:
        print("❌ VK_TOKEN или VK_GROUP_ID не заполнены в .env")
        return None
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "group_id":    str(VK_GROUP_ID),
                "access_token": str(VK_TOKEN),
                "v":           VERSION,
            }
            async with session.post(
                f"{VK_API}/photos.getMarketAlbumUploadServer",
                params=params
            ) as resp:
                data = await resp.json()
                if "response" not in data:
                    print(f"❌ VK upload server error: {data}")
                    return None
                return data["response"]["upload_url"]
    except Exception as e:
        print(f"❌ Ошибка получения upload server: {e}")
        return None


async def _download_image(photo_url: str) -> bytes | None:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept":     "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                photo_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
                ssl=False   # отключаем SSL верификацию для проблемных сайтов
            ) as resp:
                if resp.status != 200:
                    print(f"⚠ Фото вернуло статус {resp.status}: {photo_url}")
                    return None
                return await resp.read()
    except Exception as e:
        print(f"⚠ Ошибка скачивания фото: {e}")
        return None


async def upload_photo(photo) -> int | None:
    if isinstance(photo, bytes):
        photo_data = photo
    else:
        photo_data = await _download_image(photo)

    if not photo_data:
        return None

    upload_url = await get_upload_server()
    if not upload_url:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field(
                "file", photo_data,
                filename="photo.jpg",
                content_type="image/jpeg"
            )
            async with session.post(upload_url, data=form) as resp:
                upload_result = await resp.json()
                print(f"Upload result: {upload_result}")

            params = {
                "group_id":    str(VK_GROUP_ID),
                "photo":       upload_result["photo"],
                "server":      str(upload_result["server"]),
                "hash":        upload_result["hash"],
                "access_token": str(VK_TOKEN),
                "v":           VERSION,
            }
            async with session.post(
                f"{VK_API}/photos.saveMarketAlbumPhoto",
                params=params
            ) as resp:
                save_result = await resp.json()
                print(f"Save result: {save_result}")
                if "response" not in save_result:
                    print(f"❌ Ошибка сохранения фото: {save_result}")
                    return None
                return save_result["response"][0]["id"]
    except Exception as e:
        print(f"❌ Ошибка загрузки фото в VK: {e}")
        return None


async def add_product(
    title:       str,
    description: str,
    price:       float,
    photo_url=None,
    category_id: int = 1,
) -> dict:
    async with aiohttp.ClientSession() as session:
        main_photo_id = None

        if photo_url:
            main_photo_id = await upload_photo(photo_url)
            if main_photo_id:
                print(f"✅ Фото загружено, ID: {main_photo_id}")
            else:
                print(f"⚠ Публикуем без фото: {title}")

        params = {
            "owner_id":     f"-{VK_GROUP_ID}",
            "name":         title[:100],
            "description":  description,
            "category_id":  str(category_id),
            "price":        str(int(price)), 
            "access_token": str(VK_TOKEN),
            "v":            VERSION,
        }
        if main_photo_id:
            params["main_photo_id"] = str(main_photo_id)

        async with session.post(
            f"{VK_API}/market.add", params=params
        ) as resp:
            return await resp.json()


async def get_products() -> dict:
    async with aiohttp.ClientSession() as session:
        params = {
            "owner_id":     f"-{VK_GROUP_ID}",
            "access_token": str(VK_TOKEN),
            "v":            VERSION,
            "count":        "50",
        }
        async with session.post(
            f"{VK_API}/market.get", params=params
        ) as resp:
            return await resp.json()


async def delete_product(item_id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        params = {
            "owner_id":     f"-{VK_GROUP_ID}",
            "item_id":      str(item_id),
            "access_token": str(VK_TOKEN),
            "v":            VERSION,
        }
        async with session.post(
            f"{VK_API}/market.delete", params=params
        ) as resp:
            return await resp.json()