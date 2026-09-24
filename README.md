# Sentinela — Backup Automatizado

Sistema open source de backup automatizado para pequenas empresas que usam
bancos de dados relacionais (**PostgreSQL** e **MariaDB/MySQL**).

Projeto Integrador · Curso Técnico · IFSC Câmpus São Lourenço do Oeste · 2026
Autor: Kauan V. Machado Deon

## Funcionalidades

| Requisito do projeto | Como o Sentinela atende |
|---|---|
| Interface para configurar a política de backup | Painel web com login: Painel, Política, Histórico, Logs e Conexão |
| Agendamento automático | Diário à meia-noite **ou** a cada *N* dias (1–30), sem intervenção manual |
| Retenção configurável (máx. 10 dias) | Exclusão automática das cópias expiradas (1–10 dias). A cópia válida mais recente nunca é apagada |
| Dump PostgreSQL e MariaDB | `pg_dump` / `mariadb-dump` (ou `mysqldump`), escolhido pelo usuário |
| Banco em outro servidor | Conexão direta ou **túnel SSH** (senha ou chave privada), com verificação da chave do host |
| Criptografia | AES-256-GCM (confidencialidade + autenticação contra adulteração) |
| Compressão | gzip, aplicada em fluxo antes da criptografia |
| Armazenamento isolado (regra 3-2-1) | Diretório dedicado, fora da aplicação (validado). Pode apontar para disco externo, NFS/SMB etc. |
| Logs detalhados por execução | Cada etapa com horário exato, no painel, em `logs/execucoes/*.log` e em `logs/sentinela.log` |
| Verificação de integridade | Após cada backup e sob demanda: SHA-256, tag GCM, gzip e marcador de fim do dump |
| Teste de restauração | Restauração pelo painel, com verificação prévia e cópia automática do estado atual (pré-restauração) |

### Pipeline de backup

```
SGBD ──dump──▶ gzip ──▶ AES-256-GCM ──▶ arquivo .part ──rename──▶ loja_20260708_000000.sql.gz.enc
                                             │
                                             └─ SHA-256 registrado + verificação completa
```

Tudo acontece em fluxo (streaming): o SQL em texto claro **nunca** é gravado em
disco, e bancos grandes não são carregados na memória.

## Requisitos

- Linux, Python 3.10+
- Cliente do SGBD instalado no servidor:
  - PostgreSQL: `pg_dump` e `psql` (pacote `postgresql-client`)
  - MariaDB/MySQL: `mariadb-dump` e `mariadb` (pacote `mariadb-client`) ou `mysqldump`/`mysql`

## Instalação

```bash
git clone https://github.com/kauandeon-dev/P.I.IFSC2026.git sentinela
cd sentinela
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

export SENTINELA_HOME=/var/lib/sentinela            # dados da aplicação (SQLite, chave, logs)
export SENTINELA_BACKUP_DIR=/var/backups/sentinela  # diretório padrão das cópias
.venv/bin/python -m sentinela serve
```

No primeiro início é criado o usuário `admin` com uma senha aleatória exibida
no terminal. Acesse `http://127.0.0.1:8080`, depois:

1. **Conexão** → escolha o SGBD, informe host, porta, banco, usuário e senha → *Testar conexão* → *Salvar*.
2. **Política de backup** → agendamento, retenção, diretório, criptografia e compressão → *Salvar política*.
3. Pronto: o agendador executa os backups sozinho. Use *Fazer backup agora* para uma cópia manual.

Para rodar como serviço, veja [`deploy/sentinela.service`](deploy/sentinela.service).

> O painel escuta em `127.0.0.1` por padrão. Para acesso remoto, publique atrás
> de um proxy reverso com HTTPS (nginx/Caddy) e defina `SENTINELA_HTTPS=1`.

### Banco em outro servidor (túnel SSH)

Na tela **Conexão**, em *Forma de acesso*, escolha **Túnel SSH** e informe o
servidor, a porta e o usuário SSH, com **senha** ou **chave privada**
(OpenSSH/PEM: ed25519, RSA ou ECDSA; senha da chave opcional).

- Em **Host/Porta do banco**, informe o endereço **visto a partir do servidor
  SSH** — normalmente `localhost` e `5432`/`3306`. A porta do banco não precisa
  ficar exposta na internet.
- O Sentinela abre um túnel (`127.0.0.1:porta-aleatória` → servidor SSH → banco)
  a cada execução e o fecha ao terminar. Os clientes `pg_dump`/`mariadb-dump`
  continuam rodando no servidor do Sentinela, e as cópias ficam nele.
