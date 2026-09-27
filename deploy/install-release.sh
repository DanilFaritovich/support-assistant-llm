#!/bin/sh

set -eu

if [ "$#" -ne 2 ]; then
    printf 'Usage: %s <staged-directory> <deployment-directory>\n' "$0" >&2
    exit 2
fi

staged_directory=$1
deployment_directory=$2

case "$deployment_directory/" in
    *"/../"* | *"/./"* | *"//"*)
        printf 'Deployment directory contains an unsafe path component\n' >&2
        exit 2
        ;;
esac

case "$staged_directory/" in
    *"/../"* | *"/./"* | *"//"*)
        printf 'Staged directory contains an unsafe path component\n' >&2
        exit 2
        ;;
esac

case "$staged_directory" in
    "$deployment_directory"/.incoming-*) ;;
    *)
        printf 'Staged directory must be inside the deployment directory\n' >&2
        exit 2
        ;;
esac

case "$deployment_directory" in
    /opt/*) ;;
    *)
        printf 'Deployment directory must be below /opt\n' >&2
        exit 2
        ;;
esac

for required_file in \
    compose.production.yml \
    Makefile \
    deploy/production.sh \
    .env \
    .deployment.env \
    .images.env
do
    if [ ! -f "$staged_directory/$required_file" ]; then
        printf 'Staged deployment file is missing: %s\n' "$required_file" >&2
        exit 2
    fi
done

(
    cd "$staged_directory"
    sh ./deploy/production.sh validate
)

install -d -m 755 "$deployment_directory/deploy"
temporary_suffix=".incoming.$$"
temporary_files="
$deployment_directory/compose.production.yml$temporary_suffix
$deployment_directory/Makefile$temporary_suffix
$deployment_directory/deploy/production.sh$temporary_suffix
$deployment_directory/.env$temporary_suffix
$deployment_directory/.deployment.env$temporary_suffix
$deployment_directory/.images.env$temporary_suffix
"

cleanup() {
    for temporary_file in $temporary_files; do
        rm -f "$temporary_file"
    done
}
trap cleanup EXIT HUP INT TERM

install -m 644 "$staged_directory/compose.production.yml" \
    "$deployment_directory/compose.production.yml$temporary_suffix"
install -m 644 "$staged_directory/Makefile" \
    "$deployment_directory/Makefile$temporary_suffix"
install -m 755 "$staged_directory/deploy/production.sh" \
    "$deployment_directory/deploy/production.sh$temporary_suffix"
install -m 600 "$staged_directory/.env" \
    "$deployment_directory/.env$temporary_suffix"
install -m 600 "$staged_directory/.deployment.env" \
    "$deployment_directory/.deployment.env$temporary_suffix"
install -m 600 "$staged_directory/.images.env" \
    "$deployment_directory/.images.env$temporary_suffix"

mv "$deployment_directory/compose.production.yml$temporary_suffix" \
    "$deployment_directory/compose.production.yml"
mv "$deployment_directory/Makefile$temporary_suffix" \
    "$deployment_directory/Makefile"
mv "$deployment_directory/deploy/production.sh$temporary_suffix" \
    "$deployment_directory/deploy/production.sh"
mv "$deployment_directory/.env$temporary_suffix" "$deployment_directory/.env"
mv "$deployment_directory/.deployment.env$temporary_suffix" \
    "$deployment_directory/.deployment.env"
mv "$deployment_directory/.images.env$temporary_suffix" \
    "$deployment_directory/.images.env"

trap - EXIT HUP INT TERM
printf 'Staged deployment files activated\n'
