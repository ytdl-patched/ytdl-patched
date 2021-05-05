from __future__ import unicode_literals

import codecs
import json

from ..utils import check_executable, to_str
from ..compat import compat_str
from subprocess import Popen, PIPE
from os.path import join


# (mostly joke) wrappers for NodeJS WebSocket packages

if check_executable('node', ['-v']) and check_executable('npm', ['-v']):
    npm_prefix = Popen(
        ['npm', 'prefix', '-g'],
        stdout=PIPE, stderr=PIPE, stdin=PIPE)

    NPM_GLOBAL_PATH, _ = npm_prefix.communicate()
    NPM_GLOBAL_PATH = join(NPM_GLOBAL_PATH.decode().strip(), 'lib/node_modules')
    NPM_IS_SANE = npm_prefix.returncode == 0
else:
    NPM_IS_SANE = False

if NPM_IS_SANE:
    def start_node_process(args):
        return Popen(
            ['node', *args],
            stdout=PIPE, stderr=None, stdin=PIPE,
            env={'NODE_PATH': NPM_GLOBAL_PATH})

    def test_package_existence(pkg):
        assert isinstance(pkg, compat_str)
        p = start_node_process(['-e', 'require("%s")' % pkg])
        p.wait()
        return p.returncode == 0

    """
    Details of protocol between Node.js process(N) and NodeJsWrapperBase(P):

    0. Every tokens are send via stdin/stdout by line-by-line manner, terminated by LF.
    1. When N has started, prints "OPENED" after opening connection. P will wait for it.
    2. All inbound frames must be converted into HEX and printed to N's stdout.
    3. All outbound frames are converted into HEX and printed to N's stdin.
    """
    class NodeJsWrapperBase():
        def __init__(self, url, headers={}):
            self.proc = start_node_process(['-e', self.EVAL_CODE % (json.dumps(url), json.dumps({
                # any JSON is valid for JS object/array/string/number
                'headers': headers,
            }))])
            while True:
                if to_str(self.proc.stdout.readline()).strip() == 'OPENED':
                    return

        def send(self, data):
            if isinstance(data, compat_str):
                data = data.encode('utf-8')
            data = codecs.encode(data, "hex")
            self.proc.stdin.write(data)
            self.proc.stdin.write(b'\n')
            self.proc.stdin.flush()

        def recv(self):
            ret = self.proc.stdout.readline().strip()
            ret = codecs.decode(ret, "hex")
            if isinstance(ret, bytes):
                ret = ret.decode('utf-8')
            return ret

        def close(self):
            self.proc.kill()
            self.proc.terminate()
            self.proc = None

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            self.close()

    class NodeJsWsWrapper(NodeJsWrapperBase):
        EVAL_CODE = '''
            const readline = require("readline");
            const rl = readline.createInterface({
                input: process.stdin,
                output: process.stdout
            });

            const WebSocket = require('ws');

            const ws = new WebSocket(%s, %s);

            rl.on("line", function(line){
                ws.send(Buffer.from(line, "hex").toString("utf8"));
            });

            ws.on('open', function() {
                console.log('OPENED');
            });

            ws.on('error', function(err) {
                const util = require('util');
                process.stderr.write(util.inspect(err));
                process.stderr.write("\\n");
                process.exit(1);
            });

            // https://github.com/websockets/ws/blob/HEAD/doc/ws.md#event-message
            ws.on('message', function(data) {
                if(typeof data === 'string'){
                    data = [Buffer.from(data, 'utf8')];
                }else if(Buffer.isBuffer(data)){
                    data = [data];
                }else if(Array.isArray(data) && data.length){
                    if (Buffer.isBuffer(data[0])) {
                        // pass, expected type
                    }else{
                        // ArrayBuffer
                        data = [Buffer.from(data, 'utf8')];
                    }
                }else{
                    // unknown type, do toString() here
                    data = [Buffer.from(`${data}`, 'utf8')];
                }

                for (d of data) {
                    console.log(d.toString('hex'));
                }
            });
        '''.strip()

    class NodeJsWebsocketWrapper(NodeJsWrapperBase):
        EVAL_CODE = '''
            const readline = require("readline");
            const rl = readline.createInterface({
                input: process.stdin,
                output: process.stdout
            });

            const WebSocket = require('websocket').client;

            const ws = new WebSocket();

            ws.on('connect', function(conn) {
                console.log('OPENED');
                rl.on("line", function(line){
                    conn.sendUTF(Buffer.from(line, "hex").toString("utf8"));
                });
                conn.on('message', function(message) {
                    let buf;
                    if(message.type == 'utf8'){
                        buf = Buffer.from(message.utf8Data, 'utf8');
                    }else if(message.type == 'binary'){
                        buf = Buffer.from(message.binaryDataBuffer);
                    }else{
                        return;
                    }

                    console.log(buf.toString('hex'));
                });
                conn.on('error', function(err) {
                    const util = require('util');
                    process.stderr.write(util.inspect(err));
                    process.stderr.write("\\n");
                    process.exit(1);
                });
            });

            ws.on('error', function(err) {
                const util = require('util');
                process.stderr.write(util.inspect(err));
                process.stderr.write("\\n");
                process.exit(1);
            });

            ws.connect(%s, null, null, %s);
        '''.strip()

    HAVE_NODEJS_WS_WRAPPER = test_package_existence('ws')
    HAVE_NODEJS_WEBSOCKET_WRAPPER = test_package_existence('websocket')
else:
    NodeJsWsWrapper, NodeJsWebsocketWrapper = (None, ) * 2
    HAVE_NODEJS_WS_WRAPPER, HAVE_NODEJS_WEBSOCKET_WRAPPER = (False, ) * 2
