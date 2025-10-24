import httpx
import json
from random import randrange

# url = "https://restcountries.com/v3.1"

# data = httpx.get(f"{url}/name/nigeria")

with open("file.json", "r") as json_file:
    data_json = json.loads(json_file.read())

with open("exc.json", "r") as exc_file:
    country_data = json.loads(exc_file.read())

name = data_json[0]['name']['common']
capital = data_json[0]["capital"][0]
region = data_json[0]['region']
population = data_json[0]['population']
currencies_dict: dict = data_json[0]['currencies']
currency = list(currencies_dict.keys())[0]
exchange_rate = country_data['rates'][currency]
estimated_gdp = int(population) * randrange(1000,2000)/exchange_rate
flag_url = data_json[0]['flags']['png']



print(name)
print(capital)
print(region)
print(currency)
print(exchange_rate)
print(estimated_gdp)
print(flag_url)