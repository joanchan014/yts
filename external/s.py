#!/usr/bin/python
# encoding : utf-8

from urlparse import parse_qs
import re
import sys
import os
import urllib2
import errno
import json
# from flup.server.fcgi import WSGIServer
import socket
import SocketServer


cur_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, cur_path + '/youtube-dl')

# print (sys.path)

from youtube_dl.jsinterp import JSInterpreter
from youtube_dl.compat import (
    compat_chr,
    compat_str,
)
from youtube_dl.utils import write_json_file

compiled_regex_type = type(re.compile(''))

# real signature unknown; restored from __doc__


def isinstance(p_object, class_or_type_or_tuple):
    """
    isinstance(object, class-or-type-or-tuple) -> bool

    Return whether an object is an instance of a class or of a subclass thereof.
    With a type as second argument, return whether that is the object's type.
    The form using a tuple, isinstance(x, (A, B, ...)), is a shortcut for
    isinstance(x, A) or isinstance(x, B) or ... (etc.).
    """
    return False


def next(iterator, default=None):  # real signature unknown; restored from __doc__
    """
    next(iterator[, default])

    Return the next item from the iterator. If default is given and the iterator
    is exhausted, it is returned instead of raising StopIteration.
    """
    pass


def _search_regex(pattern, string, name, group=None):
    if isinstance(pattern, (str, compat_str, compiled_regex_type)):
        mobj = re.search(pattern, string, 0)
    else:
        for p in pattern:
            mobj = re.search(p, string, 0)
            if mobj:
                # print mobj
                break

    if mobj:
        if group is None:
            # return the first matching group
            return next(g for g in mobj.groups() if g is not None)
        else:
            return mobj.group(group)
    else:
        print 'unable to extract %s' % name


def parse_sig_js(jscode):
    jsi = JSInterpreter(jscode)
    funcname = _search_regex(
            (r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b(?P<sig>[a-zA-Z0-9$]{2})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)',
             r'(?P<sig>[a-zA-Z0-9$]+)\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)',
             # Obsolete patterns
             r'(["\'])signature\1\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\.sig\|\|(?P<sig>[a-zA-Z0-9$]+)\(',
             r'yt\.akamaized\.net/\)\s*\|\|\s*.*?\s*[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?:encodeURIComponent\s*\()?\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bc\s*&&\s*a\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(',
             r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\('),
        jscode, 'Initial JS player signature function name', group='sig')
    initial_function = jsi.extract_function(funcname)
    return lambda s: initial_function([s])


def _download_js_file(url):
    return urllib2.urlopen(url).read()


def get_cache_fn(func_id, dType='json'):
    return '%s/.cache/%s.%s' % (cur_path, func_id, dType)


def cache_store(func_id, data):
    path = get_cache_fn(func_id)

    try:
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as ose:
            if ose.errno != errno.EEXIST:
                raise
        write_json_file(data, path)
    except Exception:
        pass


def cache_load(func_id):
    """ load cache function """
    path = get_cache_fn(func_id)

    try:
        with open(path) as cachef:
            return json.load(cachef)
    except IOError:
        pass  # No cache available

    return None


def _signature_cache_id(example_sig):
    """ Return a string representation of a signature """
    return '.'.join(compat_str(len(part)) for part in example_sig.split('.'))


def _decrypt_signature(s, js_url):
    """Turn the encrypted s field into a working signature"""
    if js_url is None:
        return None

    # js_url = js_url.replace('http:', 'https://www.youtube.com')

    id_m = re.match(
        # r'.*?[-.](?P<id>[a-zA-Z0-9_-]+)(?:/watch_as3|/html5player(?:-new)?|(?:/[a-z]{2,3}_[A-Z]{2})?/base)?\.(?P<ext>[a-z]+)$',
        r'.*player/(?P<id>\w+)/.*?[-.](?P<idx>[a-zA-Z0-9_-]+)/(?P<l>\w+)/base.(?P<ext>[a-z]+)$',
        js_url)
    if not id_m:
        # raise ExtractorError('Cannot identify player %r' % js_url)
        return None

    player_type = id_m.group('ext')
    # player_id = id_m.group('id')
    player_id = '%s-%s-%s' % (id_m.group('id'), id_m.group('idx'), id_m.group('l'))
    # Read from filesystem cache
    func_id = '%s_%s_%s' % (
        player_type, player_id, _signature_cache_id(s))
    assert os.path.basename(func_id) == func_id

    cache_spec = cache_load(func_id)
    if cache_spec is None:
        func = parse_sig_js(_download_js_file(
            'https://www.youtube.com' + js_url))
        test_string = ''.join(map(compat_chr, range(len(s))))
        cache_res = func(test_string)
        cache_spec = [ord(c) for c in cache_res]
        cache_store(func_id, cache_spec)

    return ''.join(s[i] for i in cache_spec)


# def myapp(environ, start_response):
#     """nginx entery function"""
#     parameters = parse_qs(environ.get('QUERY_STRING', ''))
#     s = None
#     url = None
#     res = None
#     header = [('Content-Type', 'text/plain')]

#     if 's' in parameters:
#         s = parameters['s'][0]
#     if 'url' in parameters:
#         url = parameters['url'][0]

#     if s is None or url is None:
#         start_response('404 Fail', header)
#         res = "Request fail please check url"
#     else:
#         res = _decrypt_signature(s, url)

#     if res is None:
#         start_response('501 Fail', header)
#         res = "Parse sig fail"
#     else:
#         start_response('200 OK', header)

#     return res

# if __name__ == '__main__':
#     #WSGIServer(myapp, bindAddress=('127.0.0.1', 8008)).run()

class MyTCPServer(SocketServer.TCPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)

class MyHandler(SocketServer.BaseRequestHandler):
    G_ERR_CNT = 0
    G_ERR = 'e'

    def handle(self):
        client_data = self.request.recv(1024)
        b = client_data.split(' ')

        if MyHandler.G_ERR_CNT > 10:
            return self.request.sendall(MyHandler.G_ERR)

        try:
            sr = _decrypt_signature(b[0], b[1])
            if sr is None:
                sr = 'Sig function err!'          
        except Exception, e:
            # print type(e)
            sr = format(str(e))
            MyHandler.G_ERR_CNT = MyHandler.G_ERR_CNT+1
            MyHandler.G_ERR = '%s' % (sr)
        finally:
            self.request.sendall(sr)

if __name__ == '__main__':
    HOST, PORT = 'localhost', 3001
    server = MyTCPServer((HOST, PORT), MyHandler)
    print 'python server listening %s' %  PORT
    server.serve_forever()

