#!/usr/bin/env bash
# setup_github_runner.sh
# Registers a self-hosted GitHub Actions runner on this machine.
# Run ONCE manually after creating the repo on GitHub.
#
# Usage:
#   chmod +x scripts/setup_github_runner.sh
#   GITHUB_REPO=irvingfarinas/gcp-bigquery-agent \
#   RUNNER_TOKEN=<token from GitHub Settings > Actions > Runners> \
#   bash scripts/setup_github_runner.sh

set -euo pipefail

RUNNER_VERSION="2.319.1"
RUNNER_DIR="${HOME}/actions-runner"
GITHUB_REPO="${GITHUB_REPO:?Set GITHUB_REPO=owner/repo}"
RUNNER_TOKEN="${RUNNER_TOKEN:?Set RUNNER_TOKEN from GitHub repo Settings > Actions > Runners}"
RUNNER_NAME="${RUNNER_NAME:-$(hostname)-local}"
RUNNER_LABELS="${RUNNER_LABELS:-self-hosted,macOS,local}"

echo "==> Creating runner directory: $RUNNER_DIR"
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

echo "==> Downloading GitHub Actions runner v${RUNNER_VERSION}"
ARCH="osx-arm64"
if [[ "$(uname -m)" == "x86_64" ]]; then
  ARCH="osx-x64"
fi
curl -sL "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-${ARCH}-${RUNNER_VERSION}.tar.gz" \
  | tar xz

echo "==> Configuring runner for repo: https://github.com/${GITHUB_REPO}"
./config.sh \
  --url "https://github.com/${GITHUB_REPO}" \
  --token "${RUNNER_TOKEN}" \
  --name "${RUNNER_NAME}" \
  --labels "${RUNNER_LABELS}" \
  --work "_work" \
  --unattended \
  --replace

echo ""
echo "==> Runner configured. To start it in the foreground:"
echo "    cd ${RUNNER_DIR} && ./run.sh"
echo ""
echo "==> To install as a launchd service (runs on login):"
echo "    cd ${RUNNER_DIR} && sudo ./svc.sh install && sudo ./svc.sh start"
