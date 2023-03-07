import requests_mock

from fixieai import agents


def test_embed_http_uri():
    with requests_mock.Mocker() as m:
        m.get("http://example.com/image.jpg", content=b"fake bytes")
        embed = agents.Embed(
            content_type="image/jpeg", uri="http://example.com/image.jpg"
        )
        assert embed.content_type == "image/jpeg"
        assert embed.uri == "http://example.com/image.jpg"
        assert embed.content == b"fake bytes"


def test_embed_data_uri():
    embed = agents.Embed(
        content_type="text/plain", uri="data:base64,SGVsbG8sIFdvcmxkIQ=="
    )
    assert embed.content_type == "text/plain"
    assert embed.content == b"Hello, World!"
    assert embed.text == "Hello, World!"

    embed.content = b"Goodbye, World!"
    assert embed.text == "Goodbye, World!"
    assert embed.uri == "data:base64,R29vZGJ5ZSwgV29ybGQh"
