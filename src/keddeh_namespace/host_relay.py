"""Isolated outbound host lane; no listener or enrollment/credential creation."""
import argparse
from importlib.metadata import version
import fcntl
import json
import os
import re
from pathlib import Path
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit

ENDPOINT = 'https://www.keddeh.com/api/serverspace/1x/host-relay'
REQUEST_LIMIT = 65536
RESPONSE_LIMIT = 262144
COMPLETION_LIMIT = 300000
COMMAND_ID = re.compile(r'[A-Za-z0-9._:-]{8,128}')
FIELDS = {'operation', 'name', 'request_id', 'host_id', 'instance_id', 'source_digest',
          'expected_generation', 'expected_pid', 'pipeline_generation', 'projection_context'}


def encode(value):
    return json.dumps(value, separators=(',', ':'), allow_nan=False).encode()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('redirect prohibited')



def rejection(value):
    return (type(value) is dict and set(value) == {'schema', 'effect', 'code'}
            and value.get('schema') == 'keddeh.host-rejection.v1' and value.get('effect') == 'none'
            and value.get('code') in ('AUTH_DENIED', 'ORIGIN_DENIED', 'INVALID_BODY', 'ADMISSION_REJECTED'))


class NoActuationRejected(Exception):
    def __init__(self, code):
        self.code = code


