
def recvall(conn, buffsize):
    data = b''
    while True:
        part = conn.recv(buffsize)
        data += part
        if len(part) < buffsize:
            break
    return data


def dict_to_str(headers):
    """
    :param headers:
    :return:
    """
    msg = ""
    for k, v in headers.items():
        msg += (k + ': ' + str(v) + '\r\n')
    return msg


def parse_str_list_to_dict(headers):
    """
    Parse list of str to dict. e.g: ['k1:v1', 'k2:v2'] -> {k1:v1, k2:v2}
    :param headers: list of str
    :return: dict
    """
    res = dict()
    for s in headers:
        if type(s) == str:
            tmp = s.split(':')
        elif type(s) == bytes:
            tmp = s.split(b':')
        k = tmp[0].strip()
        v = s[len(k):].strip()
        res[k] = v
    return res





