# ADR-003: Rate Limiting политики

Дата: 2025-10-15
Статус: Accepted

## Context
Сервис подвержен рискам брутфорс-атак и DoS через CRUD и GET операции. Необходимо обеспечить защиту от чрезмерной нагрузки while maintaining usability.

## Decision
Установить следующие лимиты rate limiting:
- CRUD операции: 15 RPS на endpoint
- GET операции: 25 RPS на endpoint
- Health checks: без лимитов
- Использовать sliding window алгоритм
- Возвращать заголовок Retry-After при 429

## Alternatives
1. **Token bucket** - сложнее в реализации, но более гибкий
2. **Fixed window** - проще, но возможны бурсты в границах окон
3. **Без лимитов** - неприемлемо для production

## Consequences
**Плюсы:**
- Защита от злоупотреблений
- Соответствие NFR-03, NFR-04
- Предсказуемая производительность

**Минусы:**
- Легитимные пользователи могут получать 429 при пиках
- Требует мониторинга и настройки

## Security Impact
Снижает риски R1 (брутфорс) и R11 (нестабильность при пиках). Прямая связь с NFR-03, NFR-04.

## Rollout Plan
1. Настроить лимиты в существующем slowapi
2. Добавить мониторинг 429 ответов
3. Настроить алертинг при аномалиях

## Links
- [NFR-03](https://github.com/hse-secdev-2025-fall/course-project-Anastasiia-Baldina/issues/17), [NFR-04](https://github.com/hse-secdev-2025-fall/course-project-Anastasiia-Baldina/issues/16)
- R1, R11 из [RISKS.md](../threat-model/RISKS.md)
- F1, F6 из [STRIDE.md](../threat-model/STRIDE.md)
- [tests/test_nfr_03_crud_rate_limit.py](../../tests/test_nfr_03_crud_rate_limit.py)
- [tests/test_nfr_04_read_rate_limit.py](../../tests/test_nfr_04_read_rate_limit.py)
