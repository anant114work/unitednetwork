#!/bin/bash
# Delete corrupted database
rm -f db.sqlite3
echo "Database deleted. Run migrations to create a new one."
