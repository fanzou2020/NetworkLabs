import socket
import re
from urllib.parse import urlparse
import utils


def send_request(method, url, headers, verbose, body=''):
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if not url.startswith('http://'):
        url = 'http://' + url
    parsed_url = urlparse(url)

    try:
        port = 80 if parsed_url.port is None else parsed_url.port
        conn.connect((parsed_url.hostname, port))
        msg = construct_request(method, parsed_url, headers, body=body)
        conn.sendall(msg)
        response = utils.recvall(conn, buffsize=4096)
        response, status_code = construct_response(msg, response, verbose)
        if status_code.startswith(b"3"):
            re_location = re.compile(b"location: ([\s\S]*?)\r\n", re.IGNORECASE)
            new_url = re_location.findall(response)[0]
            return send_request(method, new_url.decode('ascii'), headers, verbose, body='')
        else:
            return response
    finally:
        conn.close()


def construct_response(request, response, verbose):
    status_code = response.split(b" ")[1]
    if verbose:
        response = request + b'\n\n' + response
    else:
        response = response.split(b'\r\n\r\n')[1]
    return response, status_code


# construct get request msg, encoding headers in ASCII
# read parameters from url, append headers list
def construct_request(method, parsed_url, headers, body=''):
    # print(parsed_url)
    # print(parsed_url.netloc)

    url_without_host = ''
    if parsed_url.path:
        url_without_host += parsed_url.path
    else:
        url_without_host += "/"
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
            customized_headers = utils.parse_str_list_to_dict(headers)
            http_headers.update(customized_headers)

        http_headers_str = utils.dict_to_str(http_headers)
        msg += http_headers_str
        msg += '\r\n'
        return msg.encode(encoding='ascii')

    elif method == 'post':
        msg = "POST " + url_without_host + " HTTP/1.1\r\n"
        http_headers = {'Host': parsed_url.netloc, 'User-Agent': 'httpc/1.0', 'Accept': '*/*',
                        'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': len(body)}
        if headers:
            customized_headers = utils.parse_str_list_to_dict(headers)
            http_headers.update(customized_headers)
        http_headers_str = utils.dict_to_str(http_headers)
        msg += http_headers_str
        msg += '\r\n'
        msg += body
        return msg.encode(encoding='ascii')




