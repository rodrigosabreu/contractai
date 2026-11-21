# ContractAI

Prova de conceito para apoiar a análise de contratos com inteligência artificial. A aplicação permite cadastrar uma organização, enviar um documento e solicitar uma análise estruturada de cláusulas e riscos.

> **Aviso:** projeto experimental, sem aprovação para produção ou uso com dados reais. As análises podem conter omissões ou erros e não substituem revisão jurídica. Use apenas documentos e dados fictícios.

## Demonstração

[Acessar a demonstração temporária do ContractAI](https://bloggers-designed-rug-lived.trycloudflare.com/entrar/cdTrsx2HXgyTu6lwDJLdqynw3sf5cz3-dUNJDgH3SXc)

O link pode deixar de funcionar sem aviso. A demonstração permite criar uma conta: use credenciais exclusivas para teste, dados fictícios e **não envie documentos confidenciais**. A análise pode encaminhar o texto para provedores externos de IA.

## Arquitetura da POC

- **Frontend:** Next.js, React, TypeScript e Tailwind CSS.
- **Backend:** Python, FastAPI, Pydantic e SQLAlchemy.
- **Desenvolvimento:** SQLite e arquivos locais.
- **Análise:** integração com a API local do Hermes, quando configurada. O Hermes pode encaminhar conteúdo a um provedor externo, conforme seu perfil.

O fluxo de análise da API é síncrono. Há código experimental para outros provedores, tarefas e conectores; a existência de uma rota ou tela não comprova que a funcionalidade esteja concluída.

## Limitações conhecidas

- Não há garantia de segurança, isolamento, privacidade ou conformidade regulatória.
- Conteúdo enviado à LLM pode sair da máquina. Avalie as condições dos provedores antes de qualquer uso com documentos reais.
- O processamento de textos longos pode omitir conteúdo intermediário; resultados não devem ser tratados como análise integral.
- Conectores OAuth e sincronização não estão prontos para uso; não conecte contas reais.
- A tela de relatórios contém números de demonstração, não indicadores reais.
- O modelo efetivamente usado pelo Hermes nem sempre pode ser identificado por resposta; não o infira a partir da configuração atual.
- SQLite para testes não equivale a PostgreSQL/pgvector. As migrações existentes não foram validadas para SQLite.

## Estrutura

```text
backend/     API, modelos, serviços e testes
frontend/    interface web e testes
```

As configurações de exemplo não contêm credenciais funcionais. Arquivos `.env`, bancos locais, uploads, logs e dependências não devem ser enviados ao repositório.

## Desenvolvimento

Consulte [backend/README.md](backend/README.md) para os requisitos e a execução local do backend. Para o frontend:

```bash
cd frontend
npm ci
npm test
npm run type-check
npm run dev
```

Antes de ativar qualquer integração de IA, configure credenciais de forma protegida e confira para qual provedor o texto será enviado. Nunca coloque credenciais no navegador, em commits ou em mensagens.

## Estado do projeto

Esta é uma POC em desenvolvimento. Recursos como busca, comparação de versões, integração com armazenamento externo e relatórios completos não devem ser considerados disponíveis apenas porque aparecem no código ou na interface. Não há compromisso de desempenho, precisão ou disponibilidade.

## Licença

Nenhuma licença de código aberto foi definida. A disponibilidade pública do código não concede, por si só, licença para reutilização.
