"""Tests for boardbox.server."""
import json
from http.client import HTTPConnection

from boardbox.server import CampaignServer


def _http(srv, method, path):
    host, port = srv.address
    conn = HTTPConnection(host, port, timeout=3)
    conn.request(method, path)
    resp = conn.getresponse()
    body = resp.read().decode()
    conn.close()
    return resp.status, body


def test_health_endpoint(populated_storage):
    srv = CampaignServer(populated_storage, host="127.0.0.1", port=0)
    srv.start_background()
    try:
        status, body = _http(srv, "GET", "/health")
        assert status == 200
        assert json.loads(body).get("ok") is True
    finally:
        srv.stop()


def test_root_and_sessionbook(populated_storage):
    srv = CampaignServer(populated_storage, host="127.0.0.1", port=0)
    srv.start_background()
    try:
        assert _http(srv, "GET", "/")[0] == 200
        assert _http(srv, "GET", "/sessionbook")[0] == 200
    finally:
        srv.stop()


def test_games_list_and_filters(populated_storage):
    srv = CampaignServer(populated_storage, host="127.0.0.1", port=0)
    srv.start_background()
    try:
        status, body = _http(srv, "GET", "/games?publisher_name=italian&format=main")
        assert status == 200
        data = json.loads(body)
        assert data["count"] >= 0
    finally:
        srv.stop()


def test_game_by_id(populated_storage):
    srv = CampaignServer(populated_storage, host="127.0.0.1", port=0)
    srv.start_background()
    try:
        assert _http(srv, "GET", "/games/rec001")[0] == 200
        assert _http(srv, "GET", "/games/missing99")[0] == 404
        assert _http(srv, "GET", "/games/bad/extra")[0] == 400
    finally:
        srv.stop()


def test_campaigns_bins_favorites_tags(populated_storage):
    srv = CampaignServer(populated_storage, host="127.0.0.1", port=0)
    srv.start_background()
    try:
        for path in ("/campaigns", "/bins", "/favorites", "/tags"):
            assert _http(srv, "GET", path)[0] == 200
    finally:
        srv.stop()


def test_not_found_and_post(populated_storage):
    srv = CampaignServer(populated_storage, host="127.0.0.1", port=0)
    srv.start_background()
    try:
        assert _http(srv, "GET", "/nope")[0] == 404
        assert _http(srv, "POST", "/games")[0] == 405
        assert _http(srv, "PUT", "/games")[0] == 405
        assert _http(srv, "DELETE", "/games")[0] == 405
    finally:
        srv.stop()


def test_server_address_before_start(populated_storage):
    srv = CampaignServer(populated_storage, port=8767)
    assert srv.address == ("127.0.0.1", 8767)