- Na primeira conexão, a impressão digital do servidor SSH (`SHA256:...`) é
  registrada. Se ela mudar depois, backups e restaurações são bloqueados até a
  chave ser redefinida no painel (proteção contra man-in-the-middle).
- Senha SSH, chave privada e senha da chave são guardadas criptografadas.
- Recomendado: criar no servidor do banco um usuário SSH só para o túnel, com
  chave, e restringir no `authorized_keys`:
  `restrict,port-forwarding,permitopen="localhost:5432" ssh-ed25519 AAAA...`

### Permissões mínimas do usuário de backup

PostgreSQL (o dono do banco já basta; ou somente leitura):
```sql
CREATE ROLE backup_user LOGIN PASSWORD '...';
GRANT CONNECT ON DATABASE loja TO backup_user;
GRANT pg_read_all_data TO backup_user;   -- PostgreSQL 14+
```
Para **restaurar**, o usuário precisa poder recriar os objetos (ex.: ser o dono do banco).

MariaDB:
```sql
CREATE USER 'backup_user'@'localhost' IDENTIFIED BY '...';
GRANT SELECT, SHOW VIEW, TRIGGER, LOCK TABLES, EVENT ON loja.* TO 'backup_user'@'localhost';
-- para restaurar: GRANT ALL ON loja.* TO 'backup_user'@'localhost';
```

## Linha de comando

```bash
python -m sentinela serve               # painel web + agendador
python -m sentinela passwd admin        # altera a senha do painel
python -m sentinela backup              # backup imediato (útil em cron/scripts)
python -m sentinela decrypt ARQ.sql.gz.enc -o banco.sql   # recupera o SQL sem o painel
python -m sentinela decrypt ARQ.sql.gz.enc -o - | psql -d banco   # restauração manual
```

## Chave de criptografia (importante)

A chave mestra AES-256 é gerada no primeiro início em `$SENTINELA_HOME/sentinela.key`
(permissão 0600). Ela fica **separada** do diretório de backups: quem obtiver só
as cópias não consegue lê-las.

**Guarde uma cópia da chave fora do servidor** (cofre de senhas, pendrive guardado).
Sem ela, as cópias criptografadas não podem ser recuperadas.

## Segurança

- Senha do banco guardada criptografada (AES-GCM) no SQLite; nunca retorna pela API.
- Senhas do painel com hash (werkzeug/scrypt); bloqueio temporário após 5 tentativas.
- Cookies `HttpOnly` + `SameSite=Strict`, CSP restritiva, sem scripts inline.
- MariaDB: senha passada por arquivo temporário 0600 (não aparece no `ps`).
- Arquivos de backup com permissão 0600, diretório 0700, gravação atômica (`.part` → rename).
- Verificação antes de restaurar; dump interrompido nunca vira cópia "válida".

## Estrutura

```
sentinela/
  engine.py      backup, verificação, restauração, retenção, logs por execução
  dumpers.py     adaptadores PostgreSQL e MariaDB (pg_dump/psql, mariadb-dump/mariadb)
  tunnel.py      túnel SSH (paramiko) com verificação da chave do host
  crypto.py      AES-256-GCM em fluxo, chave mestra, segredos
  scheduler.py   agendador (diário/intervalo) e limpeza
  storage.py     SQLite (configurações, histórico, logs)
  web.py         API JSON + painel
  static/        interface (HTML/CSS/JS puro, fontes IBM Plex locais)
tests/           testes automatizados (unitários e integração com PostgreSQL/MariaDB reais)
deploy/          serviço systemd
```

## Testes

```bash
pip install pytest
python -m pytest -q tests
```

Os testes de integração usam um PostgreSQL e um MariaDB locais com o banco
`loja_producao` e o usuário `backup_user` (ver `tests/conftest.py`); se não
estiverem disponíveis, são ignorados automaticamente. Cobrem: backup nas 4
combinações de criptografia/compressão, detecção de adulteração, falha de
conexão, restauração real (PostgreSQL e MariaDB), retenção e a CLI `decrypt`.
`tests/test_ssh.py` usa um `sshd` de teste em `127.0.0.1:2222` (usuário `tunel`)
para validar o túnel com senha, chave, chave protegida, senha errada, troca da
chave do host e backup/restauração via SSH.

## Licença

MIT.
