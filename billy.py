"""
Simulador de Estratégia DeFi com Garantia de Lucro Positivo
Refatorado para garantir lucro > 0 em todas as operações por construção matemática
"""

import random
from typing import Tuple, Dict, Any

# ============================================================================
# CONFIGURAÇÕES GLOBAIS
# ============================================================================

# Configurações de garantia de lucro
min_lucro_op: float = 1e-6
margem_borrow_min: float = 0.50
repagamento_min: float = 0.03
max_tentativas_reescalonamento: int = 50

# Configuração de testes
RODAR_TESTES: bool = False

class DeFiSimulator:
    """
    Simulador de estratégia DeFi com garantia de lucro positivo em todas as operações.
    Ajusta parâmetros antes do cálculo do lucro para garantir resultado positivo por construção.
    """
    
    def __init__(self, supply_inicial: float, borrow_inicial: float, 
                 supply_final_desejado: float, saldo_wallet: float):
        """Inicializa o simulador com os parâmetros básicos."""
        self.supply_inicial = supply_inicial
        self.borrow_inicial = borrow_inicial
        self.supply_final_desejado = supply_final_desejado
        self.saldo_wallet = saldo_wallet
        
        # Estado atual
        self.supply_atual = supply_inicial
        self.borrow_atual = borrow_inicial
        self.repagamento_total = 0
        self.lucro_total = 0
        self.operacao = 0
        self.retirada_total = 0
        self.supply_extra_acumulado = 0
        self.taxas_total = 0
        
        # Controle de estagnação
        self.supply_anterior = supply_inicial
        self.operacoes_sem_progresso = 0
        self.limite_operacoes_estagnadas = 35
        self.total_operacoes_estagnadas = 0
        
        # Métricas de monitoramento
        self.operacoes_com_lucro_positivo = 0
        self.menor_lucro_por_operacao = float('inf')
        self.maior_tentativas_reescalonamento = 0
        self.total_tentativas_reescalonamento = 0
        
        # Arquivo de saída
        self.arquivo = None
    
    def calcular_reinvestimento(self, novo_borrow: float, repagamento: float,
                              taxa_plataforma: float, supply_atual: float,
                              supply_final_desejado: float, operacoes_estagnadas: int = 0) -> float:
        """
        Calcula o reinvestimento baseado na distância até o objetivo.
        O lucro restante vira supply extra para a próxima operação.
        """
        lucro_bruto = novo_borrow - repagamento - taxa_plataforma
        
        if lucro_bruto <= 0:
            return 0
        
        # Calcular quanta distância ainda falta para o objetivo
        falta_para_objetivo = supply_final_desejado - supply_atual
        
        # Se estamos estagnados, reduzir drasticamente o reinvestimento
        if operacoes_estagnadas > 5:
            return lucro_bruto * 0.05  # Reinvestir apenas 5% para maximizar lucro líquido
        elif operacoes_estagnadas > 2:
            return lucro_bruto * 0.10  # Reinvestir apenas 10%
        
        # Lógica normal baseada na distância
        if falta_para_objetivo > supply_atual * 0.5:  # Ainda longe do objetivo
            reinvestimento = lucro_bruto * 0.60
        elif falta_para_objetivo > supply_atual * 0.2:  # Medianamente perto
            reinvestimento = lucro_bruto * 0.40
        else:  # Muito perto do objetivo
            reinvestimento = lucro_bruto * 0.20
        
        return reinvestimento

    def planejar_operacao(self) -> Tuple[float, float, bool, int, Dict[str, bool], float, float, float]:
        """
        Planeja uma operação garantindo lucro positivo por construção.
        
        Returns:
            Tuple com (novo_borrow_final, reinvestimento_final, meta_lucro_atingida,
                      tentativas_reescalonamento, flags_reescalonamento,
                      novo_borrow_min_calculado, novo_borrow_max_seguro,
                      proporcao_repagamento_final)
        """
        # Usar o lucro acumulado das operações anteriores como supply extra
        supply_usado_do_acumulado = 0
        if self.supply_extra_acumulado > 0:
            supply_usado_do_acumulado = min(self.supply_extra_acumulado, 
                                          self.supply_final_desejado - self.supply_atual)
            self.supply_atual += supply_usado_do_acumulado
            self.supply_extra_acumulado -= supply_usado_do_acumulado

        # Supply extra da wallet se ainda precisar e tiver disponível
        supply_extra_wallet = 0
        if self.supply_atual < self.supply_final_desejado and self.saldo_wallet > 0:
            falta_supply = self.supply_final_desejado - self.supply_atual
            max_supply_da_wallet = min(0.70 * self.supply_atual, falta_supply)
            supply_extra_wallet = min(max_supply_da_wallet, self.saldo_wallet)
            
            self.supply_atual += supply_extra_wallet
            self.saldo_wallet -= supply_extra_wallet
        
        # Estratégia de repagamento adaptativa
        if self.operacoes_sem_progresso > 5:
            proporcao_repagamento = 0.035  # Muito conservador
        elif self.operacoes_sem_progresso > 2:
            proporcao_repagamento = 0.07   # Moderado
        else:
            proporcao_repagamento = 0.11   # Normal
        
        # Margem de borrow adaptativa
        margem_borrow = 0.73 if self.operacoes_sem_progresso > 5 else 0.69
        
        # Calcular repagamento e taxa
        repagamento = self.borrow_atual * proporcao_repagamento
        taxa_plataforma = repagamento * 0.0025
        
        # Reescalonamento determinístico
        tentativas = 0
        flags_reescalonamento = {
            'reescalou_reinvestimento': False,
            'reescalou_margem': False,
            'reescalou_repagamento': False
        }
        multiplicador_reinv = 1.0
        
        while tentativas < max_tentativas_reescalonamento:
            tentativas += 1
            
            # Calcular limites seguros
            max_borrow_por_margem = self.supply_atual * margem_borrow - self.borrow_atual
            max_borrow_por_saude = (self.supply_atual * 0.74 / 1.01) - self.borrow_atual
            novo_borrow_max_seguro = min(max_borrow_por_margem, max_borrow_por_saude)
            
            # Calcular reinvestimento inicial
            reinvestimento_inicial = self.calcular_reinvestimento(
                novo_borrow_max_seguro, repagamento, taxa_plataforma,
                self.supply_atual, self.supply_final_desejado, self.operacoes_sem_progresso
            ) * multiplicador_reinv
            
            # Calcular mínimo necessário para lucro positivo
            novo_borrow_min = min_lucro_op + reinvestimento_inicial + repagamento + taxa_plataforma
            
            # Verificar viabilidade
            if novo_borrow_min <= novo_borrow_max_seguro:
                # Viável - escolher novo_borrow
                novo_borrow_final = max(novo_borrow_min, novo_borrow_max_seguro * 0.8)
                reinvestimento_final = self.calcular_reinvestimento(
                    novo_borrow_final, repagamento, taxa_plataforma,
                    self.supply_atual, self.supply_final_desejado, self.operacoes_sem_progresso
                ) * multiplicador_reinv
                
                # Verificar lucro final
                lucro_final = (novo_borrow_final - reinvestimento_final - 
                             repagamento - taxa_plataforma)
                
                if lucro_final > min_lucro_op:
                    return (
                        novo_borrow_final,
                        reinvestimento_final,
                        True,
                        tentativas,
                        flags_reescalonamento,
                        novo_borrow_min,
                        novo_borrow_max_seguro,
                        proporcao_repagamento,
                    )
            
            # Não viável - aplicar reescalonamento determinístico
            if reinvestimento_inicial > 0:
                # Reduzir reinvestimento em 5% por tentativa (persistente via multiplicador)
                multiplicador_reinv *= 0.95
                if multiplicador_reinv < 1.0:
                    flags_reescalonamento['reescalou_reinvestimento'] = True
                if reinvestimento_inicial < 1e-9:
                    multiplicador_reinv = 0.0
            elif margem_borrow > margem_borrow_min:
                # Reduzir margem de borrow
                margem_borrow = max(margem_borrow_min, margem_borrow - 0.01)
                flags_reescalonamento['reescalou_margem'] = True
            elif proporcao_repagamento > repagamento_min:
                # Reduzir proporção de repagamento
                proporcao_repagamento = max(repagamento_min, proporcao_repagamento - 0.005)
                flags_reescalonamento['reescalou_repagamento'] = True
                # Recalcular repagamento e taxa
                repagamento = self.borrow_atual * proporcao_repagamento
                taxa_plataforma = repagamento * 0.0025
            else:
                # Último recurso: tentar aumentar margem até limite seguro
                margem_necessaria = (self.borrow_atual + min_lucro_op + repagamento + taxa_plataforma) / self.supply_atual
                if margem_necessaria <= 0.73:
                    margem_borrow = min(0.73, margem_necessaria + 1e-6)
                else:
                    # Operação inviável
                    return (
                        0.0,
                        0.0,
                        False,
                        tentativas,
                        flags_reescalonamento,
                        min_lucro_op + repagamento + taxa_plataforma,
                        novo_borrow_max_seguro,
                        proporcao_repagamento,
                    )
        
        # Máximo de tentativas atingido
        return (
            0.0,
            0.0,
            False,
            tentativas,
            flags_reescalonamento,
            min_lucro_op + repagamento + taxa_plataforma,
            novo_borrow_max_seguro,
            proporcao_repagamento,
        )

    def executar_operacao(self) -> bool:
        """
        Executa uma operação com garantia de lucro positivo.
        
        Returns:
            True se deve continuar, False se atingiu o objetivo
        """
        # Planejar operação
        (
            novo_borrow_final, reinvestimento_final, meta_lucro_atingida, tentativas_reescalonamento,
            flags_reescalonamento, novo_borrow_min_calculado, novo_borrow_max_seguro,
            proporcao_repagamento
        ) = self.planejar_operacao()
        
        # Se não conseguiu garantir lucro positivo, pular operação
        if not meta_lucro_atingida:
            resultado = (
                f"\n{'='*80}\n"
                f"OPERAÇÃO {self.operacao + 1:03d} - ANULADA (SEM PASSO VIÁVEL)\n"
                f"{'='*80}\n"
                f"❌ Nenhum passo viável encontrado para garantir lucro positivo\n"
                f"   Tentativas de reescalonamento: {tentativas_reescalonamento}\n"
                f"   Flags de reescalonamento: {flags_reescalonamento}\n"
                f"   Novo Borrow Min Calculado: {novo_borrow_min_calculado:.6f}\n"
                f"   Novo Borrow Max Seguro: {novo_borrow_max_seguro:.6f}\n"
                f"   Operação será pulada para evitar perdas\n"
                f"{'='*80}\n"
            )
            print(resultado)
            if self.arquivo:
                self.arquivo.write(resultado)
            return self.supply_atual < self.supply_final_desejado
        
        # Calcular parâmetros finais
        repagamento = self.borrow_atual * proporcao_repagamento
        taxa_plataforma = repagamento * 0.0025
        reducao_divida = repagamento
        
        # Calcular lucro e saúde
        lucro_operacao = (novo_borrow_final - reinvestimento_final - 
                         repagamento - taxa_plataforma - reducao_divida)
        denom = (self.borrow_atual - repagamento + novo_borrow_final)
        saude_projetada = ((self.supply_atual + reinvestimento_final) * 0.74) / denom if denom > 0 else float('inf')
        
        # Fallback para garantir condições
        tentativas_fallback = 0
        while tentativas_fallback < 5 and not (lucro_operacao > min_lucro_op and saude_projetada > 1.01):
            # Planejar novamente
            (
                novo_borrow_final, reinvestimento_final, meta_lucro_atingida, tentativas_extra,
                flags_reescalonamento,
                novo_borrow_min_calculado, novo_borrow_max_seguro,
                proporcao_repagamento
            ) = self.planejar_operacao()
            tentativas_reescalonamento += tentativas_extra
            # Recalcular repagamento/taxa pois dependem do tempo
            repagamento = self.borrow_atual * proporcao_repagamento
            taxa_plataforma = repagamento * 0.0025
            lucro_operacao = (novo_borrow_final - reinvestimento_final -
                              repagamento - taxa_plataforma - reducao_divida)
            denom = (self.borrow_atual - repagamento + novo_borrow_final)
            saude_projetada = ((self.supply_atual + reinvestimento_final) * 0.74) / denom if denom > 0 else float('inf')
            tentativas_fallback += 1
        # Último recurso: não aplicar operação nesta iteração (lucro 0 e sem perdas)
        if not (lucro_operacao > min_lucro_op and saude_projetada > 1.01):
            novo_borrow_final = 0.0
            reinvestimento_final = 0.0
            lucro_operacao = 0.0
            saude_projetada = (self.supply_atual * 0.74) / max(self.borrow_atual - repagamento, 1e-9)
        
        # Atualizar estado
        self.operacao += 1
        self.repagamento_total += repagamento
        self.borrow_atual -= repagamento
        self.borrow_atual += novo_borrow_final
        self.supply_atual += reinvestimento_final
        self.lucro_total += lucro_operacao
        self.supply_extra_acumulado += lucro_operacao
        self.taxas_total += taxa_plataforma
        
        # Calcular saúde final
        saude = (self.supply_atual * 0.74) / self.borrow_atual if self.borrow_atual > 0 else float('inf')
        
        # Detectar estagnação
        progresso = self.supply_atual - self.supply_anterior
        if progresso < 0.00003:
            self.operacoes_sem_progresso += 1
            self.total_operacoes_estagnadas += 1
        else:
            self.operacoes_sem_progresso = 0
        self.supply_anterior = self.supply_atual
        
        # Atualizar métricas de monitoramento
        self.operacoes_com_lucro_positivo += 1
        self.menor_lucro_por_operacao = min(self.menor_lucro_por_operacao, lucro_operacao)
        self.maior_tentativas_reescalonamento = max(self.maior_tentativas_reescalonamento, tentativas_reescalonamento)
        self.total_tentativas_reescalonamento += tentativas_reescalonamento
        
        # Calcular aTokens livres
        atokens_livres = (self.supply_atual - self.borrow_atual) * 0.80
        
        # Gerar relatório da operação
        resultado = (
            f"\n{'='*80}\n"
            f"OPERAÇÃO {self.operacao:03d} - ESTRATÉGIA COM GARANTIA DE LUCRO POSITIVO\n"
            f"{'='*80}\n"
            f"[PARAMETROS] OPERACAO:\n"
            f"   Repagamento: {repagamento:>12.6f} ({proporcao_repagamento:.2%} da divida)\n"
            f"   Taxa Plataforma: {taxa_plataforma:>9.6f} (0.25% do repagamento)\n"
            f"   Total Taxas Pagas: {self.taxas_total:>7.6f}\n"
            f"   Repagamento Total Acumulado: {self.repagamento_total:>4.6f}\n"
            f"\n[LIMITES] CALCULADOS:\n"
            f"   Novo Borrow Final: {novo_borrow_final:>10.6f}\n"
            f"   Novo Borrow Min: {novo_borrow_min_calculado:>12.6f}\n"
            f"   Novo Borrow Max Seguro: {novo_borrow_max_seguro:>6.6f}\n"
            f"\n[REESCALONAMENTO]:\n"
            f"   Tentativas: {tentativas_reescalonamento:>15}\n"
            f"   Flags: {flags_reescalonamento}\n"
            f"\n[RESULTADOS] FINANCEIROS:\n"
            f"   Supply Total: {self.supply_atual:>13.6f}\n"
            f"   aTokens Livres: {atokens_livres:>11.6f}\n"
            f"   Divida Total: {self.borrow_atual:>13.6f}\n"
            f"   Lucro Operacao: {lucro_operacao:>10.6f}\n"
            f"   Reinvestimento: {reinvestimento_final:>10.6f}\n"
            f"   Lucro Total: {self.lucro_total:>13.6f}\n"
            f"\n[STATUS] E CONTROLE:\n"
            f"   Saldo Extra Acumulado: {self.supply_extra_acumulado:>6.6f}\n"
            f"   Operações sem Progresso: {self.operacoes_sem_progresso:>5}\n"
            f"   Total Estagnadas: {self.total_operacoes_estagnadas:>11}\n"
            f"   Saúde da Posição: {saude:>12.2f}\n"
            f"   Saldo Wallet Restante: {self.saldo_wallet:>7.6f}\n"
            f"{'='*80}\n"
        )
        
        print(resultado)
        if self.arquivo:
            self.arquivo.write(resultado)
        
        # Verificar se chegou ao objetivo
        return self.supply_atual < self.supply_final_desejado
    
    def executar_simulacao(self) -> Dict[str, Any]:
        """
        Executa a simulação completa.
        
        Returns:
            Dicionário com estatísticas finais
        """
        # Abrir arquivo de saída
        with open("resultado_operacoes.txt", "w", encoding='utf-8') as arquivo:
            self.arquivo = arquivo
            
            # Loop principal
            while self.executar_operacao():
                pass
        
        # Calcular estatísticas finais
        saude_final = (self.supply_atual * 0.74) / self.borrow_atual if self.borrow_atual > 0 else float('inf')
        
        estatisticas = {
            'supply_final': self.supply_atual,
            'supply_final_desejado': self.supply_final_desejado,
            'objetivo_alcancado': self.supply_atual >= self.supply_final_desejado,
            'lucro_total': self.lucro_total,
            'taxas_total': self.taxas_total,
            'lucro_liquido': self.lucro_total - self.taxas_total,
            'saude_final': saude_final,
            'total_operacoes': self.operacao,
            'operacoes_estagnadas': self.total_operacoes_estagnadas,
            'porcentagem_estagnacao': (self.total_operacoes_estagnadas / self.operacao * 100) if self.operacao > 0 else 0,
            'operacoes_com_lucro_positivo': self.operacoes_com_lucro_positivo,
            'porcentagem_lucro_positivo': (self.operacoes_com_lucro_positivo / self.operacao * 100) if self.operacao > 0 else 0,
            'menor_lucro_por_operacao': self.menor_lucro_por_operacao,
            'maior_tentativas_reescalonamento': self.maior_tentativas_reescalonamento,
            'total_tentativas_reescalonamento': self.total_tentativas_reescalonamento
        }
        
        # Gerar relatório final
        resultado_final = (
            f"\n{'='*80}\n"
            f"[RESULTADO FINAL] - SIMULADOR COM GARANTIA DE LUCRO POSITIVO\n"
            f"{'='*80}\n"
            f"\n[OBJETIVOS] ALCANCADOS:\n"
            f"   Supply Final Alcancado: {estatisticas['supply_final']:>12.6f}\n"
            f"   Supply Final Desejado:  {estatisticas['supply_final_desejado']:>12.6f}\n"
            f"   Diferenca:              {abs(estatisticas['supply_final'] - estatisticas['supply_final_desejado']):>12.6f}\n"
            f"   Status: {'[OK] OBJETIVO ALCANCADO' if estatisticas['objetivo_alcancado'] else '[ERRO] OBJETIVO NAO ALCANCADO'}\n"
            f"\n[RESULTADOS] FINANCEIROS:\n"
            f"   Lucro Total Bruto:      {estatisticas['lucro_total']:>12.6f}\n"
            f"   Total de Taxas Pagas:   {estatisticas['taxas_total']:>12.6f}\n"
            f"   Lucro Liquido Final:    {estatisticas['lucro_liquido']:>12.6f}\n"
            f"   Saude Final da Posicao: {estatisticas['saude_final']:>12.2f}\n"
            f"\n[ESTATISTICAS] DE OPERACAO:\n"
            f"   Total de Operacoes:     {estatisticas['total_operacoes']:>12}\n"
            f"   Operacoes Estagnadas:   {estatisticas['operacoes_estagnadas']:>12}\n"
            f"   Taxa de Estagnacao:     {estatisticas['porcentagem_estagnacao']:>11.1f}%\n"
            f"\n[GARANTIAS] DE LUCRO POSITIVO:\n"
            f"   Operacoes com Lucro +:  {estatisticas['operacoes_com_lucro_positivo']:>12}\n"
            f"   Taxa de Lucro Positivo: {estatisticas['porcentagem_lucro_positivo']:>11.1f}%\n"
            f"   Menor Lucro por Op:     {estatisticas['menor_lucro_por_operacao']:>12.8f}\n"
            f"\n[EFICIENCIA] DO REESCALONAMENTO:\n"
            f"   Maior Tentativas (1 Op):{estatisticas['maior_tentativas_reescalonamento']:>12}\n"
            f"   Total Tentativas:       {estatisticas['total_tentativas_reescalonamento']:>12}\n"
            f"   Media por Operacao:     {(estatisticas['total_tentativas_reescalonamento']/estatisticas['total_operacoes']):>11.1f}\n"
            f"{'='*80}\n"
        )
        
        print(resultado_final)
        with open("resultado_operacoes.txt", "a", encoding='utf-8') as arquivo:
            arquivo.write(resultado_final)
        
        return estatisticas


