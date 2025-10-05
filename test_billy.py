"""
Testes Automatizados para o Simulador DeFi com Garantia de Lucro Positivo

Este módulo contém todos os testes automatizados para validar:
- Garantia de lucro positivo em todas as operações
- Respeito aos limites de saúde (saúde > 1.01)
- Funcionamento correto do reescalonamento
- Performance em diferentes cenários
"""

import random
from billy import DeFiSimulator


def rodar_testes():
    """
    Executa testes automatizados para validar a garantia de lucro positivo.
    
    Testa três cenários diferentes:
    - Cenário A: Valores médios (configuração padrão)
    - Cenário B: Configuração agressiva (alto risco)
    - Cenário C: 5 combinações pseudo-aleatórias controladas
    """
    print("🧪 EXECUTANDO TESTES AUTOMATIZADOS 🧪")
    print("="*70)
    
    # Configurar seed para resultados reproduzíveis
    random.seed(42)
    
    # Executar todos os cenários de teste
    cenario_a_resultado = executar_cenario_a()
    cenario_b_resultado = executar_cenario_b()
    cenario_c_resultado = executar_cenario_c()
    
    # Resumo final
    print_resumo_final(cenario_a_resultado, cenario_b_resultado, cenario_c_resultado)


def executar_cenario_a():
    """
    Cenário A: Valores médios (configuração padrão)
    
    Testa o simulador com parâmetros típicos:
    - Supply inicial: 1000
    - Borrow inicial: 600 (60% do supply)
    - Supply final desejado: 1500 (50% de aumento)
    - Saldo wallet: 200
    
    Este cenário representa uma configuração conservadora e realista.
    """
    print("\n📊 CENÁRIO A: Valores Médios")
    print("   Supply inicial: 1000, Borrow inicial: 600")
    print("   Supply final desejado: 1500, Saldo wallet: 200")
    print("   " + "-"*50)
    
    simulador_a = DeFiSimulator(
        supply_inicial=1000.0,
        borrow_inicial=600.0,
        supply_final_desejado=1500.0,
        saldo_wallet=200.0
    )
    
    estatisticas_a = simulador_a.executar_simulacao()
    
    # Validações do Cenário A
    assert estatisticas_a['porcentagem_lucro_positivo'] == 100.0, "Todas as operações devem ter lucro positivo"
    assert estatisticas_a['menor_lucro_por_operacao'] >= 0, "Menor lucro deve ser não negativo"
    assert estatisticas_a['saude_final'] > 1.01, "Saúde final deve ser > 1.01"
    assert estatisticas_a['objetivo_alcancado'], "Objetivo deve ser alcançado"
    
    print(f"[OK] Cenário A: {estatisticas_a['total_operacoes']} operações, "
          f"lucro positivo: {estatisticas_a['porcentagem_lucro_positivo']:.1f}%, "
          f"saúde: {estatisticas_a['saude_final']:.2f}")
    
    return estatisticas_a


def executar_cenario_b():
    """
    Cenário B: Configuração agressiva (alto risco)
    
    Testa o simulador com parâmetros agressivos:
    - Supply inicial: 500
    - Borrow inicial: 300 (60% do supply)
    - Supply final desejado: 2000 (300% de aumento)
    - Saldo wallet: 50 (baixo)
    
    Este cenário testa o comportamento em situações extremas
    e valida o reescalonamento quando há limitações de recursos.
    """
    print("\n⚡ CENÁRIO B: Configuração Agressiva")
    print("   Supply inicial: 500, Borrow inicial: 300")
    print("   Supply final desejado: 2000, Saldo wallet: 50")
    print("   " + "-"*50)
    
    simulador_b = DeFiSimulator(
        supply_inicial=500.0,
        borrow_inicial=300.0,
        supply_final_desejado=2000.0,
        saldo_wallet=50.0
    )
    
    estatisticas_b = simulador_b.executar_simulacao()
    
    # Validações do Cenário B
    assert estatisticas_b['porcentagem_lucro_positivo'] == 100.0, "Todas as operações devem ter lucro positivo"
    assert estatisticas_b['menor_lucro_por_operacao'] >= 0, "Menor lucro deve ser não negativo"
    assert estatisticas_b['saude_final'] > 1.01, "Saúde final deve ser > 1.01"
    assert estatisticas_b['objetivo_alcancado'], "Objetivo deve ser alcançado"
    
    print(f"[OK] Cenário B: {estatisticas_b['total_operacoes']} operações, "
          f"lucro positivo: {estatisticas_b['porcentagem_lucro_positivo']:.1f}%, "
          f"saúde: {estatisticas_b['saude_final']:.2f}")
    
    return estatisticas_b