def post(url, token_file, payload):
    raw = encode(payload)
    completion = payload.get('op') == 'complete'
    limit = COMPLETION_LIMIT if completion else REQUEST_LIMIT
    if completion and len(encode(payload.get('result'))) > RESPONSE_LIMIT:
        raise ValueError('completion result exceeds 256 KiB; pending state retained')
    if len(raw) > limit:
        raise ValueError('request exceeds endpoint bound; pending state retained')
    target = urlsplit(url)
    if url == ENDPOINT:
        proxy = urllib.request.ProxyHandler()  # Preserve managed egress and CA trust.
    elif target.scheme == 'http' and target.hostname == '127.0.0.1' and not target.username and not target.password:
        proxy = urllib.request.ProxyHandler({})
    else:
        raise ValueError('unsupported relay transport destination')
    token = Path(token_file).read_text().strip()
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    if url == ENDPOINT:
        headers['User-Agent'] = 'Keddeh-Host-Relay/' + version('keddeh-sovereign-namespace-runtime')
    request = urllib.request.Request(url, data=raw, headers=headers)
    opener = urllib.request.build_opener(proxy, NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            raw = response.read(RESPONSE_LIMIT + 1)
    except urllib.error.HTTPError as exc:
        raw = exc.read(4097)
        try: value = json.loads(raw) if len(raw) <= 4096 else None
        except ValueError: value = None
        if exc.code in (400, 401, 403) and rejection(value):
            raise NoActuationRejected(value['code']) from None
        raise
    if len(raw) > RESPONSE_LIMIT:
        raise ValueError('response exceeds 256 KiB')
    return json.loads(raw)


def save(path, value):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(encode(value)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def validate(packet, host_id):
    if type(packet) is not dict or len(encode(packet)) > REQUEST_LIMIT:
        raise ValueError('invalid packet')
    if set(packet) != {'jsonrpc', 'id', 'method', 'params'} or packet['jsonrpc'] != '2.0':
        raise ValueError('invalid JSON-RPC envelope')
    if type(packet['id']) is not str or not COMMAND_ID.fullmatch(packet['id']) or packet['method'] != 'tools/call':
        raise ValueError('only identified tools/call supported')
    params = packet['params']
    if type(params) is not dict or set(params) != {'name', 'arguments'} or params['name'] != 'host_actuator':
        raise ValueError('unexpected tool')
    args = params['arguments']
    if type(args) is not dict or set(args) - FIELDS or args.get('operation') not in ('status', 'start', 'stop', 'restart'):
        raise ValueError('invalid actuator arguments')
    if args.get('host_id', host_id) != host_id:
        raise ValueError('wrong host binding')
    if args['operation'] != 'status':
        required = FIELDS - {'projection_context'}
        if not required <= set(args) or args['host_id'] != host_id:
            raise ValueError('mutation requires original descriptor fences')
        if not all(type(args[k]) is str and args[k] for k in ('name', 'request_id', 'instance_id', 'source_digest')):
            raise ValueError('invalid mutation identity')
        if args['request_id'] != packet['id']:
            raise ValueError('packet and actuator request identity differ')
        if len(args['request_id']) > 128 or args['name'] == 'estate':
            raise ValueError('unsupported mutation')
        if any(type(args[k]) is not int or args[k] < 0 for k in ('expected_generation', 'pipeline_generation')):
            raise ValueError('invalid generation')
        if args['expected_pid'] is not None and (type(args['expected_pid']) is not int or args['expected_pid'] <= 0):
            raise ValueError('invalid process identity')
    return args


class Worker:
    def __init__(self, root, relay_token_file, state_file, transport=post):
        self.root = Path(root)
        self.token_file = Path(relay_token_file)
        self.state_file = Path(state_file)
        self.transport = transport
        binding = json.loads((self.root / 'state/host-binding.json').read_text())
        self.host_id = binding['host_id']
        port = json.loads((self.root / 'launch.json').read_text())['ports']['gateway']
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('invalid gateway port')
        self.gateway = f'http://127.0.0.1:{port}/api/web4/control'

    def relay(self, body):
        return self.transport(ENDPOINT, self.token_file, {'host_id': self.host_id, **body})

    def step(self):
        # One owner spans recovery, dispatch, persistence and completion acknowledgement.
        with open(str(self.state_file) + '.lock', 'a') as lock:
            os.chmod(lock.name, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            state = json.loads(self.state_file.read_text()) if self.state_file.exists() else {}
            if state and state.get('host_id') != self.host_id:
                raise ValueError('pending host binding changed')
            if not state or state.get('acknowledged'):
                reply = self.relay({'op': 'claim'})
                call = reply['call']
                if call is None:
                    return 'idle'
                if type(call) is not dict or set(call) != {'id', 'claim', 'packet'} or any(type(call[k]) is not str or not call[k] for k in ('id', 'claim')):
                    raise ValueError('invalid claim; no local dispatch')
                state = {'host_id': self.host_id, 'call': call}
                save(self.state_file, state)
            call = state['call']
            if (not COMMAND_ID.fullmatch(call['id']) or not isinstance(call['packet'], dict)
                    or call['packet'].get('id') != call['id']):
                raise ValueError('claim and packet identity differ; no local dispatch')
            if 'result' not in state:
                packet = call['packet']
                try:
                    args = validate(packet, self.host_id)
                except (ValueError, TypeError, KeyError):
                    packet_id = packet.get('id') if isinstance(packet, dict) else None
                    if type(packet_id) not in (str, int):
                        packet_id = None
                    result = {'jsonrpc': '2.0', 'id': packet_id, 'error': {'code': -32602, 'message': 'Invalid bounded host_actuator packet'}}
                else:
                    # On any transport uncertainty retain the original packet and request_id.
                    # Recover terminal results without re-entering mutation admission.
                    if state.get('dispatch_started') and args['operation'] != 'status':
                        history = self.transport(self.gateway, self.root / 'state/token',
                            {'action': 'estate', 'tool': 'host_actuator', 'arguments':
                             {'operation': 'status', 'request_id': args['request_id']}})
                        record = history.get('structuredContent', {}).get('record')
                        if not isinstance(record, dict) or record.get('status') not in ('COMPLETED', 'FAILED'):
                            raise ValueError('target history unresolved; original claim retained')
                        expected = {k: v for k, v in args.items() if k != 'projection_context'}
                        if record.get('command') != expected:
                            raise ValueError('target history identity mismatch')
                        recovered = record.get('result')
                        if not isinstance(recovered, dict):
                            raise ValueError('terminal target result missing')
                        response = {'content': [{'type': 'text', 'text': json.dumps(recovered, sort_keys=True)}],
                                    'structuredContent': recovered, 'isError': False}
                    else:
                        state['dispatch_started'] = True
                        save(self.state_file, state)
                        try:
                            response = self.transport(self.gateway, self.root / 'state/token',
                                                      {'action': 'estate', 'tool': 'host_actuator', 'arguments': args})
                        except NoActuationRejected as exc:
                            response = {'structuredContent': {'schema': 'keddeh.host-rejection.v1',
                                        'effect': 'none', 'code': exc.code}}

                    if type(response) is not dict:
                        raise ValueError('invalid local response; pending claim retained')
                    if rejection(response.get('structuredContent')):
                        result = {'jsonrpc': '2.0', 'id': packet['id'], 'error': {
                            'code': -32010, 'message': 'Host command rejected before actuation',
                            'data': response['structuredContent']}}
                    else:
                        result = {'jsonrpc': '2.0', 'id': packet['id'], 'result': response}
                state['result'] = result
                save(self.state_file, state)
            completed = self.relay({'op': 'complete', 'id': call['id'], 'claim': call['claim'], 'result': state['result']})
            if completed.get('stored') is not True:
                raise ValueError('completion not acknowledged')
            state['acknowledged'] = True
            save(self.state_file, state)
            return 'completed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--relay-token-file', required=True, type=Path)
    parser.add_argument('--state-file', required=True, type=Path)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    worker = Worker(args.root, args.relay_token_file, args.state_file)
    while True:
        try:
            outcome = worker.step()
        except Exception:
            # Neither credentials, packets nor transport exception text reach logs.
            outcome = 'pending; inspect private state and endpoint availability'
        print(outcome, flush=True)
        if args.once:
            break
        time.sleep(5)


if __name__ == '__main__':
    main()
