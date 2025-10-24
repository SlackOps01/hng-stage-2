from fastapi import FastAPI, HTTPException, Depends, Query
from .import models
from fastapi.responses import FileResponse
from .database import get_db, engine
import httpx
from .schemas import Country
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from random import randrange
from datetime import datetime
from sqlalchemy import desc
import os
import matplotlib


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
    matplotlib.pyplot.figure(figsize=(10,6))
    matplotlib.pyplot.bar(top_names, top_gdps, color='skyblue')
    matplotlib.pyplot.title(f"Top 5 Countries by Estimated GDP\nTotal Countries: {total_countries}\nLast Refresh: {last_refresh}")
    matplotlib.pyplot.ylabel("Estimated GDP")
    matplotlib.pyplot.tight_layout()
    matplotlib.pyplot.savefig("cache/summary.png")
    matplotlib.pyplot.close()

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
        estimated_gdp = None
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
        "last_refreshed_at":datetime.now()
    }
    return data

@app.get("/")
def home():

    return {"message": "done"}


@app.post("/countries/refresh")
def refresh_countries(db: Session = Depends(get_db)):

    data = httpx.get("https://restcountries.com/v3.1/all?fields=name,capital,region,population,currencies,flags")
    exchange_data = httpx.get("https://open.er-api.com/v6/latest/USD")
    exchange_data = exchange_data.json()
    data_json =  data.json()
    for country in data_json:
        data = parse_countries(country, exchange_data)
        new_country = models.Countries(**data)
        db.add(new_country)
        try:   
            db.commit()

        
        except IntegrityError:
            db.rollback()
            print(f"skipping {country['name']}")
    generate_summary_image(db)
    return {"message": "done"} 

@app.get("/countries")
def get_countries(
    region: str | None = Query(None, description="Filter by region, e.g. Africa"),
    currency: str | None = Query(None, description="Filter by currency code, e.g. NGN"),
    sort: str = Query("gdp_desc", description="Sort by gdp_desc, gdp_asc, population_desc, population_asc, name_asc, name_desc"),
    db: Session = Depends(get_db)
):
    # Manual validation for required fields
    missing = {}
    if not region:
        missing["region"] = "is required"
    if not currency:
        missing["currency"] = "is required"
    if missing:
        raise HTTPException(status_code=400, detail={"error": "Validation failed", "details": missing})

    # Validate sort
    if sort.lower() not in VALID_SORTS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort value. Must be one of {', '.join(VALID_SORTS)}"
        )

    query = db.query(models.Countries)
    # Filters
    query = query.filter(models.Countries.region.ilike(region))
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
    country = db.query(models.Countries).where(models.Countries.name==name).first()
    if country is None:
        raise HTTPException(
            status_code=404,
            detail="Not found"
        )
    return country

@app.get("/status")
def get_status(db: Session = Depends(get_db)):
    countries_count = db.query(models.Countries).count()
    last_timestamp = db.query(models.Countries).order_by(desc(models.Countries.last_refreshed_at)).first().last_refreshed_at
    return{
        "count": countries_count,
        "last_timestamp":last_timestamp
    }

@app.delete("/countries/{name}")
def delete_country(name: str, db: Session = Depends(get_db)):
    name = name.lower()
    country = db.query(models.Countries).where(models.Countries.name==name).first()
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

@app.get("/countries/image")
def get_summary_image():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image_path = os.path.join(project_root, "cache", "summary.png")

    if not os.path.exists(image_path):
        return {"error":"Summary image not found"}
    return FileResponse(image_path, media_type="image/png")