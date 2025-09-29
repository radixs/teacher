#!/usr/bin/env bash
set -euo pipefail

COMMAND=${1:-run}
COMPOSE=${COMPOSE:-docker compose}

run_tests() {
  echo "[test] validating docker compose manifest"
  $COMPOSE -f docker-compose.yml config >/dev/null

  echo "[test] running backend feature tests"
  $COMPOSE run --rm backend php artisan test --env=testing

  echo "[test] running rag-orchestrator pytest suite"
  $COMPOSE run --rm rag-orchestrator pytest app/tests -q

  echo "[test] running search-agent scrape tests"
  $COMPOSE run --rm search-agent pytest app/tests -q

  echo "[test] building frontend (acts as smoke/e2e placeholder)"
  $COMPOSE run --rm frontend npm run build -- --mode production

  echo "[test] tests completed"
}

run_lint() {
  echo "[lint] placeholder lint aggregator"
  echo "[lint] add eslint/php-cs-fixer/etc. invocations here"
}

case "$COMMAND" in
  run)
    run_tests
    ;;
  lint)
    run_lint
    ;;
  *)
    echo "Unknown command: $COMMAND" >&2
    exit 1
    ;;
esac
