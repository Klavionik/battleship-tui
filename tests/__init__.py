import os

# Override the client version for test purposes. Otherwise, snapshot tests
# will fail after every version bump, because the footer displays the version.
os.environ.setdefault("BATTLESHIP_CLIENT_VERSION", "0.0.0")
