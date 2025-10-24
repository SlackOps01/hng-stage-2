from pydantic import BaseModel


class Country(BaseModel):
    name: str
    capital: str | None = None
    region: str
    population: int
    currency_code: str | None = None
    estimated_gdp: float | None = None
    exchange_rate: float | None = None
    flag_url: str

