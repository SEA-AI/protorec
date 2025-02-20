# Generic Prototype Recording APP

The app under ```main.py``` should ready for use for any of our products, with minimal changes, as long as we have a cameras (e.g. rtsp not supported), by changing the ```cameras_config.json``` file.

With default settings, the recordings appear under ```~/POWER_Data/SDCard/DataSink/prototype_recordings```

# Usage

Download MaritimeMatrix repository:

```git clone git@github.com:SEA-AI/MaritimeMatrix.git```

Copy ```OffshoreLiteRecordings/Watchkeeper/recording_app``` to the home directory of the product.

```pip install -r requeriments```

```cd recording_app```

```python3 main.py```

# Setup as a service

```
sudo nano /etc/systemd/system/recordings.service
```

```
Description=Recording App for Prototypes
After=network.target 

[Service] 
User=power
Type=simple
Environment="GENICAM_GENTL64_PATH=/opt/dart-bcon-mipi/lib"
WorkingDirectory=/home/power/recording_app
ExecStart=python3 main.py
Restart=on-failure 

[Install] 
WantedBy=multi-user.target
```

```
sudo systemctl daemon-reload
sudo systemctl start recordings
```