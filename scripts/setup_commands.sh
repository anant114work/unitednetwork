#!/bin/bash
# Setup commands for United Network CRM

echo "🚀 Setting up United Network CRM..."
echo "=================================="

# Step 1: Delete old database if exists
echo "Step 1: Cleaning old database..."
if [ -f "db.sqlite3" ]; then
    rm db.sqlite3
    echo "✅ Old database deleted"
else
    echo "ℹ️ No existing database found"
fi

# Step 2: Create migrations
echo "Step 2: Creating migrations..."
python manage.py makemigrations

# Step 3: Apply migrations
echo "Step 3: Applying migrations..."
python manage.py migrate

# Step 4: Create superuser and sample data
echo "Step 4: Setting up sample data..."
python scripts/setup_database.py

# Step 5: Collect static files
echo "Step 5: Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Setup completed successfully!"
echo ""
echo "🔑 Login Credentials:"
echo "Admin: +919999999999 / admin123"
echo "CP: +919876543210 / cp123"
echo "RM: +919876543220 / team123"
echo ""
echo "🌐 Start server with: python manage.py runserver"
