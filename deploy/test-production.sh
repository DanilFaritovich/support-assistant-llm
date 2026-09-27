#!/bin/sh

set -eu

project_directory=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
test_directory=$(mktemp -d)
trap 'rm -rf "$test_directory"' EXIT HUP INT TERM

mkdir -p "$test_directory/bin" "$test_directory/work"
cp "$project_directory/deploy/production.sh" "$test_directory/work/production.sh"
touch "$test_directory/work/compose.production.yml"
printf 'ENVIRONMENT=production\n' >"$test_directory/work/.env"
printf 'DEPLOYMENT_ID=test-revision\n' >"$test_directory/work/.deployment.env"

old_backend=ghcr.io/example/backend@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
old_frontend=ghcr.io/example/frontend@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
new_backend=ghcr.io/example/backend@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
new_frontend=ghcr.io/example/frontend@sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd

printf 'BACKEND_IMAGE=%s\nFRONTEND_IMAGE=%s\n' \
    "$old_backend" "$old_frontend" >"$test_directory/work/.images.env"
cp "$test_directory/work/.images.env" \
    "$test_directory/work/.images.last-known-good.env"
cp "$test_directory/work/.images.last-known-good.env" \
    "$test_directory/expected-last-known-good.env"

cat >"$test_directory/bin/docker" <<'EOF'
#!/bin/sh
case " $* " in
    *" up --no-deps --abort-on-container-exit --exit-code-from migrate migrate "*)
        if [ "${FAIL_MIGRATION:-0}" -eq 1 ]; then
            exit 1
        fi
        ;;
    *" exec -T frontend "*)
        printf '{"status":"ok"}\n'
        ;;
esac
EOF
chmod +x "$test_directory/bin/docker"

if (
    cd "$test_directory/work"
    PATH="$test_directory/bin:$PATH" FAIL_MIGRATION=1 \
        sh ./production.sh deploy "$new_backend" "$new_frontend"
); then
    printf 'Expected the simulated migration failure\n' >&2
    exit 1
fi

cmp "$test_directory/expected-last-known-good.env" \
    "$test_directory/work/.images.last-known-good.env"

(
    cd "$test_directory/work"
    PATH="$test_directory/bin:$PATH" \
        sh ./production.sh mark-healthy test-revision
)

cmp "$test_directory/work/.images.env" \
    "$test_directory/work/.images.last-known-good.env"
grep -qx 'test-revision' "$test_directory/work/.last-known-good-revision"

printf 'Deployment state regression checks: OK\n'
