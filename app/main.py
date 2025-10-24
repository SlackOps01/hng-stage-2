from fastapi import FastAPI, HTTPException, Depends, Query
from .import models
from fastapi.responses import FileResponse
from .database import get_db, engine
import httpx
from .schemas import Country
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from random import randrange
from datetime import datetime, timezone
from sqlalchemy import desc
import os
import matplotlib
import matplotlib.pyplot as plt
from sqlalchemy.sql import func



matplotlib.use("Agg")
VALID_SORTS = {"gdp_desc", "gdp_asc", "population_desc", "population_asc", "name_asc", "name_desc"}
os.makedirs("cache", exist_ok=True)

models.Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="App"
)

def generate_summary_image(db: Session):
    total_countries = db.query(models.Countries).count()
    top_countries = db.query(models.Countries)\
                     .order_by(models.Countries.estimated_gdp.desc())\
                     .limit(5)\
                     .all()
    
    top_names = [c.name for c in top_countries]
    top_gdps = [c.estimated_gdp for c in top_countries]
    last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plt.figure(figsize=(10,6))
    plt.bar(top_names, top_gdps, color='skyblue')
    plt.title(f"Top 5 Countries by Estimated GDP\nTotal Countries: {total_countries}\nLast Refresh: {last_refresh}")
    plt.ylabel("Estimated GDP")
    plt.tight_layout()
    plt.savefig("cache/summary.png")
    plt.close()

def parse_countries(country: dict, exchange_data):
    name = country['name']['common']
    try:
        capital = country.get("capital")[0]
    except:
        capital = None
    region = country['region']
    population = country['population']
    currency: dict = country['currencies']
    try:
        currency = list(currency.keys())[0]
        exchange_rate = exchange_data['rates'].get(currency)
        print(exchange_rate)
    except:
        currency = None
        exchange_rate = None
    flag_url = country['flags']['png']
    if exchange_rate is None:
        estimated_gdp = 0
    else:
        estimated_gdp = (country['population']*randrange(1000,2000)) / exchange_rate

    data = {
        "name": name,
        'capital': capital,
        'region': region,
        'population':population,
        'currency_code': currency,
        'estimated_gdp': estimated_gdp,
        'flag_url': flag_url,
        "exchange_rate": exchange_rate,
    }
    return data

@app.get("/")
def home():

    return {"message": "done"}


@app.post("/countries/refresh")
def refresh_countries(db: Session = Depends(get_db)):
    try:
        countries_resp = httpx.get(
            "https://restcountries.com/v3.1/all?fields=name,capital,region,population,currencies,flags",
            timeout=15.0,
        )
        countries_resp.raise_for_status()

        exchange_resp = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=10.0)
        exchange_resp.raise_for_status()
    except httpx.RequestError as e:
        api = "Countries" if "restcountries" in str(e) else "Exchange"
        raise HTTPException(
            status_code=503,
            detail={
                "error": "External data source unavailable",
                "details": f"Could not fetch data from {api} API",
            },
        )

    countries = countries_resp.json()
    rates = exchange_resp.json().get("rates", {})
    refresh_time = datetime.now()

    for country in countries:
        data = parse_countries(country, rates)
        if not data["name"] or not data["population"]:
            continue
        data["last_refreshed_at"] = refresh_time

        existing = db.query(models.Countries).filter(
            func.lower(models.Countries.name) == data["name"].lower()
        ).first()

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
        else:
            db.add(models.Countries(**data))

    db.commit()

    meta = db.query(models.RefreshMeta).first()
    if meta:
        meta.last_refreshed_at = refresh_time
    else:
        db.add(models.RefreshMeta(last_refreshed_at=refresh_time))
    db.commit()

    generate_summary_image(db)
    return {"message": "Cache refreshed", "refreshed_at": refresh_time.isoformat() + "Z"}
  
@app.get("/countries")
def get_countries(
    region: str | None = Query(None, description="Filter by region, e.g. Africa"),
    currency: str | None = Query(None, description="Filter by currency code, e.g. NGN"),
    sort: str = Query("gdp_desc", description="Sort by gdp_desc, gdp_asc, population_desc, population_asc, name_asc, name_desc"),
    db: Session = Depends(get_db)
):

    # Validate sort
    if sort.lower() not in VALID_SORTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort value. Must be one of {', '.join(VALID_SORTS)}"
        )

    query = db.query(models.Countries)
    # Filters
    if region:
        query = query.filter(models.Countries.region.ilike(region))
    if currency:   
        query = query.filter(models.Countries.currency_code == currency)

    # Sorting
    if sort.lower() == "gdp_desc":
        query = query.order_by(models.Countries.estimated_gdp.desc())
    elif sort.lower() == "gdp_asc":
        query = query.order_by(models.Countries.estimated_gdp.asc())
    elif sort.lower() == "population_desc":
        query = query.order_by(models.Countries.population.desc())
    elif sort.lower() == "population_asc":
        query = query.order_by(models.Countries.population.asc())
    elif sort.lower() == "name_asc":
        query = query.order_by(models.Countries.name.asc())
    elif sort.lower() == "name_desc":
        query = query.order_by(models.Countries.name.desc())

    return query.all()



@app.get("/countries/image")
def get_summary_image():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image_path = os.path.join(project_root, "cache", "summary.png")

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Summary image not found. Please refresh countries first.")
    return FileResponse(image_path, media_type="image/png")  
        
@app.get("/countries/{name}")
def get_country(name: str, db: Session = Depends(get_db)):
    name = name.lower()
    country = db.query(models.Countries).where(models.Countries.name.ilike(f"{name}")).first()
    if country is None:
        raise HTTPException(
            status_code=404,
            detail="Not found"
        )
    return country

@app.get("/status")
def get_status(db: Session = Depends(get_db)):
    countries_count = db.query(models.Countries).count()
    meta = db.query(models.RefreshMeta).first()
    last_ts = meta.last_refreshed_at.isoformat() + "Z" if meta else None
    return{
        "total_countries": countries_count,
        "last_refreshed_at":last_ts
    }

@app.delete("/countries/{name}")
def delete_country(name: str, db: Session = Depends(get_db)):
    country = db.query(models.Countries).where(models.Countries.name.ilike(f"{name}")).first()
    if country is None:
        raise HTTPException(
            status_code=404,
            detail="Not found"
        )
    db.delete(country)
    db.commit()
    return {
        "message": "deleted"
    }
