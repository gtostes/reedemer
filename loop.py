#!/usr/bin/env python3
"""
Loop automático de redeem para Polymarket.
Checa a cada 1 segundo por novas posições redeemable e executa redeem automaticamente.
"""

import os
import sys
import time
import subprocess
import requests
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Set
from pathlib import Path

# Obtém o diretório do script atual
SCRIPT_DIR = Path(__file__).parent.absolute()

# Adiciona o py-clob-client ao path (relativo ao workspace)
sys.path.insert(0, str(SCRIPT_DIR.parent / 'py-clob-client'))

from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

load_dotenv()

# Configurações
POLYMARKET_DATA_API = "https://data-api.polymarket.com"
REDEEM_SCRIPT_PATH = str(SCRIPT_DIR / "reedem-service" / "examples" / "proxyWallet" / "redeem.ts")
CHECK_INTERVAL = 1  # segundos

# Conjunto para rastrear conditionIds já processados (evita duplicatas)
processed_conditions: Set[str] = set()


def log(message: str):
    """Log com timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def get_redeemable_positions(proxy_address: str) -> List[Dict]:
    """
    Busca todas as posições redeemable da proxy wallet.
    
    Args:
        proxy_address: Endereço da proxy wallet
        
    Returns:
        Lista de posições redeemable
    """
    try:
        params = {
            "user": proxy_address,
            "sizeThreshold": "0.01",
            "limit": "500"
        }
        
        response = requests.get(
            f"{POLYMARKET_DATA_API}/positions",
            params=params,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if not response.ok:
            log(f"❌ Erro ao buscar posições: {response.status_code}")
            return []
        
        all_positions = response.json()
        redeemable = [p for p in all_positions if p.get('redeemable', False)]
        
        return redeemable
    
    except Exception as e:
        log(f"❌ Erro ao buscar posições: {e}")
        return []


def execute_redeem(condition_id: str, neg_risk: bool) -> bool:
    """
    Executa o redeem via subprocess do TypeScript.
    
    Args:
        condition_id: Condition ID do mercado
        neg_risk: Se é neg risk market
        
    Returns:
        True se sucesso, False se falhou
    """
    try:
        log(f"🔄 Executando redeem para {condition_id[:16]}... (negRisk={neg_risk})")
        
        # Monta comando
        cmd = [
            "ts-node",
            REDEEM_SCRIPT_PATH,
            condition_id,
            str(neg_risk).lower()
        ]
        
        # Executa comando
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(REDEEM_SCRIPT_PATH),
            capture_output=True,
            text=True,
            timeout=120  # 2 minutos timeout
        )
        
        if result.returncode == 0:
            log(f"✅ Redeem executado com sucesso!")
            # Procura pelo hash da transação no output
            for line in result.stdout.split('\n'):
                if 'hash' in line.lower() or '0x' in line:
                    log(f"   {line.strip()}")
            return True
        else:
            log(f"❌ Redeem falhou (exit code: {result.returncode})")
            if result.stderr:
                log(f"   Erro: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        log(f"⏰ Timeout ao executar redeem para {condition_id[:16]}...")
        return False
    except Exception as e:
        log(f"❌ Erro ao executar redeem: {e}")
        return False


def main():
    """Loop principal"""
    log("🚀 Iniciando loop de redeem automático...")
    
    # Configura cliente
    host = "https://clob.polymarket.com"
    key = os.getenv("PK")
    proxy_address = os.getenv("BROWSER_ADDRESS")
    
    if not key or not proxy_address:
        log("❌ Erro: PK e BROWSER_ADDRESS devem estar no .env")
        return
    
    # Autentica
    try:
        client = ClobClient(host, key=key, chain_id=POLYGON, signature_type=1)
        client.set_api_creds(client.create_or_derive_api_creds())
        log(f"✅ Cliente autenticado")
        log(f"� Main Wallet: {client.signer.address()}")
        log(f"🔑 Proxy Wallet: {proxy_address}")
    except Exception as e:
        log(f"❌ Erro ao autenticar: {e}")
        return
    
    log(f"⏱️  Checando a cada {CHECK_INTERVAL}s por novas posições...")
    log(f"📝 Processados até agora: {len(processed_conditions)}")
    log("="*80)
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            
            # Busca posições redeemable
            redeemable = get_redeemable_positions(proxy_address)
            
            # Filtra apenas as que ainda não foram processadas
            new_redeemable = [
                p for p in redeemable 
                if p['conditionId'] not in processed_conditions
            ]
            
            if new_redeemable:
                log(f"🎯 {len(new_redeemable)} nova(s) posição(ões) redeemable encontrada(s)!")
                
                for position in new_redeemable:
                    condition_id = position['conditionId']
                    neg_risk = position.get('negativeRisk', False)
                    title = position.get('title', 'N/A')
                    size = position.get('size', 0)
                    value = position.get('currentValue', 0)
                    
                    log(f"\n📊 Nova posição:")
                    log(f"   Título: {title}")
                    log(f"   Outcome: {position.get('outcome', 'N/A')}")
                    log(f"   Size: {size}")
                    log(f"   Valor: ${value:.2f}")
                    log(f"   Condition ID: {condition_id}")
                    
                    # Executa redeem
                    success = execute_redeem(condition_id, neg_risk)
                    
                    if success:
                        # Marca como processado
                        processed_conditions.add(condition_id)
                        log(f"✅ Condition {condition_id[:16]}... marcado como processado")
                    else:
                        log(f"⚠️  Condition {condition_id[:16]}... NÃO foi processado (será tentado novamente)")
                    
                    log("-" * 80)
                    
                    # Aguarda 2s entre redeems para não sobrecarregar
                    time.sleep(2)
            else:
                # Só loga a cada 10 iterações para não poluir
                if iteration % 10 == 0:
                    log(f"⚪ Nenhuma nova posição redeemable (total: {len(redeemable)}, processados: {len(processed_conditions)})")
            
            # Aguarda antes da próxima checagem
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        log("\n⏹️  Loop interrompido pelo usuário")
        log(f"📊 Resumo:")
        log(f"   Total de redeems executados: {len(processed_conditions)}")
        log(f"   Condition IDs processados:")
        for cid in processed_conditions:
            log(f"     - {cid}")
    except Exception as e:
        log(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
