import socket
from urllib.parse import urlparse


def send_request(method, url, headers, verbose, body=''):
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if not url.startswith('http://'):
        url = 'http://' + url
    parsed_url = urlparse(url)

    try:
        conn.connect((parsed_url.netloc, 80))
        msg = construct_request(method, parsed_url, headers, body=body)
        conn.sendall(msg)
        response = recvall(conn, buffsize=4096)
        return construct_response(msg, response, verbose)
    finally:
        conn.close()


def construct_response(request, response, verbose):
    if verbose:
        response = request + b'\n\n' + response
    else:
        response = response.split(b'\r\n\r\n')[1]
    return response


# construct get request msg, encoding headers in ASCII
# read parameters from url, append headers list
def construct_request(method, parsed_url, headers, body=''):
    # print(parsed_url)
    # print(parsed_url.netloc)

    url_without_host = ''
    if parsed_url.path:
        url_without_host += parsed_url.path
    if parsed_url.params:
        url_without_host += (";" + parsed_url.params)
    if parsed_url.query:
        url_without_host += ("?" + parsed_url.query)
    if parsed_url.fragment:
        url_without_host += ("#" + parsed_url.fragment)

    if method == 'get':
        msg = "GET " + url_without_host + " HTTP/1.1\r\n"

        # union default headers and customized headers
        http_headers = {'Host': parsed_url.netloc, 'User-Agent': 'httpc/1.0', 'Accept': '*/*'}
        if headers:
            customized_headers = parse_headers(headers)
            http_headers.update(customized_headers)

        http_headers_str = dict_to_str(http_headers)
        msg += http_headers_str
        msg += '\r\n'
        return msg.encode(encoding='ascii')

    elif method == 'post':
        msg = "POST " + url_without_host + " HTTP/1.1\r\n"
        http_headers = {'Host': parsed_url.netloc, 'User-Agent': 'httpc/1.0', 'Accept': '*/*',
                        'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': len(body)}
        if headers:
            customized_headers = parse_headers(headers)
            http_headers.update(customized_headers)
        http_headers_str = dict_to_str(http_headers)
        msg += http_headers_str
        msg += '\r\n'
        msg += body
        return msg.encode(encoding='ascii')


def dict_to_str(headers):
    """
    :param headers:
    :return:
    """
    msg = ""
    for k, v in headers.items():
        msg += (k + ': ' + str(v) + '\r\n')
    return msg


def parse_headers(headers):
    """
    Parse list of str to dict. e.g: ['k1:v1', 'k2:v2'] -> {k1:v1, k2:v2}
    :param headers: list of str
    :return: dict
    """
    res = dict()
    for s in headers:
        tmp = s.split(':')
        k = tmp[0]
        v = tmp[1]
        res[k] = v
    return res


def recvall(conn, buffsize):
    data = b''
    while True:
        part = conn.recv(buffsize)
        data += part
        if len(part) < buffsize:
            break
    return data
