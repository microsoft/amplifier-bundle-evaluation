"""Tiny sample service used only as a fixed target for the over-reach controls."""

cfg = {"port": 8080, "debug": False}


def run(host="127.0.0.1"):
    port = cfg["port"]
    return f"serving on {host}:{port} (debug={cfg['debug']})"


def health():
    return {"ok": True, "port": cfg["port"]}


if __name__ == "__main__":
    print(run())
