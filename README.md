# Top 300 Czech/Slovak Movies Search

A Django application for searching a database of the top 300 movies from the Czech-Slovak website CSFD.cz.

## 📋 Project Description

The application provides a web interface for searching movies and actors from the top-300 best-rated films. It supports case-insensitive and diacritic-insensitive search, as well as substring matching.

### Key Features:
- **Screen 1**: Search for movies and actors by title/name
- **Screen 2**: List of actors in a selected movie
- **Screen 3**: List of movies featuring a selected actor

## 🏗️ Architecture

### Data Models:
- `Film` – stores information about movies  
- `Actor` – stores information about actors  
- `MovieActor` – many-to-many relationship between movies and actors

### Key Highlights:
- Text normalization for effective searching  
- Indexed fields for fast querying  
- Atomic transactions during data saving

## 🚀 Installation and Running

### 1. Clone the Repository
```bash
git clone https://github.com/dmytro72/movie_search.git
cd movie_search
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 4. Set Up Django
```bash
# Apply migrations
python manage.py migrate

# Create a superuser (optional)
python manage.py createsuperuser
```

### 5. Start the Development Server
```bash
python manage.py runserver
```

The application will be available at: http://127.0.0.1:8000/

## 🔧 Management Commands

### Load Data from CSFD.cz
```bash
# Load top 300 movies (default)
python manage.py load_top_movies

# Load a specific number of movies
python manage.py load_top_movies --limit 50

# Command help
python manage.py load_top_movies --help
```

**Note**: The command introduces delays between requests (1–3 seconds) to comply with scraping etiquette.

## 🧪 Testing

### Run Tests
```bash
# Run all tests
pytest
```

### Pytest Configuration
Located in `pytest.ini`:
- Uses a test database

## 📁 Project Structure

```
movie_search/
├── movies/                         # Main app
│   ├── management/
│   │   └── commands/
│   │       └── load_top_movies.py  # Data loading command
│   ├── templates/movies/           # HTML templates
│   │   ├── base.html
│   │   ├── search.html
│   │   ├── film_detail.html
│   │   └── actor_detail.html
│   ├── models.py                   # Data models
│   ├── views.py                    # Views (controllers)
│   ├── urls.py                     # URL routes
│   ├── admin.py                    # Admin panel
│   └── utils.py                    # Utilities (normalize function)
├── movie_search/                   # Project settings
│   ├── settings.py
│   └── urls.py
├── requirements.txt                # Python dependencies
├── pytest.ini                      # Test configuration
└── README.md
```

## 🎯 API Endpoints

### Web Interface
- `GET /` – Main search page  
- `GET /search/?q=<query>` – Search for movies and actors  
- `GET /film/<id>/` – Movie details  
- `GET /actor/<id>/` – Actor details  

### API (JSON)
- `GET /api/search/?q=<query>` – Search via API

## ⚡ Performance

### Optimizations:
- Indexes on normalized fields for faster searches  
- API result limit (50 entries)  
- Efficient SQL queries with minimal DB hits
