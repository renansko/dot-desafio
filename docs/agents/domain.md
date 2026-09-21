# Documentação de domínio

Organização multi-contexto: ler `CONTEXT-MAP.md`, o `CONTEXT.md` do módulo em trabalho e os ADRs aplicáveis antes de explorar ou implementar.

- Contextos em `docs/modules/<modulo>/CONTEXT.md`.
- ADRs compartilhados em `docs/adr/`; específicos em `docs/modules/<modulo>/adr/` quando houver decisões locais.
- Usar o vocabulário do contexto em issues, código e testes.
- Atualizar contratos, erros, exemplos e instruções de teste na mesma entrega que alterar o comportamento.
- Sinalizar conflitos com ADRs e registrar a decisão de substituição; não mudar a arquitetura silenciosamente.
- Distinguir comportamento planejado de comportamento implementado e verificável.
