# setup.sh - Script for quick project startup
#!/bin/bash

echo "🚀 Setting up the Movie Search project..."

# Creating a virtual environment
echo "📦 Creating virtual environment..."
python -m venv movie_search_env

# Activating the virtual environment
echo "🔧 Activating virtual environment..."
source movie_search_env/bin/activate  # Linux/Mac
# movie_search_env\Scripts\activate     # Windows

# Installing dependencies
echo "📋 Installing dependencies..."
pip install -r requirements.txt
pip install -r requirements-test.txt

# Creating a superuser (optional)
echo "👤 Creating superuser..."
python manage.py createsuperuser

# Starting the development server
echo "🌐 Starting development server..."
python manage.py runserver

echo "✅ Project is ready! Open http://127.0.0.1:8000 in your browser"
