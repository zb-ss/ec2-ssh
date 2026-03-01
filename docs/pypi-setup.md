# PyPI Publishing Setup Guide

Step-by-step instructions to enable automated PyPI publishing from GitHub releases.

## 1. Create a PyPI Account

1. Go to [https://pypi.org/account/register/](https://pypi.org/account/register/)
2. Create an account and verify your email
3. Enable 2FA (required for new projects)

## 2. Create the Project on PyPI (First-Time Only)

The first publish must be done manually to register the package name:

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Upload to PyPI (will prompt for credentials)
twine upload dist/*
```

You'll be prompted for your PyPI username and password. Use `__token__` as the username and a PyPI API token as the password (see step 3).

## 3. Create a PyPI API Token

1. Log in to [https://pypi.org](https://pypi.org)
2. Go to **Account Settings** → **API tokens**
3. Click **Add API token**
4. Set scope to **Project: ec2-ssh** (after first upload)
5. Copy the token (starts with `pypi-`)

## 4. Configure GitHub for Trusted Publishing (Recommended)

Trusted publishing uses OIDC — no tokens or secrets needed.

1. Go to [https://pypi.org/manage/project/ec2-ssh/settings/publishing/](https://pypi.org/manage/project/ec2-ssh/settings/publishing/)
2. Under **Add a new publisher**, fill in:
   - **Owner**: `zb-ss`
   - **Repository name**: `ec2-connect`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`
3. Click **Add**

Then create the GitHub environment:

1. Go to your repo → **Settings** → **Environments**
2. Click **New environment**
3. Name it `pypi`
4. (Optional) Add protection rules like required reviewers
5. Save

That's it — the `publish.yml` workflow uses `pypa/gh-action-pypi-publish` with OIDC, so no secrets are needed.

## 5. Alternative: Token-Based Publishing

If you prefer tokens over trusted publishing:

1. Create a PyPI API token (step 3)
2. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `PYPI_API_TOKEN`
5. Value: paste the `pypi-...` token
6. Then update `.github/workflows/publish.yml` — replace the publish step with:

```yaml
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

And remove the top-level `permissions: id-token: write` block.

## 6. Publishing a Release

Once set up, publishing is automatic:

1. Update the version in `pyproject.toml`:
   ```toml
   version = "2.1.0"
   ```
2. Commit and push to master
3. Go to GitHub → **Releases** → **Draft a new release**
4. Create a new tag (e.g., `v2.1.0`)
5. Write release notes
6. Click **Publish release**

The `publish.yml` workflow will:
1. Run the test suite
2. Build the package
3. Publish to PyPI via trusted publishing

## 7. Verify

After publishing, check:
- [https://pypi.org/project/ec2-ssh/](https://pypi.org/project/ec2-ssh/)
- Install: `pip install ec2-ssh` or `pipx install ec2-ssh`

## Testing with TestPyPI (Optional)

To test the workflow without publishing to the real PyPI:

1. Create an account at [https://test.pypi.org](https://test.pypi.org)
2. Set up trusted publishing there (same steps, different site)
3. Add `repository-url: https://test.pypi.org/legacy/` to the publish step
4. Install from TestPyPI: `pip install -i https://test.pypi.org/simple/ ec2-ssh`
