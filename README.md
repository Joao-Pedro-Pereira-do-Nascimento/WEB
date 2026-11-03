# UNO FOLCLÓUNO

Jogo de cartas **online e multijogador** no estilo UNO, feito em **Streamlit**, em que as cartas são
personagens do **folclore brasileiro**: Saci, Curupira, Cuca, Iara, Mula sem Cabeça, Boto, Boitatá e outros.
Toda a arte (cartas, logo animado, ícones, avatares e favicon) é **SVG original gerado em código** — sem
emojis, sem pacotes de ícones e sem imagens prontas —, com animações em CSS/SVG e **efeitos sonoros
sintetizados** pela Web Audio API (sem arquivos de áudio). Visual de RPG sombrio: mata à noite, névoa,
vaga-lumes e luz de tocha. Funciona igual no celular e no computador.

- 2 a 6 jogadores por sala (complete com **bots**)
- Sala com **código de 5 letras**: cada pessoa entra pelo próprio celular/computador com o próprio nome
- **Reconexão**: recarregou a página ou trocou de aparelho? O **link de reconexão** devolve o mesmo lugar e as mesmas cartas
- Atualização em tempo real (a mesa é relida a cada ~1 s)
- **Ranking** persistente por nome de jogador
- **Bestiário** com todas as cartas e as lendas de cada personagem

## Início rápido

