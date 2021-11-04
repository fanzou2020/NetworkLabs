import socket
import argparse
import threading
from datetime import datetime

import utils
import os


class HttpFs:
    def __init__(self, host, port, root_path):
        self.host = host
        # self.root_path = root_path
        self.root_path = os.path.abspath(root_path)
        self.port = port
        print(os.path.abspath(root_path))

    def run_server(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            listener.bind((self.host, self.port))
            listener.listen(5)
            print('Echo server is listening at ', self.port)
            while True:
                conn, addr = listener.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()
        finally:
            listener.close()

    def handle_client(self, conn, addr):
        print('New client from', addr)
        try:
            data = utils.recvall(conn, 4096)

            # split request into header and body
            header_str = data.split(b'\r\n\r\n')[0].strip()
            body_str = data[len(header_str):].strip()

            # parse header string to a dictionary
            header = self.parse_header(header_str)
            print(header)
            print(body_str)

            msg = b""
            status = 0
            if header[b'method'].lower() == b'get':
                status, msg = self.handle_get_request(header, body_str)

            elif header[b'method'].lower() == b'post':
                status, msg = self.handle_post_request(header, body_str)

            print("msg is :")
            print(msg)
            print("status code is " + str(status))

            response = self.make_http_response(status, msg)
            print(response)

            conn.sendall(response)

        finally:
            conn.close()


    def handle_get_request(self, header, body_str):
        path = header[b'path']
        if path == b'/':
            return 200, os.listdir(self.root_path)
        else:
            file_path = os.path.abspath(self.root_path + path)
            if not self.is_safe_path(file_path):
                return 400, b"Bad Request, cannot access files outside of directory!"

            try:
                with open(file_path, 'r') as f:
                    content = f.read().encode('ascii')
                    return 200, content
            except FileNotFoundError:
                return 404, b"File does not exist"


    def handle_post_request(self, header, body_str):
        path = header[b'path']
        if path == b'/':
            return 400, b"Bad request, please provide a file name!"

        else:
            file_path = os.path.abspath(self.root_path + path)
            if not self.is_safe_path(file_path):
                return 400, b"Bad Request, cannot access files outside of directory!"

            try:
                with open(file_path, 'w') as f:
                    f.write(body_str.decode('ascii'))
                    return 200, b"Write to file success!"
            except OSError:
                return 500, b"Write to file failed!"


    def make_http_response(self, status, msg):
        result = b""
        http_version = b'HTTP/1.1'
        status_msg = b""
        if status == 200:
            status_msg = b"200 OK"
        elif status == 400:
            status_msg = b"400 Bad Request"
        elif status == 404:
            status_msg = b"404 Not Found"
        elif status == 500:
            status_msg = b"500 Internal Server Error"
        result += (http_version + b" " + status_msg + b"\r\n")

        datetime_str = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT").encode("ascii")
        result += (b"Date: " + datetime_str + b"\r\n")
        result += (b"Content-Type: " + b"text/plain\r\n")
        result += (b"Content-Length: " + str(len(msg)).encode('ascii') + b"\r\n")
        result += b"Connection: keep-alive\r\n"
        result += b"Server: httpfs\r\n"
        result += b"Access-Control-Allow-Origin: *\r\n"
        result += b"Access-Control-Allow-Credentials: true\r\n"
        result += b"\r\n"

        result += msg

        return result


    def is_safe_path(self, path):
        return self.root_path == os.path.commonpath((self.root_path, path))


    def list_filenames(self):
        return os.listdir(self.root_path)


    @staticmethod
    def parse_header(header_str):
        """
        Parse the header str received from request into a dictionary
        :param header_str: header string
        :return: header dict
        """
        # print(header_str)
        header = dict()
        lines = header_str.split(b'\r\n')

        tmp = lines[0].split(b' ')
        header[b'method'] = tmp[0]
        header[b'path'] = tmp[1]
        header[b'http_version'] = tmp[2]

        header_kv = utils.parse_str_list_to_dict(lines[1:])

        header.update(header_kv)
        # print(header)
        return header


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", help="port number of server", type=int, default=8080)
    parser.add_argument("-d", "--directory", help="root path of this file server", type=bytes, default=b"FileServer/")
    args = parser.parse_args()

    fs = HttpFs("", args.port, args.directory)
    fs.run_server()
