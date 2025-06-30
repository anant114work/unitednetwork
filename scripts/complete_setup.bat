@echo off
echo 🚀 Complete Django CRM Setup
echo ================================

echo Step 1: Cleaning up old database...
if exist "db.sqlite3" del "db.sqlite3"

echo Step 2: Force creating CRM migrations...
python manage.py makemigrations crm --empty
python manage.py makemigrations crm

echo Step 3: Applying all migrations...
python manage.py migrate

echo Step 4: Setting up sample data...
python scripts/setup_database.py

echo Step 5: Creating superuser (optional)...
echo You can create a superuser manually with: python manage.py createsuperuser

echo ✅ Setup complete! You can now run: python manage.py runserver
pause