```bash
git clone https://github.com/Joao-Pedro-Pereira-do-Nascimento/WEB.git
cd WEB
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Abra **http://localhost:8501** no navegador, digite seu nome, crie uma sala e passe o código de 5 letras
para os amigos (ou adicione bots). Funciona sem configurar nada: sem Firebase, os dados ficam na pasta `.data/`.
Detalhes (rede local, Firebase, login com Google, deploy e testes) nas seções abaixo.

---

## Regras (UNO oficial)

- **108 cartas**: 4 cores × (um 0, dois de cada 1–9, dois Pular, dois Inverter, dois +2) + 4 Coringas + 4 Coringas +4.
- Cada jogador recebe **7 cartas**. Vira-se a primeira carta do monte (se for +4, ela volta ao monte).
- Na sua vez, jogue uma carta que combine com o topo do descarte na **cor**, no **número** ou no **símbolo** — ou um coringa.
- Sem jogada (ou se preferir), **compre 1 carta**: se ela servir, você pode jogá-la na hora; senão, a vez passa.
- Quando o monte acaba, o descarte (menos a carta do topo) é **embaralhado** e vira o novo monte.
- **Pular**: o próximo perde a vez. **Inverter**: inverte o sentido (com **2 jogadores vale como Pular**).
  **+2**: o próximo compra 2 e perde a vez. **Coringa**: você escolhe a cor.
  **+4**: escolhe a cor e o próximo compra 4 e perde a vez — ele pode **desafiar**: se você tinha carta da cor da mesa, *você* compra 4; se não tinha, ele compra 6.
- **UNO!**: ao ficar com 1 carta, aperte **UNO!** (com 2 cartas antes de jogar, ou logo depois de jogar).
  Se esquecer, qualquer adversário pode **denunciar** antes do próximo jogador agir: **+2 cartas** de punição.
- A rodada acaba quando alguém **esvazia a mão**. Pontuação: números = valor da carta;
  Pular/Inverter/+2 = 20; Coringas = 50. O vencedor soma os pontos das mãos dos adversários.
- Modo **rodada única** (padrão) ou partida até **100 / 200 / 500 pontos**.

Toda jogada é **validada do lado do servidor** (só o jogador da vez age e só cartas legais são aceitas),
dentro de uma transação no armazenamento.

## Personagens e cartas

As 4 cores são 4 biomas: **Fogo** (vermelho) · **Mata** (verde) · **Rios** (azul) · **Cerrado** (amarelo).

| Carta | Personagem | Por quê |
|---|---|---|
| Pular | **Saci-Pererê** | some num redemoinho e leva a vez do próximo |
| Inverter | **Curupira** | pés virados para trás: as pegadas invertem o caminho |
| +2 | **Cuca** | a poção do caldeirão faz o próximo comprar 2 |
| Coringa | **Iara** | o canto da sereia muda a cor da mesa |
| Coringa +4 | **Mula sem Cabeça** | galope de fogo: o próximo compra 4 |
| 0 | Vitória-régia | |
| 1 | Boto-cor-de-rosa | |
| 2 | Boitatá | |
| 3 | Lobisomem | |
| 4 | Caipora | |
| 5 | Mapinguari | |
| 6 | Negrinho do Pastoreio | |
| 7 | Matinta Pereira | |
| 8 | Boi-bumbá | |
| 9 | Cobra-Grande (Boiúna) | |

A aba **Bestiário** mostra cada carta com a lenda do personagem. Em qualquer lugar, passe o mouse sobre uma carta
(computador) ou **segure o dedo** sobre ela (celular) para ver a carta ampliada com todos os textos — o toque curto
continua jogando a carta normalmente.

## Logo, efeitos e sons

**Logo animado** (SVG desenhado em código, `ui/logo.py`): o "O" de UNO é o olho em chamas do **Boitatá**
(pisca), cujo corpo de fogo serpenteia sob as letras; o primeiro "O" de FOLCLÓUNO é o anel de água da **Iara**;
os dois "L" são o **Saci** (perna única, gorro balançando, cachimbo) e o **Curupira** (cabelo de fogo; as
pegadas ao contrário andam ao lado de UNO); o "C" é a bocarra de jacaré da **Cuca**; o acento do "Ó" é a
labareda da **Mula sem Cabeça** e o "U" é a ferradura dela; o último "O" é a lua cheia.

**Animações** (CSS/SVG, leves, e respeitam *reduzir movimento* do sistema). Cada uma toca **uma vez só** por
evento, mesmo com a página sendo redesenhada a cada segundo (chave de evento guardada em `st.session_state`):

- **Entrar numa sala:** a névoa se abre como um portal, cartas giram no ar e o código da sala surge.
- **Alguém entra na sala:** quem já estava vê o nome surgir de uma fogueira ("Fulano entrou na sala"), com som.
  Quando alguém sai, um aviso discreto na névoa.
- **Cartas especiais vivas** (na mão, na mesa e no Bestiário): Saci (Pular) com redemoinho girando e gorro
  balançando; Curupira (Inverter) com cabelo de fogo e pegadas piscando; Cuca (+2) com olho brilhando e caldeirão
  borbulhando; Iara (Coringa) com água ondulando e escamas brilhando; Mula sem Cabeça (+4) com chamas vivas.
- **Jogadas:** redemoinho do Saci com o gorro voando (Pular), pegadas ao contrário e setas (Inverter), olhos e
  caldeirão da Cuca (+2), parede de labaredas (+4), onda da cor escolhida (Coringa/escolha de cor), ondas de
  grito (UNO!), corneta e tremor (denúncia), cartas voando para quem compra, brilho na mão na sua vez,
  cena de **vitória** (coroa, raios dourados, brasas) e de **derrota** (névoa e cinzas).

**Duelo de biomas:** sempre que uma carta cai no descarte, os dois biomas (o da mesa e o da carta) se
enfrentam numa animação curta (~2 s, tela cheia, sem bloquear cliques), vista por todos na sala — inclusive nas
jogadas dos bots. Ciclo de vantagem: **Rios apagam o Fogo**, **Fogo queima a Mata**, **Mata vence o Cerrado**,
**Cerrado seca os Rios**; nos pares inversos o mais fraco resiste (o Fogo ferve os Rios, a Mata abafa o Fogo...);
mesmo bioma vira uma aura de reforço; Coringa/+4 faz a cor escolhida invadir a mesa. São 16 combinações, cada uma
com som próprio do bioma. O duelo toca primeiro e o efeito da carta especial vem logo depois. É só visual: não
muda nada nas regras (`ui/duels.py`).

**Personagens dos jogadores:** cada jogador escolhe um retrato do folclore (Saci, Curupira, Iara, Cuca, Mula sem
Cabeça, Boitatá, Boto-cor-de-rosa, Caipora, Negrinho do Pastoreio, Lobisomem, Mapinguari, Boi-bumbá, Matinta
Pereira e Boiúna) ao criar ou entrar numa sala, e pode trocar na sala de espera (botão **Trocar** ao lado do nome).
Dois jogadores nunca ficam com o mesmo personagem.

**Sons** (sintetizados com Web Audio API): jogar, comprar, passar, Pular, Inverter, +2/+4, alerta de +4, Coringa,
UNO!, denúncia, desafio, "sua vez", embaralhar, distribuir, portal, chegada e saída de jogador, vitória, derrota.
Há **Silenciar sons** e **Testar som** no topo. *Os navegadores só liberam áudio depois do primeiro clique.*

---

## Rodar no computador

Requer Python 3.10+ (testado em 3.14).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
streamlit run app.py
```

