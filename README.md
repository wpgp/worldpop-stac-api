# WorldPop STAC API

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0+-blue.svg)](https://fastapi.tiangolo.com)
[![STAC](https://img.shields.io/badge/STAC-1.0.0-blue.svg)](https://stacspec.org)

A specialized STAC API implementation for accessing WorldPop geospatial datasets, built on top of [stac-fastapi](https://github.com/stac-utils/stac-fastapi).

## Features

- Full implementation of the STAC API specification v1.0.0
- MongoDB backend for efficient data storage and retrieval
- Advanced filtering capabilities with CQL2 support
- Customized for WorldPop datasets with specialized metadata
- Built-in caching mechanisms for improved performance
- Comprehensive API documentation via Swagger/OpenAPI
- Both sync and async client interfaces
- Support for field filtering, sorting, and pagination
- Country-specific data access through ISO 3166-1 alpha-3 codes

## Installation

### From Source

```bash
git clone https://github.com/wpgp/worldpop-stac-api
cd worldpop-stac-api
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/wpgp/worldpop-stac-api
cd worldpop-stac-api
pip install -e ".[dev]"
```

## Using as a Python Package

### Basic Usage

```python
from wpstac import WorldPopSTAC

# Initialize the client
stac = WorldPopSTAC()

# Async context usage
async def get_collections():
    # Get all collections
    collections = await stac.get_collections()
    return collections

# Get specific collection
async def get_population_data(country_code: str):
    collection = await stac.get_collection(f"pop_{country_code.lower()}")
    return collection

# Search for items
async def search_items(bbox=None, datetime=None):
    items = await stac.search_items(
        collections=["population"],
        bbox=bbox,
        datetime=datetime,
        limit=10
    )
    return items
```

### Custom Settings

```python
from wpstac import Settings, WorldPopSTAC

# Configure custom settings
settings = Settings(
    mongodb_host="custom-host",
    mongodb_port=27017,
    mongodb_dbname="stac_db",
    cache_ttl=1800,
    enable_response_models=True
)

# Initialize with custom settings
stac = WorldPopSTAC(settings=settings)
```

## Using as an API Server

### Quick Start

1. Set up your environment:
```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your configuration
nano .env
```

2. Run the server:
```bash
python -m wpstac.app
```

### Using Docker

```bash
# Build the image
docker build -t worldpop-stac-api .

# Run the container
docker run -p 8000:8000 \
  --env-file .env \
  worldpop-stac-api
```

### API Endpoints

The API provides the following main endpoints:

- `GET /` - Landing page with API information
- `GET /conformance` - API conformance classes
- `GET /collections` - List all collections
- `GET /collections/{collection_id}` - Get collection details
- `GET /collections/{collection_id}/items` - List items in collection
- `GET /collections/{collection_id}/items/{item_id}` - Get specific item
- `GET /search` - Search items with filtering
- `POST /search` - Advanced search with JSON body

### Example API Requests

```bash
# Get available collections
curl http://localhost:8000/collections

# Get items from a specific collection
curl http://localhost:8000/collections/pop_gbr/items

# Search with parameters
curl "http://localhost:8000/search?collections=population&bbox=-10,50,2,60&datetime=2020-01-01/2021-01-01"
```

### Advanced Search Example

```bash
# POST search with CQL2 filter
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "collections": ["population"],
    "limit": 10,
    "filter": {
      "op": "and",
      "args": [
        {
          "op": ">=",
          "args": [{"property": "year"}, "2020"]
        },
        {
          "op": "s_intersects",
          "args": [
            {"property": "geometry"},
            {
              "type": "Polygon",
              "coordinates": [[[-10, 50], [2, 50], [2, 60], [-10, 60], [-10, 50]]]
            }
          ]
        }
      ]
    }
  }'
```

## Configuration

### Environment Setup

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit the `.env` file according to your needs.

### Required Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| MONGODB_HOST | MongoDB host | localhost | Yes |
| MONGODB_PORT | MongoDB port | 27017 | Yes |
| MONGODB_DB | Database name | stac_worldpop_db | Yes |
| MONGODB_USERNAME | MongoDB username | None | No |
| MONGODB_PASSWORD | MongoDB password | None | No |

### Optional Settings

| Variable | Description | Default |
|----------|-------------|---------|
| APP_HOST | API host | 127.0.0.1 |
| APP_PORT | API port | 8000 |
| RELOAD | Enable hot reload | false |
| UVICORN_ROOT_PATH | Base path for the API | "" |
| USE_CACHE | Enable caching | true |
| CACHE_TTL | Cache time-to-live (seconds) | 3600 |
| ENABLE_RESPONSE_MODELS | Enable pydantic validation | true |

### API Extensions

Available extensions:
- Fields (`/search?fields=id,properties.datetime`)
- Filter (CQL2 filtering support)
- Sort (`/search?sortby=datetime`)
- Query (Property-based filtering)

Enable/disable extensions using the `ENABLED_EXTENSIONS` environment variable:
```bash
export ENABLED_EXTENSIONS=query,sort,fields,filter
```

### Documentation

API documentation is available at:
- Swagger UI: http://localhost:8000/api.html
- OpenAPI JSON: http://localhost:8000/api

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes 
4. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.