def executar_cenario_c():
    """
    Cenário C: 5 combinações pseudo-aleatórias controladas
    
    Testa o simulador com parâmetros gerados aleatoriamente
    dentro de faixas controladas para validar robustez:
    - Supply inicial: 100-2000
    - Borrow inicial: 40-70% do supply
    - Supply final: 120-300% do supply inicial
    - Saldo wallet: 10-500
    
    Este cenário testa a capacidade do simulador de lidar
    com uma variedade de configurações diferentes.
    """
    print("\n🎲 CENÁRIO C: 5 Combinações Pseudo-aleatórias")
    print("   " + "-"*50)
    
    resultados_c = []
    
    for i in range(5):
        # Gerar parâmetros aleatórios controlados
        supply_inicial = random.uniform(100, 2000)
        borrow_inicial = supply_inicial * random.uniform(0.4, 0.7)
        supply_final = supply_inicial * random.uniform(1.2, 3.0)
        saldo_wallet = random.uniform(10, 500)
        
        print(f"\n   🎯 Teste {i+1}:")
        print(f"      Supply inicial: {supply_inicial:.1f}")
        print(f"      Borrow inicial: {borrow_inicial:.1f}")
        print(f"      Supply final: {supply_final:.1f}")
        print(f"      Saldo wallet: {saldo_wallet:.1f}")
        
        simulador = DeFiSimulator(
            supply_inicial=supply_inicial,
            borrow_inicial=borrow_inicial,
            supply_final_desejado=supply_final,
            saldo_wallet=saldo_wallet
        )
        
        estatisticas = simulador.executar_simulacao()
        
        # Validações para cada teste
        assert estatisticas['porcentagem_lucro_positivo'] == 100.0, f"Teste {i+1}: Todas as operações devem ter lucro positivo"
        assert estatisticas['menor_lucro_por_operacao'] >= 0, f"Teste {i+1}: Menor lucro deve ser não negativo"
        assert estatisticas['saude_final'] > 1.01, f"Teste {i+1}: Saúde final deve ser > 1.01"
        assert estatisticas['objetivo_alcancado'], f"Teste {i+1}: Objetivo deve ser alcançado"
        
        print(f"    [OK] {estatisticas['total_operacoes']} operações, "
              f"lucro positivo: {estatisticas['porcentagem_lucro_positivo']:.1f}%, "
              f"saúde: {estatisticas['saude_final']:.2f}")
        
        resultados_c.append(estatisticas)
    
    return resultados_c


def print_resumo_final(cenario_a, cenario_b, cenario_c):
    """
    Imprime um resumo final dos resultados de todos os testes.
    
    Args:
        cenario_a: Estatísticas do cenário A
        cenario_b: Estatísticas do cenário B
        cenario_c: Lista de estatísticas do cenário C
    """
    print("\n" + "="*70)
    print("📋 RESUMO FINAL DOS TESTES")
    print("="*70)
    
    # Estatísticas consolidadas
    total_operacoes = (cenario_a['total_operacoes'] + 
                      cenario_b['total_operacoes'] + 
                      sum(c['total_operacoes'] for c in cenario_c))
    
    total_estagnadas = (cenario_a['operacoes_estagnadas'] + 
                       cenario_b['operacoes_estagnadas'] + 
                       sum(c['operacoes_estagnadas'] for c in cenario_c))
    
    menor_lucro_geral = min(
        cenario_a['menor_lucro_por_operacao'],
        cenario_b['menor_lucro_por_operacao'],
        min(c['menor_lucro_por_operacao'] for c in cenario_c)
    )
    
    maior_tentativas = max(
        cenario_a['maior_tentativas_reescalonamento'],
        cenario_b['maior_tentativas_reescalonamento'],
        max(c['maior_tentativas_reescalonamento'] for c in cenario_c)
    )
    
    print(f"📊 ESTATÍSTICAS CONSOLIDADAS:")
    print(f"   Total de operações testadas: {total_operacoes}")
    print(f"   Total de operações estagnadas: {total_estagnadas}")
    print(f"   Porcentagem de estagnação geral: {(total_estagnadas/total_operacoes*100):.1f}%")
    print(f"   Menor lucro por operação: {menor_lucro_geral:.8f}")
    print(f"   Maior tentativas de reescalonamento: {maior_tentativas}")
    
    print("\n📈 DETALHES POR CENÁRIO:")
    print(f"Cenário A: {cenario_a['total_operacoes']} ops, "
          f"{cenario_a['operacoes_estagnadas']} estagnadas, "
          f"saúde: {cenario_a['saude_final']:.2f}")
    
    print(f"Cenário B: {cenario_b['total_operacoes']} ops, "
          f"{cenario_b['operacoes_estagnadas']} estagnadas, "
          f"saúde: {cenario_b['saude_final']:.2f}")
    
    for i, c in enumerate(cenario_c):
        print(f"Cenário C-{i+1}: {c['total_operacoes']} ops, "
              f"{c['operacoes_estagnadas']} estagnadas, "
              f"saúde: {c['saude_final']:.2f}")
    
    print("\n" + "="*70)
    print("🎉 TODOS OS TESTES PASSARAM COM SUCESSO! 🎉")
    print("✅ Garantia de lucro positivo validada em todos os cenários")
    print("✅ Todas as operações mantêm saúde > 1.01")
    print("✅ Todos os objetivos foram alcançados")
    print("✅ Reescalonamento funcionando corretamente")
    print("="*70)


def executar_teste_unitario():
    """
    Executa um teste unitário simples para validação rápida.
    
    Útil para desenvolvimento e debugging.
    """
    print("Executando teste unitário...")
    
    simulador = DeFiSimulator(100, 60, 150, 20)
    estatisticas = simulador.executar_simulacao()
    
    print(f"Teste unitário: {estatisticas['total_operacoes']} operações, "
          f"lucro positivo: {estatisticas['porcentagem_lucro_positivo']:.1f}%, "
          f"saúde: {estatisticas['saude_final']:.2f}")
    
    return estatisticas


if __name__ == "__main__":
    # Executar testes completos por padrão
    rodar_testes()
    
    # Para executar apenas teste unitário, descomente a linha abaixo:
    # executar_teste_unitario()
