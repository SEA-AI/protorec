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

1. Install dependencies:


```bash
sudo apt-get install libcairo-dev
sudo apt-get install libgirepository1.0-dev
uv sync
```

2. Run the development server:

```bash
uv run protorec-app
```

or

```bash
uv run python3 app.py
```

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

## 🛠️ Production Deployment

ProtoRec is optimized for reliable hardware interaction with a single-worker architecture.

1. Install the Python package:

```bash
pip install https://github.com/SEA-AI/protorec/releases/download/v0.1.0/protorec-0.1.0-py3-none-any.whl
```

2. Run the application:

```bash
protorec-app
```

## 👨🏻‍🔧 Setup as a service

```
sudo nano /etc/systemd/system/recordings.service
```

```
Description=Recording App for Prototypes
After=network.target

[Service]
User=lite
Type=simple
Environment="GENICAM_GENTL64_PATH=/opt/dart-bcon-mipi/lib"
WorkingDirectory=/home/lite/
ExecStart=/home/lite/.local/bin/protorec-app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```
sudo systemctl daemon-reload
sudo systemctl enable recordings
sudo systemctl start recordings
```
