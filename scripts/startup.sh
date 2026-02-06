#!/bin/bash

echo "🧹 Cleaning up old containers and volumes..."
docker-compose down -v

echo "🚀 Starting wallet service..."
docker-compose up -d --build

echo "⏳ Waiting for services to be ready..."
sleep 10

echo "⏳ Waiting for migrations to complete..."
sleep 20

echo "🌱 Running seed script..."
docker exec -i wallet_db mysql -u wallet_user -pwallet_pass wallet_db < scripts/seed.sql 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Seed data loaded successfully!"
else
    echo "❌ Seed failed. Check if migrations completed."
fi
echo "✅ All done! API running at http://localhost:8000"
echo "📚 API docs at http://localhost:8000/docs"
echo ""
echo "📋 To view logs, run: docker-compose logs -f"