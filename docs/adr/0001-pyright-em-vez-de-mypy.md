# ADR 0001 — Pyright em vez de mypy para checagem de tipos

- **Status:** aceito
- **Data:** agosto de 2026
- **Contexto do projeto:** backend Python (FastAPI + SQLAlchemy 2.0), Sprint 0

## Contexto

O projeto adota tipagem explícita como princípio de engenharia, com checagem de
tipos rodando no CI a cada push/PR. A primeira tentativa usou **mypy**.

Os modelos SQLAlchemy do projeto estão escritos no estilo clássico
(`id = Column(UUID(as_uuid=True), ...)`), e não no estilo tipado
`Mapped[...] / mapped_column(...)` introduzido no SQLAlchemy 2.0. Nesse estilo,
o mypy infere o tipo do atributo como `Column[...]` em vez do tipo Python da
coluna. Consequência prática: qualquer código que lê ou escreve um atributo de
modelo (`company.cnpj`, construção de `Company(...)`, retorno de rota tipado com
schema Pydantic) gera erro de tipo mesmo estando correto em tempo de execução.

As saídas disponíveis eram todas ruins:

1. Espalhar `# type: ignore` pelos modelos e rotas — ruído que anula o valor da checagem
2. Instalar e configurar o plugin `sqlalchemy2-stubs` / `sqlalchemy.ext.mypy` — o plugin de mypy do SQLAlchemy está **descontinuado** na linha 2.0
3. Migrar todos os 7 modelos para `Mapped`/`mapped_column` ainda no Sprint 0 — trabalho real de refatoração, com migrations já aplicadas, antes de existir qualquer funcionalidade de produto

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| mypy strict + migração imediata para `Mapped`/`mapped_column` | Custo alto no Sprint 0, sem ganho de produto; adiável sem risco |
| mypy + `# type: ignore` nos pontos de atrito | Silencia erros reais junto com os falsos; degrada com o tempo |
| Nenhuma checagem de tipos por enquanto | Contraria o princípio de tipagem explícita e deixa a dívida crescer |

## Decisão

Usar **Pyright em modo `basic`** como checador de tipos do backend, configurado
em `backend/pyproject.toml`:

```toml
[tool.pyright]
include = ["app"]
exclude = ["venv", "tests"]
typeCheckingMode = "basic"
```

O Pyright trata os atributos de modelos SQLAlchemy no estilo clássico com muito
mais tolerância, sem exigir plugin nem anotações defensivas, e ainda captura a
classe de erro que interessa hoje: atributo inexistente, argumento errado,
`None` não tratado, import quebrado.

O CI roda `pyright app` como passo obrigatório, junto de `ruff check .` e `pytest`.

## Consequências

**Positivas**
- Checagem de tipos verde e útil desde o Sprint 0, sem `type: ignore` espalhado
- Sem dependência de plugin descontinuado
- Mesmo checador usado pelo editor (VS Code/Pylance), então erro no CI é erro na tela

**Negativas / dívida registrada**
- O modo `basic` é menos rigoroso que `mypy --strict`: código sem anotação
  nenhuma passa silenciosamente. Mitigação: anotar assinaturas por convenção,
  não por obrigação da ferramenta.
- Fica registrada a **dívida técnica** de migrar os modelos para
  `Mapped`/`mapped_column`. Quando isso acontecer, vale reavaliar subir o
  Pyright para `standard`/`strict` — ou reconsiderar o mypy.
- `pyright` é distribuído via wrapper que precisa de Node.js; por isso
  `nodeenv` e `pyright` estão fixados em `backend/requirements.txt`.

## Revisão

Reavaliar esta decisão quando os modelos migrarem para o estilo tipado do
SQLAlchemy 2.0.

---

## Atualização — agosto de 2026: a dívida foi paga

Ao implementar o serviço de scan (Sprint 2), o Pyright passou a acusar 13 erros
do tipo `Não é possível atribuir o atributo "status" para a classe "Scan"`. A
causa é a mesma que motivou este ADR, agora aparecendo pelo outro lado: o estilo
clássico tipa o atributo como `Column[str]`, o que tolera *leitura* mas rejeita
*atribuição* — e o worker precisa fazer `scan.status = ScanStatusEnum.completed`.

Não havia como escrever a lógica de negócio sem resolver isso. Os 7 modelos foram
migrados para `Mapped`/`mapped_column`:

```python
# antes
status = Column(SQLEnum(ScanStatusEnum), nullable=False, default=ScanStatusEnum.pending)

# depois
status: Mapped[ScanStatusEnum] = mapped_column(
    SQLEnum(ScanStatusEnum), nullable=False, default=ScanStatusEnum.pending
)
```

**Uma migration foi necessária** — ao contrário do que se esperava. Rodar
`alembic revision --autogenerate` para conferir revelou que `Mapped[datetime]` sem
`| None` declara a coluna como `NOT NULL`, enquanto o `Column(DateTime, ...)`
original era nullable por omissão. O autogenerate propôs `alter_column(...,
nullable=False)` para os sete `created_at`/`updated_at`.

A mudança é segura e desejável (todas essas colunas têm `server_default now()`, então
nenhuma linha pode estar nula) e foi mantida na migration
`0fa4137f549d_created_at_not_null.py`.

A lição registrada no Stack (seção 7) se confirmou pelo lado positivo: rodar o
autogenerate *para conferir* — sem aplicar — foi o que revelou a diferença. A
suposição de que "mudança de anotação não mexe no schema" estava errada.

Ganho colateral: os tipos agora são os tipos reais do Python, então o Pyright
passou a pegar erros de verdade nos serviços (`scan.url` é `str`, não
`Column[str]`).

A decisão de manter o Pyright em `basic` continua valendo. Com os modelos
tipados, subir para `standard` virou uma opção real — fica registrado como o
próximo passo natural, a ser avaliado quando a cobertura de anotações do
`app/services/` estiver estável.
