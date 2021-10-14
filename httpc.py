import argparse
import httplib

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="httpc", add_help=False, usage="python httpc.py (get|post) [options...] URL")

    # positional arguments
    parser.add_argument("method", help="get or post method", type=str.lower, choices=['get', 'post'])
    parser.add_argument("URL", help="URL", type=str)

    # optional arguments
    parser.add_argument("--help", action="help", help="show this help message and exit")
    parser.add_argument("-v", "--verbose", help="verbosity mode", action="store_true")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-d", "--data", help="inline data", type=str)
    group.add_argument("-f", "--file", help="read from file", type=str)

    parser.add_argument("-o", "--output", help="output to file", type=str)

    parser.add_argument("-h", "--header", help="header", type=str, action="append")

    args = parser.parse_args()
    url = args.URL
    headers = args.header

    response = ""
    if args.method == 'get':
        if args.data or args.file:
            print("Cannot use '-d' or '-f' in GET method")
            exit(1)
        response = httplib.send_request('get', url, headers, verbose=args.verbose)

    if args.method == 'post':
        body = ''
        if args.data:
            body = args.data
        elif args.file:
            filename = args.file
            with open(filename, 'r') as f:
                body = str.strip(f.read())
        response = httplib.send_request('post', url, headers, verbose=args.verbose, body=body)

    if args.output:
        with open(args.output, "w") as fo:
            fo.write(response.decode('ascii'))
    else:
        print(response.decode('ascii'))




