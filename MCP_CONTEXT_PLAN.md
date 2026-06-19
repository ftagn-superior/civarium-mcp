# План обогащения civarium-mcp контекстом для агентов

## Цель

Добавить в `civarium-mcp` слой доменного контекста, чтобы агенты лучше понимали
Civarium, игровой цикл, доступные действия, структуру входных и выходных данных,
а также правила и ограничения мира.

Контекст должен помогать агенту принимать игровые решения, но не должен
противоречить текущему HTTP-контракту Civarium backend. Если правило или поле еще
не реализовано в backend, оно должно быть явно помечено как planned/design rule,
а не как доступная механика.

## Текущее состояние

- Адаптер является локальным stdio MCP server поверх agent-owner HTTP API.
- Сервер экспонирует только пять tools:
  - `get_active_round`
  - `get_visible_state`
  - `submit_command`
  - `list_my_commands`
  - `wait_next_round`
- README и Hermes example сейчас явно фиксируют отсутствие MCP prompts и MCP
  resources.
- Тесты закрепляют, что `list_prompts()` и `list_resources()` возвращают пустые
  списки.

## Принципы организации

1. Короткий стабильный контекст держать в server-level instructions.
2. Описания конкретных действий держать рядом с MCP tools.
3. Описания входных и выходных моделей держать рядом с Pydantic schemas.
4. Длинные справочные материалы, схемы и правила мира отдавать как MCP resources.
5. MCP prompts использовать для игровых сценариев и workflow, а не как основной
   справочник.
6. Не раскрывать admin/service возможности: адаптер должен оставаться
   agent-owner only.
7. Свежие чтения состояния, ожидание и действия оставлять MCP tools: resources
   могут дополнять их, но не должны становиться единственным способом получить
   актуальный state перед решением.
8. Статичные и session-bound правила отдавать как resources, потому что это
   адресуемый контекст, который host/client может явно выбрать, закешировать или
   вложить в разговор.
9. Prompts должны объяснять агенту, как использовать tools/resources в конкретном
   игровом сценарии, а не дублировать весь справочник правил.

Короткая эвристика:

```text
rules/docs/catalogs      -> MCP resources
thinking workflows       -> MCP prompts
fresh reads/actions/wait -> MCP tools
```

## Этап 1: Server Instructions

Добавить файл:

```text
src/civarium_mcp/instructions.py
```

В нем определить `CIVARIUM_INSTRUCTIONS` с кратким описанием:

- Civarium - open-world пошаговая стратегия, где государства/агенты борются за
  влияние и мировое господство.
- Агент наблюдает только доступную ему часть мира через `VisibleState`.
- Агент воздействует на мир через команды.
- Команды не меняют мир немедленно: они принимаются backend, валидируются и
  исполняются при продвижении раунда.
- Состояние мира меняется через события и projection pipeline.

Подключить instructions в `src/civarium_mcp/server.py`:

```python
server = FastMCP(
    name="civarium",
    instructions=CIVARIUM_INSTRUCTIONS,
    log_level="INFO",
)
```

Это изменение не требует включать prompts/resources и не меняет список tools.

## Этап 2: Tool Descriptions

Усилить descriptions в `src/civarium_mcp/tools.py`.

Для каждого tool описать не только техническое действие, но и игровую роль:

- `get_active_round`: возвращает текущий раунд, для которого агент может
  принимать решения.
- `get_visible_state`: возвращает наблюдаемую агентом часть мира.
- `submit_command`: передает управляющую команду агента; команда является
  намерением, а не мгновенной мутацией мира.
- `list_my_commands`: показывает команды агента, уже принятые backend в
  указанном раунде.
- `wait_next_round`: ожидает смены активного раунда, но не продвигает сессию.

Также уточнить `Field(description=...)` для параметров:

- `round_id`
- `client_command_id`
- `command_type`
- `payload`
- `timeout_seconds`

## Этап 3: Model Descriptions

Расширить описания в `src/civarium_mcp/schemas.py`.

Добавить `Field(description=...)` к полям output-моделей:

- `AgentRoundOutput`
- `VisibleStateOutput`
- `EntityLibraryOutput`
- `CommandReceivedOutput`
- `AcceptedCommandOutput`
- `AcceptedCommandListOutput`
- `WaitNextRoundOutput`

Особенно важно пояснить:

- `entities` - словарь библиотек видимых сущностей по типу сущности.
- `structures` - готовые построенные здания в игровом мире.
- `constructions` - незавершенные стройки, которые могут стать structures после
  нескольких раундов.
- `checks` - результаты backend-валидации команды.
- `is_valid` - допущена ли команда к дальнейшему исполнению.

## Этап 4: MCP Resources

Добавить файл:

```text
src/civarium_mcp/resources.py
```

Регистрировать resources через `server.resource(...)`.

### Базовые справочные resources

Первым шагом добавить resources для правил, справочников и схем, применимых к
текущей игре или текущей сессии.

Предлагаемый набор URI:

```text
civarium://guide/overview
civarium://guide/game-loop
civarium://session/current/rules
civarium://session/current/mechanics
civarium://session/current/command-catalog
civarium://session/current/victory-conditions
civarium://session/current/entity-schema
civarium://commands/construction_start
civarium://schemas/visible-state
civarium://schemas/command-receipt
civarium://rules/world
```

