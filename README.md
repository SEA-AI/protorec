# ProtoRec

ProtoRec is a Flask-based web application for managing audio and video recordings with GStreamer, designed specifically for early-stage prototypes and experimental hardware.

## 🚀 Features

- 📹 **Record and monitor** live sessions
- 💾 **Track storage usage** effectively
- 📷 **Monitor sensors** such as cameras and IMUs

## 📋 Requirements

- **Python 3.8+**
- **GStreamer** with necessary plugins
- **JavaScript-enabled modern web browser**
- [**UV Python package manager**](https://docs.astral.sh/uv/getting-started/installation/) (for development)

## ⚙️ Quick Start

Download the latest wheel from the [releases page](https://github.com/SEA-AI/protorec/releases).

1. Install the wheel:

```bash
sudo pip3 install /path/to/protorec-<version>-py3-none-any.whl
```

### 👨‍💻 Manual start

1. Launch the web app:

```bash
protorec-app --config /absolute/path/to/your_config.json --recdir /absolute/path/to/your_recordings_dir
```

2. Go to `http://<your-server-ip>:5000` on your browser.

### 🐧 Start on Boot

1. Install linux service:

```bash
sudo protorec-service --config /absolute/path/to/your_config.json --recdir /absolute/path/to/your_recordings_dir
```

2. Go to `http://<your-server-ip>:5000` on your browser.

<details>
<summary>Something went wrong?</summary>

1. Check service status:

```bash
sudo systemctl status protorec
```

2. Check service logs:

```bash
sudo journalctl -u protorec -f
```

3. Stop service:

```bash
sudo systemctl stop protorec
```

</details>

## 💪 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

- **Pre-commit Hooks:** Use [pre-commit hooks](https://pre-commit.com/) to maintain code quality.
- **Style Guide:** Follow guidelines enforced via `ruff` and run checks before committing.

1. Install pre-commit hooks:

```bash
uvx pre-commit install
```

2. Run Ruff for linting and auto-fixes:

```bash
uvx ruff check --fix
```

3. Add dependencies using UV:

```bash
uv add <package-name>
uv add <package-name>@<version>
uv sync  # Syncs dependencies from pyproject.toml
```
