from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re
from datetime import datetime
from num2words import num2words

CADASTRE_REGEX = re.compile(r'^\d{2}:\d{2}:\d{6,7}:\d+$')


def format_money_rus(amount: float) -> str:
    rub = int(amount)
    kop = int(round((amount - rub) * 100))
    rub_formatted = f"{rub:,}".replace(",", " ")
    rub_words = num2words(rub, lang='ru')
    kop_words = num2words(kop, lang='ru')
    return f"{rub_formatted} руб. {kop:02d} коп. ({rub_words} рублей {kop_words} копеек)"


class CadastreRequest(BaseModel):
    cad_num: str = Field(..., description="Кадастровый номер в формате XX:XX:XXXXXX:XX")

    @field_validator('cad_num')
    @classmethod
    def validate_cad_num(cls, v: str) -> str:
        if not CADASTRE_REGEX.match(v):
            raise ValueError("Неверный формат кадастрового номера. Пример: 77:03:0001001:1")
        return v


class CadastreResponse(BaseModel):
    cn: Optional[str] = Field(None, description="Кадастровый номер")
    address: Optional[str] = Field(None, description="Адрес")
    area_gkn: Optional[str] = Field(None, description="Площадь по ГКН (с единицей измерения)")
    category_type: Optional[str] = Field(None, description="Категория земель")
    util_code: Optional[str] = Field(None, description="Код вида использования")
    util_by_doc: Optional[str] = Field(None, description="Вид использования по документу")
    cad_cost: Optional[str] = Field(None, description="Кадастровая стоимость (форматированная)")
    date_create: Optional[str] = Field(None, description="Дата создания записи")
    date_update: Optional[str] = Field(None, description="Дата обновления")
    coordinates: Optional[List[List[float]]] = Field(None, description="Координаты полигона участка")

    @field_validator("area_gkn", mode="before")
    @classmethod
    def format_area(cls, v):
        if v is None:
            return None
        v_str = str(v).strip()
        if v_str.endswith("м²") or v_str.endswith("м^2"):
            return v_str.replace("м^2", "м²")
        try:
            return f"{float(v):,.2f}".replace(",", " ") + " м²"
        except Exception:
            return v_str + " м²"

    @field_validator("cad_cost", mode="before")
    @classmethod
    def format_cad_cost(cls, v):
        if v is None:
            return None
        try:
            return format_money_rus(float(v))
        except Exception:
            return str(v)

    @field_validator("date_create", "date_update", mode="before")
    @classmethod
    def format_dates(cls, v):
        if not v:
            return None
        try:
            dt = datetime.fromisoformat(v)
        except ValueError:
            try:
                dt = datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                return v
        return dt.strftime("%d-%m-%Y")

    class Config:
        from_attributes = True