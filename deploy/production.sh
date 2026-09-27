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

    printf 'BACKEND_IMAGE=%s\nFRONTEND_IMAGE=%s\n' \
        "$backend_image" "$frontend_image" >"$temporary_file"
    mv "$temporary_file" .images.env
    trap - EXIT HUP INT TERM
}

read_value() {
    key=$1
    file=$2
    sed -n "s/^${key}=//p" "$file"
}

validate_images_file() {
    file=$1
    require_file "$file"

    backend_image=$(read_value BACKEND_IMAGE "$file")
    frontend_image=$(read_value FRONTEND_IMAGE "$file")
    validate_image BACKEND_IMAGE "$backend_image"
    validate_image FRONTEND_IMAGE "$frontend_image"
}

validate() {
    require_file .env
    require_file .deployment.env
    require_file .images.env
    validate_images_file .images.env
    compose config --quiet
    printf 'Production Compose config: OK\n'
}

backup_database() {
    compose run --rm --no-deps database-backup
    printf 'SQLite backup boundary: OK\n'
}

migrate() {
    compose up -d --wait --wait-timeout "$HEALTH_TIMEOUT_SECONDS" redis
    compose stop backend >/dev/null
    backup_database
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

deploy_current() {
    validate
    compose pull redis backend frontend
    migrate
    start
    health
}

deploy() {
    if [ "$#" -ne 2 ]; then
        printf 'Usage: %s deploy <backend-image@digest> <frontend-image@digest>\n' \
            "$0" >&2
        exit 2
    fi

    write_images "$1" "$2"
    deploy_current
}

mark_healthy() {
    if [ "$#" -ne 1 ]; then
        printf 'Usage: %s mark-healthy <deployment-id>\n' "$0" >&2
        exit 2
    fi

    expected_deployment_id=$1
    actual_deployment_id=$(read_value DEPLOYMENT_ID .deployment.env)
    if [ -z "$actual_deployment_id" ] || [ "$actual_deployment_id" != "$expected_deployment_id" ]; then
        printf 'Deployment ID does not match the activated runtime state\n' >&2
        exit 2
    fi

    validate
    health

    images_temporary_file=".images.last-known-good.env.tmp.$$"
    revision_temporary_file=".last-known-good-revision.tmp.$$"
    trap 'rm -f "$images_temporary_file" "$revision_temporary_file"' EXIT HUP INT TERM
    umask 077
    cp .images.env "$images_temporary_file"
    printf '%s\n' "$actual_deployment_id" >"$revision_temporary_file"
    mv "$images_temporary_file" .images.last-known-good.env
    mv "$revision_temporary_file" .last-known-good-revision
    trap - EXIT HUP INT TERM
    printf 'Last-known-good deployment recorded: %s\n' "$actual_deployment_id"
}

restore_last_known_good() {
    validate_images_file .images.last-known-good.env

    temporary_file=".images.env.tmp.$$"
    trap 'rm -f "$temporary_file"' EXIT HUP INT TERM
    umask 077
    cp .images.last-known-good.env "$temporary_file"
    mv "$temporary_file" .images.env
    trap - EXIT HUP INT TERM
    validate
    printf 'Last-known-good image references restored; services were not changed\n'
}

command=${1:-}
if [ "$#" -gt 0 ]; then
    shift
fi

case "$command" in
    deploy)
        deploy "$@"
        ;;
    deploy-current)
        if [ "$#" -ne 0 ]; then
            printf 'Usage: %s deploy-current\n' "$0" >&2
            exit 2
        fi
        deploy_current
        ;;
    mark-healthy)
        mark_healthy "$@"
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
    restore-last-known-good)
        if [ "$#" -ne 0 ]; then
            printf 'Usage: %s restore-last-known-good\n' "$0" >&2
            exit 2
        fi
        restore_last_known_good
        ;;
    *)
        printf 'Usage: %s {deploy|deploy-current|mark-healthy|migrate|health|restore-last-known-good|validate}\n' "$0" >&2
        exit 2
        ;;
esac
