# ADR 0001 — Publicação atômica de FAISS e metadados

Status: aceito.

## Contexto

Q3 exige persistência, compatibilidade por modelo/configuração e manutenção do índice anterior
quando a reconstrução falha. Publicar dois arquivos independentes permite que uma consulta
combine vetores novos com metadados antigos.

## Decisão

Persistir FAISS serializado e JSON em um único ZIP. Construir e sincronizar um temporário no
mesmo diretório; publicar com uma substituição atômica. A consulta lê um snapshot completo.
O formato registra configuração exata e checksum dos vetores; não usa pickle. Provedor/modelo
são parte da identidade semântica, não apenas a dimensão. Revisão local opcional permite fixar
pesos; modelos remotos com nomes mutáveis dependem da estabilidade oferecida pelo provedor.

Usar índice exato com cosseno e classificar todos os trechos antes de deduplicar pelo documento.
Isso garante até k documentos distintos disponíveis, sem heurísticas de oversampling.

Referências: [I/O FAISS](https://github.com/facebookresearch/faiss/wiki/Index-IO%2C-cloning-and-hyper-parameter-tuning)
e [índices exatos](https://github.com/facebookresearch/faiss/wiki/Guidelines-to-choose-an-index).

## Consequências

Implementação adequada ao corpus pequeno do desafio. Cada requisição carrega um snapshot e cada
reconstrução reprocessa todo o corpus. A substituição exige sistema de arquivos local com rename
atômico; não promete durabilidade contra perda de energia do diretório. Concorrência entre builds
é last-writer-wins, sem geração parcialmente publicada. Índices são arquivos locais confiáveis.
Escalabilidade, GC de gerações, locks distribuídos e atualizações incrementais ficam fora da Q3.
