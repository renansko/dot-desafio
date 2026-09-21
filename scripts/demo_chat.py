"""Verificação real explícita: python -m scripts.demo_chat (servidor local em execução)."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def ask(question, history):
    request = Request(
        "http://127.0.0.1:8000/api/chat/",
        data=json.dumps({"question": question, "history": history}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        return json.load(response)["answer"]


def main():
    history = []
    for question in ("Como criar uma lista em Python?", "Como adicionar um item nessa lista?"):
        answer = ask(question, history)
        print(f"Pergunta: {question}\nResposta: {answer}\n")
        history.extend(
            [{"role": "user", "content": question}, {"role": "assistant", "content": answer}]
        )


if __name__ == "__main__":
    try:
        main()
    except (HTTPError, URLError, TimeoutError):
        raise SystemExit("Demonstração falhou. Verifique servidor e configuração do provedor.")
