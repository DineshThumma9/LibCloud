"""Shared helpers for the backend test-suite."""

import struct
import zlib


def make_png(width, height, rows, filter_type=0):
    prev = bytes(width * 3)
    raw = b""
    for row in rows:
        current = bytes(row)
        if filter_type == 2:
            current = bytes((value - up) & 255 for value, up in zip(current, prev))
        raw += bytes([filter_type]) + current
        prev = bytes(row)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


class RecordingJobManager:
    def __init__(self):
        self.events: list[tuple[str, dict]] = []
        self.job_id = "job_test"

    async def emit(self, event_type, data):
        self.events.append((event_type, data))

    def package_events(self):
        return [data for event_type, data in self.events if event_type == "package.found"]

    def emitted_packages(self):
        packages = []
        for event in self.package_events():
            packages.extend(event["packages"])
        return packages


class FakeDepDB:
    def __init__(self, cached=None):
        self.cached = cached

    async def get_repo_deps(self, **kwargs):
        return self.cached

    async def save_repo_deps(self, **kwargs):
        return None


def make_api(cached=None):
    from app.services.scanning import GraphGithubAPI

    job_manager = RecordingJobManager()
    api = GraphGithubAPI("test_user", job_manager=job_manager)
    api.dep_db = FakeDepDB(cached)
    return api, job_manager


def manifest_nodes(*manifests):
    return {
        "repository": {
            "dependencyGraphManifests": {
                "nodes": [
                    {
                        "filename": filename,
                        "dependencies": {
                            "nodes": [{"packageName": name} for name in names]
                        },
                    }
                    for filename, names in manifests
                ]
            }
        }
    }
