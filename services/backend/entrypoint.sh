#!/usr/bin/env bash
set -euo pipefail

cd /var/www/html

if [ ! -f .env ]; then
  cp .env.example .env
fi

if [ ! -f vendor/autoload.php ]; then
  composer install --no-interaction --prefer-dist
fi

php artisan key:generate --force

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

PORT=${BACKEND_INTERNAL_PORT:-8080}
exec php artisan serve --host=0.0.0.0 --port="${PORT}"
