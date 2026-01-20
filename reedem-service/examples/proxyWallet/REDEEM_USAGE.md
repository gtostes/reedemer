# Redeem Script - Usage Guide

## Como usar

O script `redeem.ts` agora aceita argumentos da linha de comando para fazer redeem de forma mais fácil.

### Sintaxe

```bash
ts-node redeem.ts <conditionId> [negRisk] [yesAmount] [noAmount]
```

### Argumentos

- **conditionId** (obrigatório): O condition ID do mercado
- **negRisk** (opcional): `true` ou `false` (default: `false`)
- **yesAmount** (opcional): Quantidade de tokens YES para redeem em neg risk (default: `1`)
- **noAmount** (opcional): Quantidade de tokens NO para redeem em neg risk (default: `1`)

### Exemplos

#### 1. Redeem simples (não neg risk)
```bash
ts-node redeem.ts 0x930381b7efcf46597e2bc8f324f6f3dc19a286d7344d5d745687261366bee3ec
```

#### 2. Redeem neg risk com valores padrão
```bash
ts-node redeem.ts 0x930381b7efcf46597e2bc8f324f6f3dc19a286d7344d5d745687261366bee3ec true
```

#### 3. Redeem neg risk com valores customizados
```bash
ts-node redeem.ts 0x930381b7efcf46597e2bc8f324f6f3dc19a286d7344d5d745687261366bee3ec true 100 50
```

### Redeem em Lote

Para fazer redeem de múltiplas posições, você pode criar um script bash:

```bash
#!/bin/bash

# redeem_all.sh
ts-node redeem.ts 0x930381b7efcf46597e2bc8f324f6f3dc19a286d7344d5d745687261366bee3ec false
ts-node redeem.ts 0x123abc...def true 10 10
ts-node redeem.ts 0x456xyz...uvw false
```

Torne executável:
```bash
chmod +x redeem_all.sh
./redeem_all.sh
```

### Integração com Python

Você pode chamar o script do Python:

```python
import subprocess

condition_ids = [
    "0x930381b7efcf46597e2bc8f324f6f3dc19a286d7344d5d745687261366bee3ec",
    "0x123abc...def",
]

for cid in condition_ids:
    result = subprocess.run(
        ["ts-node", "redeem.ts", cid, "false"],
        cwd="/path/to/reedem-service/examples/proxyWallet",
        capture_output=True,
        text=True
    )
    print(f"Result: {result.stdout}")
```

### Notas

- ⚠️ Certifique-se de ter MATIC suficiente para pagar o gas
- ✅ O script agora usa gas dinâmico (mínimo 25 Gwei no Polygon)
- 🔒 Sempre teste com valores pequenos primeiro
