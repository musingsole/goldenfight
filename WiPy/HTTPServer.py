import _thread
import socket
from network import WLAN
from sys import print_exception


not_configured_response = """HTTP/1.1 404 Not Found
Content-Type: text/html
Connection: close
Server: edaphic

Endpoint not found"""


success = """HTTP/1.1 200 OK
Content-Type: text/html
Connection: close
Access-Control-Allow-Origin: *
Server: edaphic

Successful Operation
"""


failure = """HTTP/1.1 502 OK
Content-Type: text/html
Connection: close
Access-Control-Allow-Origin: *
Server: edaphic

Operation Failed
"""


MAX_HTTP_MESSAGE_LENGTH = 2048


def unquote(s):
    """unquote('abc%20def') -> b'abc def'."""
    # Note: strings are encoded as UTF-8. This is only an issue if it contains
    # unescaped non-ASCII characters, which URIs should not.
    if not s:
        return b''

    if isinstance(s, str):
        s = s.encode('utf-8')

    bits = s.split(b'%')
    if len(bits) == 1:
        return s

    res = [bits[0]]
    append = res.append

    # Build cache for hex to char mapping on-the-fly only for codes
    # that are actually used
    hextobyte_cache = {}
    for item in bits[1:]:
        try:
            code = item[:2]
            char = hextobyte_cache.get(code)
            if char is None:
                char = hextobyte_cache[code] = bytes([int(code, 16)])
            append(char)
            append(item[2:])
        except KeyError:
            append(b'%')
            append(item)

    return b''.join(res)


def parse_querystring(qs):
    parameters = {}
    ampersandSplit = qs.split("&")
    for element in ampersandSplit:
        equalSplit = element.split("=")
        parameters[equalSplit[0]] = unquote(equalSplit[1].replace("+", " ")).decode()

    return parameters


def set_wlan_to_access_point(
    ssid="wipy_https_server",
    password="micropython",
    host_ip="192.168.4.1",
    log=lambda msg: None
):
    log("Creating Access Point {} with password {}".format(ssid, password))
    wlan = WLAN()
    wlan.deinit()
    wlan.ifconfig(config=(host_ip, '255.255.255.0', '0.0.0.0', '8.8.8.8'))
    wlan.init(mode=WLAN.AP, ssid=ssid, auth=(WLAN.WPA2, password), channel=5, antenna=WLAN.INT_ANT)

    return wlan


def http_daemon(path_to_handler={},
                error_response=failure,
                threading=True,
                port=80,
                lock=None,
                log=print):
    s = socket.socket()
    s.bind(('0.0.0.0', port))

    s.listen(5)
    while lock is None or not lock.locked():
        conn, address = s.accept()

        try:
            log('New connection from {}'.format(address))
            conn.setblocking(False)

            msg = conn.recv(MAX_HTTP_MESSAGE_LENGTH).decode()
            msg = msg.replace("\r\n", "\n")

            log("Received MSG:\n{}".format(msg))

            if msg == '(null)':
                conn.send(success)
                conn.close()
                continue

            blank_line_split = msg.split('\n\n')
            if 'favicon' in blank_line_split[0]:
		conn.send(success)
                conn.close()
                continue
		
            if len(blank_line_split) == 1:
                msg += "\n\n"
            elif len(blank_line_split) > 2:
                print("Unexpected blank_line_split length: {}".format(len(blank_line_split)))
                raise Exception("Malformated HTTP request.")
            
        except Exception as e:
            log("Request initial processing failure")
            print_exception(e)
            conn.send(failure)
            conn.close()

        if threading:
            log("Spawn thread to handle message")
            _thread.start_new_thread(process_message_and_response, (msg, conn, path_to_handler, error_response, log))
        else:
            process_message_and_response(msg, conn, path_to_handler, error_response, log)
 

def process_message_and_response(
    message,
    conn,
    path_to_handler={},
    error_response=failure,
    log=print
):
    log("Processing message:\n{}".format(message))
    try:
        blank_line_split = message.split('\n\n')
        preamble = blank_line_split[0].split("\n")
        request = preamble[0]
        request_keys = ["method", "path", "version"]
        request_key_value = zip(request_keys, request.split(" "))
        request = {key: value for key, value in request_key_value}

        headers = preamble[1:]
        headers = {line.split(":")[0].strip(): line.split(":")[1].strip() for line in headers}

        for key, value in headers.items():
            request[key] = value

        if 'path' not in request:
            raise Exception("Invalid Request")

        split_path = request['path'].split("?")
        request['path'] = split_path[0]
        if len(split_path) > 1:
            request['query_parameters'] = split_path[1]

        log("Received Request:\n{}".format(request))

        request['body'] = blank_line_split[1]
        content_length = 0
        if 'Content-Length' in request:
            content_length = int(request['Content-Length'])

        if len(request['body']) < content_length:
            log("Attempting to retrieve {} ({} remaining) bytes of content".format(content_length, content_length - len(request['body'])))
            while len(request['body']) != content_length:
                new_segment = conn.recv(MAX_HTTP_MESSAGE_LENGTH).decode()
                request['body'] += new_segment

        if request['path'] not in path_to_handler:
            log("{} not found in path_to_handler".format(request['path']))
            response = not_configured_response
            conn.send(response)
        else:
            endpoint_handler = path_to_handler[request['path']]
            log("Path found. Passing to {}".format(endpoint_handler))
            request['conn'] = conn
            response = endpoint_handler(request)

            log("Sending response")
            conn.send(response)
    except Exception as e:
        log("Request processing failure")
        print_exception(e)
        conn.send(error_response)

    try:
        conn.close()
    except Exception as e:
        log("Failed to close connection")
        print_exception(e)


def build_response(
    status_code=200,
    body='',
    content_type='text/html'
):
    base = """Content-Type: {content_type}
Connection: close
Access-Control-Allow-Origin: *
Server: edaphic

""".format(content_type=content_type)

    status_line = "HTTP/1.1 {}\n".format(status_code)

    response = status_line + base + body

    return response
