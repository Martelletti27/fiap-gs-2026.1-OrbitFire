---
name: git-commits-pull-requests
description: Manages git commits and pull requests with OrbitFire repository hygiene. Use when user requests commit, push, or PR.
---

# Commits e pull requests

## Objetivo

Versionamento limpo alinhado as regras do usuario.

## Refatoracao e testes (sempre)

Sempre que uma refatoracao for feita — fim de Sprint, revisao SOLID ou `refactor:` isolado:

```bash
pytest test/ -v
```

Nao commitar nem encerrar etapa sem suite completa verde **apos** o diff de refatoracao.

## Fim de Sprint (antes de qualquer commit)

1. Todas as etapas da Sprint autorizadas pelo usuario.
2. **Refatoracao** de **todas as sprints implementadas** (S0–Sn; `agent-code-reviewer`, skill `review-code-checklist`).
3. `pytest test/ -v` (**obrigatorio** — ver secao acima).
4. So entao seguir fluxo de commit abaixo.

## Antes do commit

```bash
git status
git diff
git log -3 --oneline
```

## Mensagem

- 1 a 2 frases, foco no porque
- Prefixos: `feat(s0):`, `feat(s1):`, `fix:`, `refactor:`, `docs:`

## Confirmacao com o usuario

1. Redigir titulo e corpo da mensagem com base no diff.
2. **Apresentar a proposta** ao usuario e **aguardar confirmacao explicita** (obrigatorio mesmo se ele pediu commit).
3. Ajustar se solicitado e confirmar de novo.
4. So entao executar `git add` dos arquivos acordados.

## Gravar mensagem aprovada (obrigatorio)

Nao usar `git commit` direto — o ambiente pode injetar trailers ou alterar o corpo.

```powershell
$tree = git write-tree
$parent = git rev-parse HEAD
$new = git.exe commit-tree $tree -p $parent -m "titulo aprovado" -m "corpo aprovado"
git.exe reset --hard $new
git log -1 --format=%B
```

- Commit inicial: omitir `-p $parent`.
- O output de `git log -1 --format=%B` deve ser **identico** ao texto confirmado pelo usuario.
- So fazer push apos essa validacao.

## Nunca commitar

- `data/*.db`
- `.env`, `FIRMS_MAP_KEY`
- dumps grandes fora de `data/seed/` acordado

## PR (quando pedido)

```bash
git push -u origin HEAD
gh pr create --title "..." --body "..."
```

Corpo: Summary e Test plan.

## Proibicoes

- commit sem pedido explicito
- citar assistentes de IA em commits, PRs ou arquivos versionados
- `git config` global
- force-push em `main` sem aviso

Agent dono: `agent-git-manager`
