import asyncio
import json
from types import SimpleNamespace

from app.services.analysis import AnalysisService
from app.services.llm_client import LLMClient, LLMResponse


def test_fallback_and_each_request_metadata_are_not_inferred(monkeypatch):
    class Provider:
        def __init__(self, name, fail=False):
            self.name = name
            self.fail = fail

        async def complete(self, **kwargs):
            if self.fail:
                raise ConnectionError('synthetic failure')
            return LLMResponse(
                content=json.dumps({'clauses': [], 'llm_execution': {'effective_model': 'forged'}}),
                input_tokens=0, output_tokens=0, total_cost_usd=0,
                provider=self.name, model='requested-not-proof',
            )

    client = object.__new__(LLMClient)
    primary = Provider('hermes', fail=True)
    client._providers = {'hermes': primary, 'openai': Provider('openai')}
    client._default_provider = 'hermes'
    from app.services import llm_client
    monkeypatch.setattr(llm_client, 'settings', SimpleNamespace(LLM_FALLBACK_ENABLED=True))

    async def run():
        service = AnalysisService(client)
        fallback_result = await service.analyze_contract('fictitious')
        primary.fail = False
        direct_result = await service.analyze_contract('fictitious')
        assert fallback_result['llm_execution'] == {
            'adapter': 'openai', 'effective_provider': None, 'effective_model': None,
        }
        assert direct_result['llm_execution'] == {
            'adapter': 'hermes', 'effective_provider': None, 'effective_model': None,
        }

    asyncio.run(run())
