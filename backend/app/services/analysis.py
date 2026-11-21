"""Analysis service for contract processing."""
import json
from typing import Any, Dict, List, Optional

from app.services.llm_client import get_llm_client, LLMMessage
from app.services.clause_normalization import normalize_clause


class AnalysisService:
    """Service for contract analysis using LLMs."""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()
    
    async def analyze_contract(
        self,
        contract_text: str,
        analysis_type: str = "full",
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        prompt_version: str = "1.0",
    ) -> Dict[str, Any]:
        """
        Analyze a contract text and extract structured information.
        
        Args:
            contract_text: Full text of the contract
            analysis_type: Type of analysis (full, clause_extraction, risk_assessment, etc.)
            llm_provider: Specific provider to use (None for default)
            llm_model: Specific model to use
            prompt_version: Version of the prompt template
            
        Returns:
            Dict with analysis results including clauses, risks, entities
        """
        
        # Build system prompt based on analysis type
        system_prompt = self._build_system_prompt(analysis_type)
        
        # Build user prompt with contract text
        user_prompt = self._build_user_prompt(contract_text, analysis_type)
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
        
        # Call LLM with JSON response format
        response = await self.llm_client.complete(
            messages=messages,
            provider=llm_provider,
            model=llm_model,
            temperature=0.1,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )
        
        # Parse and validate response
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError as e:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if not json_match:
                raise ValueError(f"Invalid JSON response from LLM: {e}") from e
            try:
                result = json.loads(json_match.group())
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON response from LLM: {e}") from e

        result = self._validate_and_enhance_result(result, analysis_type)
        # Never allow generated content to supply the authenticated envelope.
        result.pop("_execution_evidence_v1", None)
        # This field is owned by the application, never by model-generated JSON.
        # The adapter is observable even when client fallback was used; it is not
        # proof of an upstream provider/model, especially behind Hermes.
        result["llm_execution"] = {
            "adapter": getattr(response, "provider", None),
            "effective_provider": getattr(response, "metadata", {}).get("effective_provider"),
            "effective_model": getattr(response, "metadata", {}).get("effective_model"),
        }
        return result
    
    def _build_system_prompt(self, analysis_type: str) -> str:
        """Build system prompt based on analysis type."""
        
        base_prompt = """Você é um especialista em análise jurídica de contratos brasileiros.
Sua tarefa é analisar contratos e extrair informações estruturadas em formato JSON.

REGRAS IMPORTANTES:
1. Responda APENAS com JSON válido, sem texto adicional
2. Use português brasileiro
3. Seja preciso e cite trechos do contrato quando relevante
4. Classifique riscos de cada cláusula como: low, medium, high, critical
5. Para cada cláusula retorne texto não vazio em content e classificação em risk_level
6. Tipos de cláusula válidos: parties, definitions, scope, obligations, payment, term, termination, liability, indemnification, confidentiality, intellectual_property, dispute_resolution, force_majeure, governing_law, amendment, assignment, notices, general, other"""

        type_prompts = {
            "full": """
ANÁLISE COMPLETA: Extraia todas as cláusulas, classifique riscos, identifique entidades.
Retorne JSON com: clauses[], risk_summary, entities{}, recommendations[]""",
            
            "clause_extraction": """
EXTRAÇÃO DE CLÁUSULAS: Identifique e separe cada cláusula do contrato.
Retorne JSON com: clauses[] contendo number, title, type, content, page_start, page_end""",
            
            "risk_assessment": """
AVALIAÇÃO DE RISCO: Foque em identificar e classificar riscos jurídicos.
Retorne JSON com: risk_summary{}, high_risk_clauses[], recommendations[]""",
            
            "comparison": """
COMPARAÇÃO DE VERSÕES: Identifique diferenças semânticas entre versões.
Retorne JSON com: changes[], risk_delta{}, added_clauses[], removed_clauses[], modified_clauses[]""",
            
            "entity_extraction": """
EXTRAÇÃO DE ENTIDADES: Identifique partes, valores, datas, foro, lei aplicável.
Retorne JSON com: parties{}, financial_terms{}, dates{}, jurisdiction{}, governing_law{}""",
        }
        
        return base_prompt + type_prompts.get(analysis_type, type_prompts["full"])
    
    def _build_user_prompt(self, contract_text: str, analysis_type: str) -> str:
        """Build user prompt with contract text."""
        
        # Truncate if too long (keep first and last parts)
        max_chars = 15000
        if len(contract_text) > max_chars:
            half = max_chars // 2
            contract_text = contract_text[:half] + "\n\n[...CONTEÚDO OMITIDO POR TAMANHO...]\n\n" + contract_text[-half:]
        
        return f"""Contrato para análise:

{contract_text}

---

Realize a análise conforme as instruções do sistema e retorne JSON estruturado."""
    
    def _validate_and_enhance_result(self, result: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
            """Validate and enhance analysis result."""

            if not isinstance(result, dict):
                raise ValueError("Invalid analysis result")
            clauses = result.get("clauses", [])
            if not isinstance(clauses, list) or any(not isinstance(c, dict) for c in clauses):
                raise ValueError("Invalid analysis clauses")
            result["clauses"] = [normalize_clause(c) for c in clauses]

            if not isinstance(result.get("risk_summary"), dict):
                result["risk_summary"] = {}
            # Recompute counts rather than trusting or double-counting model output.
            result["risk_summary"].update({
                "total_clauses": 0,
                "high_risk": 0,
                "medium_risk": 0,
                "low_risk": 0,
                "critical_risk": 0,
            })

            if "entities" not in result:
                result["entities"] = {}

            if "recommendations" not in result:
                result["recommendations"] = []

            # Calculate risk summary from clauses
            for clause in result.get("clauses", []):
                risk_level = clause.get("risk_level", "low")
                if risk_level == "critical":
                    result["risk_summary"]["critical_risk"] += 1
                elif risk_level == "high":
                    result["risk_summary"]["high_risk"] += 1
                elif risk_level == "medium":
                    result["risk_summary"]["medium_risk"] += 1
                else:
                    result["risk_summary"]["low_risk"] += 1

            result["risk_summary"]["total_clauses"] = len(result.get("clauses", []))

            # Add metadata
            result["analysis_type"] = analysis_type
            result["processed_at"] = datetime.utcnow().isoformat()

            return result


# Import datetime at module level
from datetime import datetime