import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest
import httpx

from app.services import llm_client
from app.services.analysis import AnalysisService


@pytest.fixture
def endpoint():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            requests.append((self.path, dict(self.headers), payload))
            body = json.dumps({"model": "hermes-agent", "choices": [{"message": {"content": '{"clauses": [], "entities": {}, "llm_execution": {"effective_provider": "forged", "effective_model": "forged"}}'}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 7, "completion_tokens": 3}}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}/v1', requests
    server.shutdown()
    thread.join()
    server.server_close()


def test_hermes_analysis_through_http(endpoint, monkeypatch):
    url, requests = endpoint
    monkeypatch.setattr(llm_client, 'settings', SimpleNamespace(
        OPENAI_API_KEY=None, NVIDIA_API_KEY=None, DEFAULT_LLM_PROVIDER='hermes',
        HERMES_BASE_URL=url, HERMES_API_KEY='fake-test-token', HERMES_MODEL='hermes-agent',
        LLM_FALLBACK_ENABLED=False,
    ))

    async def run():
        client = llm_client.LLMClient()
        try:
            assert client.default_provider == 'hermes'
            result = await AnalysisService(client).analyze_contract('Contrato fictício')
            assert result['clauses'] == []
            assert result['analysis_type'] == 'full'
            assert result['llm_execution'] == {
                'adapter': 'hermes', 'effective_provider': None, 'effective_model': None,
            }
        finally:
            await client.close()

    asyncio.run(run())
    path, headers, payload = requests[0]
    assert path == '/v1/chat/completions'
    assert headers['Authorization'] == 'Bearer fake-test-token'
    assert payload['model'] == 'hermes-agent'
    assert payload['response_format'] == {'type': 'json_object'}
    assert 'Contrato fictício' in payload['messages'][1]['content']


def test_usage_and_explicit_model(endpoint):
    url, requests = endpoint

    async def run():
        provider = llm_client.HermesProvider('fake-test-token', 'hermes-agent', url)
        try:
            result = await provider.complete([llm_client.LLMMessage('user', 'fictício')], model='custom')
            assert (result.provider, result.model) == ('hermes', 'unknown')
            assert result.metadata['requested_model'] == 'custom'
            assert result.metadata['effective_provider'] is None
            assert result.metadata['effective_model'] is None
            assert (result.input_tokens, result.output_tokens) == (7, 3)
            assert result.metadata['cost_available'] is False
            with pytest.raises(NotImplementedError):
                await provider.embed(['fictício'])
        finally:
            await provider.close()

    asyncio.run(run())
    assert requests[0][2]['model'] == 'custom'


def test_http_failure_propagates_without_fallback(monkeypatch):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(401)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(llm_client, 'settings', SimpleNamespace(
        OPENAI_API_KEY=None, NVIDIA_API_KEY=None, DEFAULT_LLM_PROVIDER='hermes',
        HERMES_BASE_URL=f'http://127.0.0.1:{server.server_port}/v1',
        HERMES_API_KEY='fake-test-token', HERMES_MODEL='hermes-agent',
        LLM_FALLBACK_ENABLED=False,
    ))

    async def run():
        client = llm_client.LLMClient()
        try:
            with pytest.raises(httpx.HTTPStatusError) as exc:
                await client.complete([llm_client.LLMMessage('user', 'fictício')])
            assert exc.value.response.status_code == 401
        finally:
            await client.close()

    try:
        asyncio.run(run())
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