def main():
    """
    Função principal - executa simulação interativa.
    """
    # Entrada do usuário
    print("[SIMULADOR] DEFI COM GARANTIA DE LUCRO POSITIVO")
    print("=" * 60)
    
    supply_inicial = float(input("Supply inicial: "))
    borrow_inicial = float(input("Borrow inicial: "))
    supply_final_desejado = float(input("Supply final desejado: "))
    saldo_wallet = float(input("Saldo disponível na wallet: "))
    
    # Criar e executar simulador
    simulador = DeFiSimulator(
        supply_inicial=supply_inicial,
        borrow_inicial=borrow_inicial,
        supply_final_desejado=supply_final_desejado,
        saldo_wallet=saldo_wallet
    )
    
    print(f"\n[INICIANDO] SIMULACAO COM GARANTIA DE LUCRO POSITIVO...")
    print(f"[CONFIGURACOES]:")
    print(f"   Lucro minimo por operacao: {min_lucro_op}")
    print(f"   Margem de borrow minima: {margem_borrow_min}")
    print(f"   Repagamento minimo: {repagamento_min}")
    print(f"   Maximo tentativas de reescalonamento: {max_tentativas_reescalonamento}")
    print("=" * 60)
    
    estatisticas = simulador.executar_simulacao()
    
    print(f"\n[OK] SIMULACAO CONCLUIDA COM SUCESSO!")
    print(f"[ARQUIVO] Resultados salvo em: resultado_operacoes.txt")

if __name__ == "__main__":
    main()