Abra http://localhost:8501, crie uma sala e passe o código. Para testar sozinho, abra outra aba
(ou uma janela anônima) e entre com outro nome — ou adicione bots.

Sem Firebase configurado, os dados ficam em arquivos JSON na pasta `.data/` (com trava de arquivo,
funciona com várias abas e vários aparelhos acessando o mesmo servidor).

## Jogar na rede local (LAN)

```bash
streamlit run app.py --server.address 0.0.0.0
```

O Streamlit mostra o **Network URL** (ex.: `http://192.168.0.10:8501`). Os outros aparelhos da mesma
rede Wi-Fi abrem esse endereço e entram com o código da sala. (Se não abrir, libere a porta 8501 no firewall.)

## Firebase Realtime Database — salas e ranking online

No Streamlit Community Cloud o disco é temporário (os dados locais somem quando o app reinicia). Para salas e
**ranking global** persistentes, o app usa o **Firebase Realtime Database** do projeto `BaralhoFloclorioBR`
(`https://baralhoflocloriobr-default-rtdb.firebaseio.com`, plano Spark gratuito).

**Como o app escolhe o armazenamento** (arquivo `.streamlit/secrets.toml`):

| O que tem nos secrets | Armazenamento usado |
|---|---|
| seção `[firebase]` **com** `database_url` | Firebase **Realtime Database** (recomendado) |
| seção `[firebase]` **sem** `database_url` | Cloud Firestore (modo antigo, continua funcionando) |
| nada | arquivos locais em `.data/` |

Se as credenciais falharem, o app volta para o modo local e mostra um aviso no topo. A barra do topo sempre
mostra qual armazenamento está em uso. (`UNO_BACKEND=local` força o modo local; `UNO_BACKEND=firestore` força o Firestore.)

### Passo a passo (para leigos)

1. Abra https://console.firebase.google.com e entre no projeto **BaralhoFloclorioBR**.
2. Clique na **engrenagem** ao lado de "Visão geral do projeto" e depois em **Configurações do projeto**.
3. Abra a aba **Contas de serviço** e clique em **Gerar nova chave privada** e depois em **Gerar chave**.
   O navegador baixa um arquivo `.json`. **Guarde-o com cuidado e nunca envie para o GitHub.**
4. Na pasta do projeto, copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml`.
5. Abra o `.json` baixado num editor de texto e copie cada campo para a seção `[firebase]` do `secrets.toml`
   (`project_id`, `private_key_id`, `private_key`, `client_email`, `client_id`...). O `database_url` já vem
   preenchido. A `private_key` fica entre aspas, com os `\n` exatamente como estão no JSON.
6. Confira que o `.gitignore` tem a linha `.streamlit/secrets.toml` (já tem) — assim a chave nunca vai para o Git.
7. Rode `streamlit run app.py`. No topo deve aparecer **armazenamento: Firebase (Realtime Database)** e, na aba
   Ranking, o selo **Ranking online**.

### Regras de segurança do Realtime Database

O app acessa o banco pelo **SDK de administrador** (com a chave da conta de serviço), que **ignora as regras**.
Então as regras podem **bloquear tudo** para qualquer outro acesso (navegadores, apps de terceiros). No console:
**Realtime Database > Regras**, cole e publique:

```json
{
  "rules": {
    ".read": false,
    ".write": false
  }
}
```

### Como os dados ficam no banco

- `/uno/rooms/{CODIGO}`: `{version, data, updated_at}` — o estado da sala é guardado como **texto JSON** em `data`,
  porque o Realtime Database não aceita certas chaves (`.`, `$`, `#`, `[`, `]`, `/`) e apaga listas vazias e `null`.
