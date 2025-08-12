import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
import aiohttp
from models import CadastreResponse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загружаем переменные окружения (для совместимости с .env в разработке)
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_URL = os.getenv('API_URL', 'http://localhost:8000')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в секретах или .env файле.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Старт
@dp.message(CommandStart())
async def start_handler(message: types.Message) -> None:
    await message.reply("Привет! Отправь кадастровый номер в формате XX:XX:XXXXXX:XX (например, 77:03:0001001:1).")

# Стоп
@dp.message(Command("stop"))
async def stop_handler(message: types.Message) -> None:
    await message.reply("Бот остановлен. Для возобновления работы отправьте /start")

# Поиск по кадастровому номеру
@dp.message()
async def message_handler(message: types.Message) -> None:
    cad_num = message.text.strip()

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/cadastre/{cad_num}"
            async with session.get(url, timeout=10) as response:
                if response.status == 400:
                    error = await response.json()
                    await message.reply(error.get('detail', 'Неверный формат.'))
                    return
                if response.status == 404:
                    await message.reply("Объект не найден.")
                    return
                if response.status != 200:
                    raise ValueError(f"API вернул статус {response.status}")

                data = await response.json()

        info = CadastreResponse(**data)

        reply = (
            f"Кадастровый номер: {info.cn or 'Не указан'}\n\n"
            f"Адрес: {info.address or 'Не указан'}\n\n"
            f"Площадь (ГКН): {info.area_gkn or 'Не указана'}\n\n"
            f"Категория земель: {info.category_type or 'Не указана'}\n\n"
            f"Вид использования: {info.util_code or 'Не указан'} ({info.util_by_doc or 'Не указано'})\n\n"
            f"Кадастровая стоимость: {info.cad_cost or 'Не указана'}\n\n"
            f"Дата создания: {info.date_create or 'Не указана'}\n\n"
            f"Дата обновления: {info.date_update or 'Не указана'}"
        )

        await message.reply(reply)
        logger.info(f"Успешный запрос для {cad_num} от {message.from_user.id}")

    except aiohttp.ClientError as e:
        logger.error(f"Ошибка сети при запросе к API: {e}")
        await message.reply("Ошибка соединения с сервером. Попробуйте позже.")
    except ValueError as e:
        logger.error(f"Ошибка в ответе API: {e}")
        await message.reply("Ошибка в данных. Проверьте номер.")
    except Exception as e:
        logger.exception(f"Неожиданная ошибка: {e}")
        await message.reply("Произошла неизвестная ошибка.")

async def main() -> None:
    logger.info("Бот запущен.")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())