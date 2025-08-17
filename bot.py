import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.enums import ChatAction
import aiohttp
from models import CadastreResponse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
API_URL = os.getenv('API_URL', 'http://localhost:8000')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в секретах или .env файле.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start_handler(message: types.Message) -> None:
    await message.reply("Привет! Отправь кадастровый номер в формате XX:XX:XXXXXX:XX (например, 77:03:0001001:1).")


@dp.message(Command("stop"))
async def stop_handler(message: types.Message) -> None:
    await message.reply("Бот остановлен. Для возобновления работы отправьте /start")


@dp.message()
async def message_handler(message: types.Message) -> None:
    cad_num = message.text.strip()

    # Отправляем индикатор загрузки
    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
    loading_message = await message.reply("Подождите, идёт получение данных с сервера НСПД...")

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{API_URL}/cadastre/{cad_num}"
            async with session.get(url, timeout=10) as response:
                if response.status == 400:
                    error = await response.json()
                    await message.reply(error.get('detail', 'Неверный формат.'))
                    await bot.delete_message(chat_id=message.chat.id, message_id=loading_message.message_id)
                    return
                if response.status == 404:
                    await message.reply("Объект не найден.")
                    await bot.delete_message(chat_id=message.chat.id, message_id=loading_message.message_id)
                    return
                if response.status != 200:
                    raise ValueError(f"API вернул статус {response.status}")

                data = await response.json()
                info = CadastreResponse(**data)

            # Формируем ссылку на карту НСПД
            x_coords = [point[0] for point in info.coordinates]
            y_coords = [point[1] for point in info.coordinates]
            center_x = sum(x_coords) / len(x_coords)
            center_y = sum(y_coords) / len(y_coords)
            map_url = (f"https://nspd.gov.ru/map?thematic=PKK&zoom=20&"
                       f"coordinate_x={center_x}&coordinate_y={center_y}&baseLayerId=235&theme_id=1&active_layers=36048")

            reply = (
                f"Кадастровый номер: {info.cn or 'Не указан'}\n\n"
                f"Адрес: {info.address or 'Не указан'}\n\n"
                f"Площадь (ГКН): {info.area_gkn or 'Не указана'}\n\n"
                f"Категория земель: {info.category_type or 'Не указана'}\n\n"
                f"Вид использования: {info.util_code or 'Не указан'} ({info.util_by_doc or 'Не указано'})\n\n"
                f"Кадастровая стоимость: {info.cad_cost or 'Не указана'}\n\n"
                f"Дата создания: {info.date_create or 'Не указана'}\n\n"
                f"Дата обновления: {info.date_update or 'Не указана'}\n\n"
                f"Ссылка на карту НСПД: {map_url}"
            )

            await bot.delete_message(chat_id=message.chat.id, message_id=loading_message.message_id)
            await message.reply(reply)

        logger.info(f"Успешный запрос для {cad_num} от {message.from_user.id}")

    except aiohttp.ClientError as e:
        logger.error(f"Ошибка сети при запросе к API: {e}")
        await bot.delete_message(chat_id=message.chat.id, message_id=loading_message.message_id)
        await message.reply("Ошибка соединения с сервером. Попробуйте позже.")
    except ValueError as e:
        logger.error(f"Ошибка в ответе API: {e}")
        await bot.delete_message(chat_id=message.chat.id, message_id=loading_message.message_id)
        await message.reply("Ошибка в данных. Проверьте номер.")
    except Exception as e:
        logger.exception(f"Неожиданная ошибка: {e}")
        await bot.delete_message(chat_id=message.chat.id, message_id=loading_message.message_id)
        await message.reply("Произошла неизвестная ошибка.")


async def main() -> None:
    logger.info("Бот запущен.")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())