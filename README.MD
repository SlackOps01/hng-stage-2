# Country Data API

## Overview
This project provides a REST API for retrieving country data including GDP estimates, population statistics, and other key metrics. The application fetches real-time data from external APIs and maintains a local database for efficient querying.

live at https://hng-stage-2-production.up.railway.app/

## Features
- Real-time country data fetching from REST APIs
- Database storage with SQLAlchemy ORM
- GDP estimation calculations
- Image generation for summary statistics
- Filtering and sorting capabilities

## Prerequisites
- Python 3.7+
- MySQL database
- pip

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/SlackOps01/hng-stage-2.git
cd hng-stage-2.git
```

### 2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
venv\Scripts\activate    # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.env` file in the project root with:
```env
MYSQL_USERNAME="your_mysql_username"
MYSQL_PASSWORD="your_mysql_password"
MYSQL_HOST="your_mysql_host"
MYSQL_PORT="your_mysql_port"
```


This will initialize the database schema and populate it with country data.

## Running the Application

### Development Server
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

### Production Deployment
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Country Data
- `GET /countries` - List countries with filtering and sorting
- `GET /countries/{name}` - Get specific country by name
- `POST /countries/refresh` - Refresh country data from external APIs
- `DELETE /countries/{name}` - Delete country from database
- `GET /countries/image` - Get summary statistics image

### Status
- `GET /status` - Get database status information

## Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| MYSQL_USERNAME | Database username | root |
| MYSQL_PASSWORD | Database password | your_password |
| MYSQL_HOST | Database host | examplehost |
| MYSQL_PORT | Database port | 3306 |

## Dependencies


1. fastapi[all]
2. uvicorn
3. sqlalchemy
4. pymysql
5. cryptography
6. matplotlib



## Data Refresh
The application  fetches fresh data from:
- https://restcountries.com/v3.1/all
- https://open.er-api.com/v6/latest/USD

## Image Generation
The `/countries/image` endpoint generates PNG images showing top 5 countries by estimated GDP. These images are cached in the `cache/` directory.