- `/uno/presence/{CODIGO}/{jogador}`: horário do último sinal de vida de cada jogador.
- `/uno/stats/{nome}`: ranking global. A chave é o nome normalizado (minúsculas, sem acento, com caracteres proibidos
  escapados); o nome original fica no campo `name`. Bots não entram no ranking.
- `/uno/stats_games/{sala-partida}`: marca de partida já contada (cada partida soma no ranking **uma vez só**).

**Concorrência:** cada jogada roda numa `transaction()` do Realtime Database: o banco lê o valor atual, o motor do
jogo valida a jogada e só grava se ninguém tiver escrito no meio; se alguém escreveu, a transação é repetida com o
estado novo — e a validação do motor decide quem jogou primeiro (a segunda jogada fora da vez é recusada).
O ranking também usa `transaction()` (incremento atômico: duas partidas terminando juntas não perdem contagem).

## Contas (login)

Na tela inicial há **Entrar | Criar conta | Esqueci a senha**, o botão **Entrar com Google** e, mais discreto,
**Jogar como convidado** (como antes, sem conta).

- **Criar conta:** usuário (único, sem diferenciar maiúsculas e acentos), data de nascimento e senha (mínimo 6,
  com confirmação). A senha nunca é guardada: só um hash PBKDF2-SHA256 (240 mil iterações) com salt próprio.
- **Esqueci a senha:** usuário + data de nascimento certos permitem definir uma senha nova. Depois de 5 erros em
  15 minutos o formulário bloqueia por 15 minutos (o login também).
- **Continuar logado:** ao entrar, o navegador guarda um cookie `uno_sess` (30 dias); no banco fica só o hash dele.
  **Sair** apaga o cookie e invalida a sessão. Trocar a senha derruba as sessões antigas.
- **Voltar para a sala:** a conta lembra a sala em que você está. Fechou a aba? Entre de novo e clique em
  **Voltar para a sala X** — você volta ao mesmo lugar, com as mesmas cartas. Entrar de novo pelo código também
  devolve o mesmo lugar. Logado, o nome vem da conta (não precisa digitar).
- **Ranking:** quem está logado soma pela conta (para contas com senha a chave é a mesma do nome antigo, então as
  estatísticas antigas continuam valendo).

No banco: `/uno/users/{usuario}` (contas; Google em `/uno/users/g_{id}`), `/uno/sessions/{hash}` e
`/uno/limits/...` (tentativas erradas).

### Login com Google (passo a passo)

O app usa o login nativo do Streamlit (`st.login`, padrão OpenID Connect). Sem a seção `[auth]` nos secrets o botão
aparece desativado e o resto funciona normalmente.

1. **Firebase Console** > projeto `baralhoflocloriobr` > **Authentication** > **Sign-in method** > ative **Google**.
   Isso cria automaticamente um cliente OAuth no Google Cloud.
2. **Google Cloud Console** (mesmo projeto) > **APIs e serviços** > **Credenciais** > clique em
   **Web client (auto created by Google Service)**.
3. Em **URIs de redirecionamento autorizados**, adicione:
   - `http://localhost:8501/oauth2callback`
   - `https://SEU-APP.streamlit.app/oauth2callback` (troque pelo endereço do seu app)
   e salve.
4. Na mesma tela, copie o **ID do cliente** e a **Chave secreta do cliente**.
5. Gere um segredo aleatório para o cookie: `python -c "import secrets; print(secrets.token_hex(32))"`.
6. Preencha no `.streamlit/secrets.toml` (veja o exemplo em `.streamlit/secrets.toml.example`):

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"   # no Streamlit Cloud: https://SEU-APP.streamlit.app/oauth2callback
cookie_secret = "o-segredo-aleatorio-do-passo-5"

[auth.google]
client_id = "....apps.googleusercontent.com"
client_secret = "..."
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

7. Reinicie o app. Precisa do pacote `Authlib` (já está no `requirements.txt`).

A conta Google vira um usuário com o nome do Google (dá para editar em **Conta**, no topo) e não usa senha.

## Publicar no Streamlit Community Cloud

