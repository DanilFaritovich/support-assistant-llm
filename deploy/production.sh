#!/bin/sh

set -eu

COMPOSE_FILE=${COMPOSE_FILE:-compose.production.yml}
HEALTH_TIMEOUT_SECONDS=${HEALTH_TIMEOUT_SECONDS:-120}

compose() {
    docker compose \
        --env-file .env \
        --env-file .deployment.env \
        --env-file .images.env \
        -f "$COMPOSE_FILE" \
        "$@"
}

require_file() {
    if [ ! -f "$1" ]; then
        printf 'Required deployment file is missing: %s\n' "$1" >&2
        exit 2
    fi
}

validate_image() {
    if ! printf '%s\n' "$2" | grep -Eq '^ghcr\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$'; then
        printf '%s must be an immutable GHCR digest reference\n' "$1" >&2
        exit 2
    fi
}

write_images() {
    backend_image=$1
    frontend_image=$2

    validate_image BACKEND_IMAGE "$backend_image"
    validate_image FRONTEND_IMAGE "$frontend_image"

    umask 077
    temporary_file=".images.env.tmp.$$"
    trap 'rm -f "$temporary_file"' EXIT HUP INT TERM

    if [ -f .images.env ]; then
        cp .images.env .images.previous.env
    fi

    printf 'BACKEND_IMAGE=%s\nFRONTEND_IMAGE=%s\n' \
        "$backend_image" "$frontend_image" >"$temporary_file"
    mv "$temporary_file" .images.env
    trap - EXIT HUP INT TERM
}

validate() {
    require_file .env
    require_file .deployment.env
    require_file .images.env
    compose config --quiet
    printf 'Production Compose config: OK\n'
}

migrate() {
    compose up -d --wait --wait-timeout "$HEALTH_TIMEOUT_SECONDS" redis
    compose stop backend >/dev/null
    compose up \
        --no-deps \
        --abort-on-container-exit \
        --exit-code-from migrate \
        migrate
    printf 'Database migration: OK\n'
}

start() {
    compose up -d --wait --wait-timeout "$HEALTH_TIMEOUT_SECONDS" backend frontend
    printf 'Production services: healthy\n'
}

health() {
    compose exec -T frontend \
        wget -qO- http://127.0.0.1/api/health | grep -q '"status":"ok"'
    printf 'Gateway health: OK\n'
}

deploy() {
    if [ "$#" -ne 2 ]; then
        printf 'Usage: %s deploy <backend-image@digest> <frontend-image@digest>\n' \
            "$0" >&2
        exit 2
    fi

    write_images "$1" "$2"
    validate
    compose pull redis backend frontend
    migrate
    start
    health
}

command=${1:-}
if [ "$#" -gt 0 ]; then
    shift
fi

case "$command" in
    deploy)
        deploy "$@"
        ;;
    migrate)
        validate
        migrate
        ;;
    health)
        validate
        health
        ;;
    validate)
        validate
        ;;
    *)
        printf 'Usage: %s {deploy|migrate|health|validate}\n' "$0" >&2
        exit 2
        ;;
esac