Назначение resources:

- `overview`: общий обзор игры, целей и роли агента.
- `game-loop`: описание цикла round/command/event/state.
- `session/current/rules`: правила, реально действующие для текущей сессии.
- `session/current/mechanics`: игровые механики текущей сессии, включая раунды,
  видимость, команды, события и применение projection pipeline.
- `session/current/command-catalog`: список доступных command types и краткое
  описание их игрового смысла.
- `session/current/victory-conditions`: условия победы, scoring и критерии
  долгосрочного успеха, если они доступны в backend/session contract.
- `session/current/entity-schema`: справочник видимых типов сущностей и их
  полей.
- `construction_start`: shape payload, смысл команды и ожидаемый результат.
- `visible-state`: структура видимого состояния.
- `command-receipt`: структура ответа после отправки команды.
- `world`: актуальные правила и ограничения мира.

Если часть правил еще не реализована в backend, resource должен явно маркировать
такие блоки как planned/design notes, а не как действующую механику.

### Resource templates

После базовых resources можно добавить templates для параметризованного чтения:

```text
civarium://commands/{command_type}
civarium://schemas/{schema_name}
civarium://rules/{rule_set}
```

Это позволит не плодить отдельную регистрацию на каждый command type или schema,
если backend начнет отдавать каталог правил/команд динамически.

### Динамические resources

Динамические resources возможны, но должны быть вторым шагом после справочных
resources. Их задача - дать host/client адресуемые snapshots, а не заменить
существующие tools.

Потенциальные URI:

```text
civarium://agent/round/current
civarium://agent/state/visible
civarium://round/{round_id}/visible-state
civarium://round/{round_id}/commands/my
```

Рекомендация:

- `get_active_round` оставить tool, потому что агенту часто нужен свежий round
  прямо перед действием.
- `get_visible_state` оставить tool, потому что это явное свежее чтение перед
  принятием решения.
- `wait_next_round` оставить tool, потому что это активное ожидание/поллинг, а
  не просто чтение документа.
- `submit_command` всегда оставлять tool, потому что это действие.
- Immutable или nearly-immutable snapshots по `round_id` лучше подходят для
  resources, чем mutable alias вида `current`.

Важно: включение resources меняет публичный контракт MCP server. Нужно обновить:

- README
- `examples/hermes.config.yaml`
- тесты, которые сейчас ожидают пустой список resources

## Этап 5: MCP Prompts

Добавить prompts только после появления resources.

Предлагаемый файл:

```text
src/civarium_mcp/prompts.py
```

Предлагаемые prompts:

```text
civarium_onboarding
analyze_current_round
draft_commands
review_command
explain_command_result
wait_and_review_next_round
plan_strategy
```

Назначение prompts:

- `civarium_onboarding`: объяснить пользователю механику текущей сессии,
  опираясь на rules/resources.
- `analyze_current_round`: получить текущий раунд и видимое состояние, выделить
  угрозы, возможности и ограничения.
- `draft_commands`: подготовить один или несколько вариантов команд на раунд, но
  не отправлять их без явного подтверждения пользователя/host policy.
- `review_command`: проверить proposed command payload против известных правил,
  command catalog и schema resource.
- `explain_command_result`: разобрать receipt после `submit_command`, особенно
  `is_valid=false` и `checks`.
- `wait_and_review_next_round`: дождаться нового раунда и сравнить состояние.
- `plan_strategy`: составить стратегический план на несколько раундов с учетом
  victory conditions и текущего видимого состояния.

Prompts должны быть workflow-сценариями, а не заменой resources.
Они могут ссылаться на resources или встраивать server-managed resource content,
если SDK/host это поддерживает.

Prompts не должны автоматически выполнять destructive/action tools. Для
`submit_command` prompt должен готовить draft и явно отделять план от отправки.

## Этап 6: README, Hermes Config, Tests

После добавления resources/prompts обновить документацию:

- README: убрать утверждение, что prompts/resources не экспонируются, или
  заменить его на точное описание доступных prompts/resources.
- `examples/hermes.config.yaml`: поменять `resources: false` и/или
  `prompts: false`, если Hermes должен видеть новые capabilities.
- Tests:
  - проверить наличие instructions, если тестовый API FastMCP это позволяет;
  - проверить расширенные descriptions tools;
  - проверить список resources;
  - проверить чтение ключевых resources;
  - проверить, что динамические resources, если они включены, используют тот же
    agent-only gateway и не раскрывают `agent_id`/admin данные;
  - проверить список prompts, если prompts включены;
  - проверить, что prompts не подменяют action tools и не отправляют команды
    без явного вызова `submit_command`.

## Рекомендуемый порядок внедрения

1. Добавить server instructions.
2. Улучшить tool descriptions и schema field descriptions.
3. Добавить справочные MCP resources для правил, command catalog и схем.
4. Обновить README, Hermes example и tests для resources.
5. Добавить MCP prompts для игровых workflow.
6. Обновить README, Hermes example и tests для prompts.
7. Отдельно оценить динамические resources для current state/round snapshots,
   не удаляя существующие tools.

Такой порядок позволяет сначала улучшить качество контекста без изменения
набора MCP capabilities, а затем осознанно расширить публичный контракт сервера.
