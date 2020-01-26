## File Uploads with AIOHTTP

# Device Setup

Reverse proxy port `8000` to the server.

```bash
adb reverse tcp:8000 tcp:800
```

Make a bunch of files to test with.

```bash
adb shell truncate -s 1000000000 /data/local/tmp/large.bin
adb shell truncate -s 500000 /data/local/tmp/small.bin
adb shell truncate -s 900 /data/local/tmp/tiny.bin
```
