# vps Backend

Backend service of vps web-app.

To run this service simply use docker-compose
```
docker-compose build && docker-compose up
```

Миграции применяются автоматом при запуске.

Connect to api container
```
docker exec -it *your_container_id* sh
```

Generate new migrations
```
alembic revision --autogenerate -m "name"
```

После генерации нужно положить миграции в migrations/versions
достать их можно через docker cp
либо сделать cat */путь до миграций*, скопировать содержимое и вставить