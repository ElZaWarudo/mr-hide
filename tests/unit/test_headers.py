from mr_hide.proxy.headers import filter_request_headers, filter_response_headers


def test_request_headers_remove_hop_by_hop_host_and_connection_extensions() -> None:
    headers = [
        (b"Host", b"localhost"),
        (b"Connection", b"keep-alive, X-Private-Hop"),
        (b"Keep-Alive", b"timeout=5"),
        (b"X-Private-Hop", b"sentinel"),
        (b"Authorization", b"Bearer fixture"),
        (b"X-Repeated", b"first"),
        (b"X-Repeated", b"second"),
    ]

    assert filter_request_headers(headers) == (
        (b"Authorization", b"Bearer fixture"),
        (b"X-Repeated", b"first"),
        (b"X-Repeated", b"second"),
    )


def test_response_headers_remove_hop_by_hop_and_preserve_duplicates() -> None:
    headers = [
        (b"Connection", b"X-Private-Hop"),
        (b"X-Private-Hop", b"sentinel"),
        (b"Transfer-Encoding", b"chunked"),
        (b"Set-Cookie", b"a=1"),
        (b"Set-Cookie", b"b=2"),
        (b"Content-Type", b"text/event-stream"),
    ]

    assert filter_response_headers(headers) == (
        (b"Set-Cookie", b"a=1"),
        (b"Set-Cookie", b"b=2"),
        (b"Content-Type", b"text/event-stream"),
    )

