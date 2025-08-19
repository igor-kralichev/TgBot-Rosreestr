import logging
from fastapi import FastAPI, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from models import CadastreRequest, CadastreResponse
import httpx

# Настройка логирования и инициализация приложения
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Cadastre API",
    description="API для получения информации по кадастровому номеру из Росреестра",
    version="1.0.0"
)

limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Асинхронная функция для получения данных из внешнего API НСПД
async def fetch_cadastre_object(cad_num: str) -> dict:
    url = "https://nspd.gov.ru/api/geoportal/v2/search/geoportal"
    params = {
        "query": cad_num,
        "thematicSearchId": 1
    }

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            json_data = response.json()
            return json_data.get("data")
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error while fetching cadastre data: {exc.response.status_code}")
            raise HTTPException(status_code=exc.response.status_code, detail="Ошибка при запросе к внешнему API.")
        except Exception as exc:
            logger.error(f"Unexpected error: {exc}")
            raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера.")

# Эндпоинт для получения данных по кадастровому номеру
@app.get("/cadastre/{cad_num}", response_model=CadastreResponse, summary="Получить данные по кадастровому номеру")
@limiter.limit("20/minute")
async def get_cadastre(request: Request, cad_num: str) -> CadastreResponse:
    try:
        CadastreRequest(cad_num=cad_num)
    except ValueError as e:
        logger.warning(f"Неверный формат: {cad_num}")
        raise HTTPException(status_code=400, detail=str(e))

    data = await fetch_cadastre_object(cad_num)

    if not data or not data.get('features'):
        logger.info(f"Объект не найден: {cad_num}")
        raise HTTPException(status_code=404, detail="Объект не найден.")

    feature = data['features'][0]
    props = feature.get('properties', {})
    options = props.get('options', {})

    response = CadastreResponse(
        cn=options.get("cad_num") or props.get("descr"),
        address=options.get("readable_address"),
        area_gkn=options.get("specified_area"),
        category_type=props.get("categoryName"),
        util_code=None,
        util_by_doc=options.get("permitted_use_established_by_document"),
        cad_cost=options.get("cost_value"),
        date_create=options.get("cost_determination_date"),
        date_update=props.get("systemInfo", {}).get("updated"),
        coordinates=feature.get('geometry', {}).get('coordinates', [[]])[0]
    )

    logger.info(f"Успешный запрос для {cad_num}")
    return response

# Точка входа для запуска приложения
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)