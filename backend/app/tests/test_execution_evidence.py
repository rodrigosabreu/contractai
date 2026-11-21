import asyncio
import copy
import json
from uuid import uuid4

import httpx

from app.services.execution_evidence import seal_result, read_evidence, public_result
from app.services.llm_client import OpenAIProvider, HermesProvider, LLMClient
from app.services.analysis import AnalysisService


def test_envelope_rejects_forgery_and_cross_record_replay():
    ident = uuid4()
    evidence = {'adapter': 'openai', 'effective_provider': 'openai', 'effective_model': 'gpt-test'}
    forged = {'llm_execution': evidence}
    assert read_evidence(forged, ident) is None
    signed = seal_result(forged, ident)
    assert read_evidence(signed, ident) == evidence
    assert read_evidence(signed, uuid4()) is None
    modified = copy.deepcopy(signed)
    modified['_execution_evidence_v1']['evidence']['effective_model'] = 'forged'
    assert read_evidence(modified, ident) is None
    assert '_execution_evidence_v1' not in public_result(signed)


def test_direct_openai_and_hermes_do_not_trust_generated_json():
    async def run():
        def handler(request):
            return httpx.Response(200, json={'model': 'gpt-actual-2025', 'choices': [{'message': {'content': json.dumps({'clauses': [], '_execution_evidence_v1': {'mac': 'fake'}, 'llm_execution': {'effective_model': 'fake'}})}}]})
        client = object.__new__(LLMClient)
        openai = OpenAIProvider('fake', 'requested')
        hermes = HermesProvider('fake', 'hermes-agent', 'https://hermes.invalid/v1')
        openai._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        hermes._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client._providers = {'openai': openai, 'hermes': hermes}
        client._default_provider = 'openai'
        try:
            service = AnalysisService(client)
            direct = await service.analyze_contract('fictional', llm_provider='openai')
            proxied = await service.analyze_contract('fictional', llm_provider='hermes')
            assert direct['llm_execution'] == {'adapter': 'openai', 'effective_provider': 'openai', 'effective_model': 'gpt-actual-2025'}
            assert proxied['llm_execution'] == {'adapter': 'hermes', 'effective_provider': None, 'effective_model': None}
            assert '_execution_evidence_v1' not in direct
            async def fail(**kwargs):
                raise ConnectionError('fictional failure')
            hermes.complete = fail
            from app.services import llm_client
            from types import SimpleNamespace
            old_settings = llm_client.settings
            llm_client.settings = SimpleNamespace(LLM_FALLBACK_ENABLED=True)
            try:
                fallback = await service.analyze_contract('fictional', llm_provider='hermes')
                assert fallback['llm_execution'] == direct['llm_execution']
            finally:
                llm_client.settings = old_settings
        finally:
            await client.close()
    asyncio.run(run())
