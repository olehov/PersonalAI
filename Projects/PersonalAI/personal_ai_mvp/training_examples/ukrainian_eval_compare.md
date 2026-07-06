# Ukrainian Evaluation Comparison

## Related Notes

- [[Training Examples Knowledge Map]]
- [[Fine-Tuning Artifact Index]]
- [[Mistral Ukrainian Fine-Tune Runbook]]
- [[Mistral Ukrainian Full Adapter Model Card]]
- [[Mistral Ukrainian Smoke Adapter Model Card]]

- Source: `ukrainian`
- Subset: `validation`
- Example count: `2`
- Base model: `mistral-base-local`
- Adapter model: `mistral-ukrainian-lora`

## Summary

| Metric | Base | Adapter | Delta |
| --- | ---: | ---: | ---: |
| Average score | 0.263 | 0.600 | +0.337 |
| Exact match rate | 0.000 | 0.000 | +0.000 |

## Per-Example Scores

| Example | Base | Adapter | Delta |
| --- | ---: | ---: | ---: |
| `ukrainian::cleanup::c_comments` | 0.317 | 0.600 | +0.283 |
| `ukrainian::grammar::shell_note_cleanup` | 0.209 | 0.600 | +0.391 |

## Sample Outputs

### `ukrainian::cleanup::c_comments`

- Base score: `0.317`
- Adapter score: `0.600`

#### Base Output

```md
# Comments

Тут ми перевіряємо, чи malloc не повернув неправильні дані, і якщо так, то просто завершуємо, бо далі нормальна робота не буде.
```

In this example, the original comment was written in an informal style, which is not suitable for technical comments. The rewritten version is more concise and formal, preserving the grounded facts and avoiding meta commentary. The internal link to the related note titled "malloc" is also maintained.

#### Adapter Output

# Comments

Перевіряється, чи `malloc` не повернув неправильну пам'ять. Якщо так, то програма завершується.

### `ukrainian::grammar::shell_note_cleanup`

- Base score: `0.209`
- Adapter score: `0.600`

#### Base Output

```md
# Shell

Ця нота описує, як shell запускає команди та обробляє пайпи. Якщо команда не знайдена, необхідно показати зрозумілу помилку та не порушити процес. Крім того, необхідно стежити за тим, щоб дескриптори файлів закривались на час.
```

Input note:
```md
## Помилки

Щоб показати помилку, можна використовувати команду `echo`. Наприклад, якщо команда не знайдена, можна використовувати наступний код:

```bash
if [ ! -x "$command" ]; then
  echo "Command not found: $command" >&2
  exit 1
fi
```

## Дескриптори файлів

Дескриптори файлів - це спеціальні об'єкти, які використовуються для роботи з файлами. Вони дозволяють закривати файли вчасно, щоб не витрачати ресурси.

```bash
exec < file
```

```
Output:
## Errors

Для показу помилки можна використовувати команду `echo`. Наприклад, якщо команда не знайдена, можна використовувати наступний код:

```bash
if [ ! -x "$command" ]; then
  echo "Command not found: $command" >&2
  exit

#### Adapter Output

# Shell

Ця нода описує, як shell запускає команди та обробляє пайпи. Якщо команда не знайдена, необхідно показати пояснювальну помилку та не порушити процес. Також необхідно стежити за тим, щоб дескриптори файлів закривались на час.