1. Suba o repositório para o GitHub (sem `secrets.toml`, sem `.data/`, sem o JSON da conta de serviço).
2. Em https://share.streamlit.io > **Create app** > escolha o repositório, branch e `app.py`.
3. Em **Advanced settings**, escolha **Python 3.12** (versão mais testada pelos pacotes do Google/Firebase
   na nuvem) e cole o conteúdo do seu `secrets.toml` (seção `[firebase]`, com o `database_url`) no campo **Secrets**.
4. Deploy! Compartilhe o link do app; os jogadores criam/entram em salas pelo código.

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

A suíte (`tests/`) cobre:

- `test_engine.py` — baralho de 108 cartas, legalidade, Pular/Inverter/+2/+4 (com desafio), Inverter com 2 jogadores,
  comprar-e-jogar, reembaralhar o descarte, UNO! e denúncia (+2), pontuação e fim de rodada;
- `test_storage_local.py` — CRUD, transações, conflito de versão, escritas concorrentes (threads e processos),
  reconexão por token, presença, ranking, escolha automática do backend;
- `test_rooms.py` — criar/entrar, máximo de 6, nomes repetidos, começar, sair, troca de anfitrião, bots,
  pular jogador ausente, bot assumindo quem caiu;
- `test_bots_sim.py` — centenas de partidas só com bots (2–6 jogadores): sempre terminam e as 108 cartas se conservam;
- `test_stats.py` — estatísticas da partida até o ranking;
- `test_firebase_fake.py` — `FirebaseBackend` com um Firestore falso em memória (transações, conflitos, incrementos);
- `test_rtdb_fake.py` — `RTDBBackend` com um Realtime Database falso (transações com ETag, jogadas concorrentes,
  ranking idempotente, bots fora do ranking, nomes com caracteres proibidos), sem rede;
- `test_ui_theme.py` — nome novo, nenhum emoji no projeto, favicon, logo SVG válido, ícones, efeitos que tocam uma
  vez só, chegada/saída de jogadores, cartas vivas e visualização ampliada;
- `test_cards_ui.py` — SVG válido para todas as cartas, bestiário, efeitos e sons;
- `test_avatars.py` — personagens: SVG válido sem emoji, escolha ao criar/entrar, conflito, troca no lobby,
  bloqueio depois do início, chaves antigas;
- `test_duels.py` — duelo de biomas: matriz 4x4 completa, não mexe no jogo, toca uma vez por jogada;
- `test_accounts.py` — hash de senha, cadastro único (inclusive concorrente no RTDB falso), login, redefinição,
  limite de tentativas, sessões, conta Google, volta à sala pela conta, ranking por conta, app sem `[auth]`;
- `test_app.py` — testes da interface com `streamlit.testing.v1.AppTest` (carregar, criar sala, bots, começar,
  jogar uma partida inteira, entrar por código, reconectar pelo link).

## Estrutura

```
app.py                  # app Streamlit (telas, mesa ao vivo com st.fragment)
game/engine.py          # regras do UNO (puro, sem Streamlit)
game/rooms.py           # salas, anfitrião, bots, reconexão, estatísticas
game/avatars.py         # personagens escolhíveis (dados) e chaves antigas
game/accounts.py        # contas, senhas (hash), sessões, vínculo com salas
game/bots.py            # IA dos bots + simulação
game/cards.py           # personagens e arte SVG das cartas
storage/local.py        # arquivos JSON + trava de arquivo
storage/rtdb.py         # Firebase Realtime Database (firebase-admin)
storage/firebase.py     # Cloud Firestore (firebase-admin)
ui/render.py            # HTML da mesa, bestiário, ranking, regras
ui/logo.py              # logo animado UNO FOLCLÓUNO (SVG)
ui/icons.py             # ícones e avatares SVG originais
ui/effects.py           # animações (uma vez por evento), sons e visualização ampliada
ui/duels.py             # duelo de biomas (16 combinações)
ui/styles.py            # CSS e keyframes
assets/favicon.svg|png  # ícone da página (gerado por tools/make_favicon.py)
tests/                  # pytest
.streamlit/config.toml  # tema
.streamlit/secrets.toml.example
```

Variáveis de ambiente opcionais: `UNO_BACKEND=local` (força o modo local), `UNO_DATA_DIR` (pasta dos dados locais),
`UNO_BOT_DELAY` (segundos entre jogadas de bot), `UNO_POLL` (intervalo de atualização da mesa).
