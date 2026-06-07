# Vault

> Tugas 4 II4021 Kriptografi 2026

<h3 align="center">Distributed password manager with Shamir Secret Sharing, AES-128-GCM, normal mode, backup mode, and visual recovery-share support</h3>

## Overview
`Vault` is a CLI-based distributed password manager. The application encrypts the entire vault using AES-128-GCM and protects the master key using Shamir Secret Sharing with threshold `(2,3)`. The client handles sensitive cryptographic operations, while the server only stores encrypted vault data, one server share, and supporting metadata in SQLite.

## Tech Stack and Languages
- Python 3.11+
- FastAPI
- SQLite
- `cryptography`
- `prompt_toolkit`
- `rich`
- `qrcode`
- `opencv-python-headless`
- `Pillow`
- `uv`
- `ruff`

## Authors
<div align="center">
  <table>
    <tr>
      <th>NIM</th>
      <th>Name</th>
      <th>GitHub</th>
    </tr>
    <tr align="center">
      <td>13523067</td>
      <td>Benedict Presley</td>
      <td>
        <a href="https://github.com/BP04">
          <img src="https://github.com/BP04.png" width="48" alt="BP04" /><br/>
          <sub><b>@BP04</b></sub>
        </a>
      </td>
    </tr>
    <tr align="center">
      <td>13523090</td>
      <td>Nayaka Ghana Subrata</td>
      <td>
        <a href="https://github.com/Nayekah">
          <img src="https://github.com/Nayekah.png" width="48" alt="Nayekah" /><br/>
          <sub><b>@Nayekah</b></sub>
        </a>
      </td>
    </tr>
    <tr align="center">
      <td>18223041</td>
      <td>Luckman Fakhmanidris Arvasirri</td>
      <td>
        <a href="https://github.com/Arva05">
          <img src="https://github.com/Arva05.png" width="48" alt="Arva05" /><br/>
          <sub><b>@Arva05</b></sub>
        </a>
      </td>
    </tr>
  </table>
</div>

## About Vault
`Vault` was built to satisfy the required client-server password manager workflow from the assignment specification. The main security model keeps the server in a zero-knowledge role: it never receives the master key, local share, recovery share, derived password key, or plaintext vault contents. The client supports two access flows:
- Normal mode: `local share + server share`
- Backup mode: `local share + recovery share`

The project also includes the bonus visual-cryptography flow for recovery shares by converting the recovery share into a QR code and splitting it into two visual shares.

For the visual-cryptography flow, image paths entered by the user must use absolute paths, both when saving generated visual shares and when reopening the vault from visual share images.

---
## Features
- AES-128-GCM encryption for the full vault payload
- Shamir Secret Sharing with threshold `(2,3)`
- Encrypted local share protected by a KDF-derived key from the master password
- SQLite-backed API server for encrypted vault storage
- Normal mode with live server access
- Backup mode with read-only access from encrypted local backup data
- Password entry create, update, delete, and view flows
- Automatic password generation with CSPRNG
- Bonus visual recovery share generation and reconstruction
- Environment-based configuration through `.env`
- `ruff` linting support

---
## Installation & Setup

### Requirements
- Python 3.11 or newer
- `uv` for the recommended workflow, or `venv` + `pip`
- Docker, if you want to run the server/client through containers

> [!IMPORTANT]
> If you switch between WSL/Linux and PowerShell Windows, recreate `.venv` in the shell you are currently using. Do not reuse the same `.venv` across different OS environments.

### Dependencies
The project uses these main libraries and frameworks:
- FastAPI
- cryptography
- prompt_toolkit
- rich
- qrcode
- opencv-python-headless
- Pillow

### Environment Configuration
Copy the template first:

```bash
cp .env.example .env
```

or in PowerShell:

```powershell
Copy-Item .env.example .env
```

Main configuration values include:

