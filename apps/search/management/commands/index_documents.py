from django.core.management.base import BaseCommand, CommandError

from apps.search.application.errors import InvalidCorpus, SearchTimeout, SearchUnavailable
from apps.search.application.use_cases import BuildIndex
from apps.search.infrastructure.corpus import read_corpus
from apps.search.infrastructure.embeddings import LangChainEmbeddings
from apps.search.infrastructure.faiss_index import FaissIndex
from apps.search.infrastructure.settings import load_config


class Command(BaseCommand):
    help = "Indexa documentos JSON do brain, publicando FAISS e metadados atomicamente."

    def add_arguments(self, parser):
        parser.add_argument("--corpus", default="apps/brain/documents")

    def handle(self, *args, **options):
        try:
            config = load_config()
            documents = read_corpus(options["corpus"])
            count = BuildIndex(
                LangChainEmbeddings(config), FaissIndex(config.path), config.spec,
            ).execute(documents)
        except (InvalidCorpus, SearchUnavailable) as exc:
            raise CommandError(str(exc)) from None
        except SearchTimeout:
            raise CommandError("Tempo limite dos embeddings excedido; índice anterior preservado.")
        except Exception:
            raise CommandError("Falha na indexação; índice anterior preservado.") from None
        self.stdout.write(self.style.SUCCESS(
            f"{len(documents)} documentos, {count} trechos indexados em {config.path}."
        ))