| Variable | Description | Default Example |
| :-- | :-- | :-- |
| `VAULT_SERVER_HOST` | Host used by the client to reach the server in local runs. | `127.0.0.1` |
| `VAULT_SERVER_BIND_HOST` | Host interface used by the server process when binding sockets. | `0.0.0.0` |
| `VAULT_SERVER_PORT` | Port used by the FastAPI server. | `5000` |
| `VAULT_SERVER_URL` | Base URL used by the client for API requests. | `http://127.0.0.1:5000` |
| `VAULT_SERVER_DB_PATH` | SQLite database path for server-side storage. | `data/server/vault.db` |
| `VAULT_CLIENT_DATA_DIR` | Directory for encrypted local share and backup vault data on the client side. | `data/client` |
| `VAULT_DOCKER_PYTHONPATH` | `PYTHONPATH` value used inside Docker containers. | `/app/src` |
| `VAULT_DOCKER_SERVER_CONTAINER` | Container name for the server service in Docker Compose. | `vault_server` |
| `VAULT_DOCKER_CLIENT_CONTAINER` | Container name for the client service in Docker Compose. | `vault_client` |
| `VAULT_DOCKER_SERVER_HOST_PORT` | Host port mapped to the server container port in Docker Compose. | `5000` |
| `VAULT_DOCKER_SERVER_URL` | Server base URL used by the client container inside the Docker network. | `http://server:5000` |
| `VAULT_DOCKER_SERVER_DATA` | Host path mounted as persistent server data volume. | `./data/server` |
| `VAULT_DOCKER_CLIENT_DATA` | Host path mounted as persistent client data volume. | `./data/client` |
| `VAULT_DOCKER_SERVER_DB_PATH` | SQLite database path used by the server container. | `data/server/vault.db` |
| `VAULT_DOCKER_CLIENT_DATA_DIR` | Client data directory used inside the client container. | `data/client` |

---
## How to Run

### Recommended: `uv`
1. Open a terminal in the project root.
2. Run:

```bash
rm -rf .venv
uv venv
uv sync
```

3. Start the server:

```bash
uv run python -m server
```

4. Open another terminal and start the client:

```bash
uv run python -m client.main
```

### Alternative: `venv` and `pip`
1. Create a virtual environment:

```bash
python -m venv .venv
```

2. Activate it:

```powershell
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the server:

```bash
python -m server
```

5. Run the client in another terminal:

```bash
python -m client.main
```

The application entry points are:
- `server`
- `client.main`

---
## Docker
Make sure `.env` already exists before using Docker Compose.

### Build
```bash
docker compose build
```

### Run Server
```bash
docker compose up -d server
```

### Run Client
```bash
docker compose run --rm client
```

---
## Linting
Run the linter with:

```bash
uv run ruff check src
```

or if you use plain `pip`:

```bash
ruff check src
```

---
## Project Structure
- `src/client` for CLI, crypto, local storage, and vault management
- `src/server` for FastAPI routes and SQLite persistence
- `src/shared` for shared config and models
- `data/client` for local encrypted share and backup vault data
- `data/server` for SQLite server storage

---
## Supported Workflows

### Vault Creation
- Input master password
- Generate random master key
- Encrypt empty vault with AES-128-GCM
- Split master key into `local share`, `server share`, and `recovery share`
- Encrypt local share with a key derived from the master password
- Store encrypted vault and server share through the server API
- If visual recovery shares are used, output image locations must be provided as absolute paths

### Normal Access
- Decrypt local share from client storage
- Fetch server share, encrypted vault, and vault nonce from the server
- Reconstruct the master key from two valid shares
- Decrypt and manage vault contents

### Backup Access
- Decrypt local share from client storage
- Input recovery share or reconstruct it from two visual shares
- Use encrypted local backup vault as the data source
- Open vault in read-only mode
- If visual recovery shares are used, both input image paths must be absolute paths

---
## Notes
- `requirements.txt` is provided for `pip` workflows.
- `pyproject.toml` is provided for `uv` workflows and project packaging.
- Dependency ranges are intentionally flexible, but still constrained for compatibility with `numpy<2` and the visual-crypto stack.

---

## Contact

If you have questions, please contact the authors:

Benedict Presley <13523067@std.stei.itb.ac.id>  
Nayaka Ghana Subrata <13523090@std.stei.itb.ac.id>  
Luckman Fakhmanidris Arvasirri <18223041@std.stei.itb.ac.id>

---

<br/>
<br/>

<div align="center">
II4021 Kriptografi • 2026 • Vault
</div>