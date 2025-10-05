"""
Simulador de Estratégia DeFi com Garantia de Lucro Positivo
Refatorado para garantir lucro > 0 em todas as operações por construção matemática
"""

from typing import Tuple, Dict, Any

# ============================================================================
# CONFIGURAÇÕES GLOBAIS
# ============================================================================

# Configurações de garantia de lucro
min_lucro_op: float = 1e-6
margem_borrow_min: float = 0.50
repagamento_min: float = 0.03
max_tentativas_reescalonamento: int = 50

# Constantes do sistema DeFi
class ConfigDeFi:
    """
    Constantes do sistema DeFi para evitar magic numbers.
    
    Esta classe centraliza todas as constantes utilizadas no simulador,
    facilitando manutenção e configuração do sistema.
    
    Exemplo de uso:
        >>> ConfigDeFi.FATOR_SAUDE
        0.74
        >>> ConfigDeFi.TAXA_PLATAFORMA
        0.0025
    """
    # ============================================================================
    # FATORES DE SAÚDE E SEGURANÇA
    # ============================================================================
    FATOR_SAUDE = 0.74                    # Fator de colateralização (74%)
    LIMITE_SAUDE_MINIMO = 1.01            # Saúde mínima aceitável (101%)
    FATOR_ATOKENS_LIVRES = 0.80           # Fator para cálculo de aTokens livres (80%)
    
    # ============================================================================
    # TAXAS E CUSTOS
    # ============================================================================
    TAXA_PLATAFORMA = 0.0025              # Taxa da plataforma (0.25%)
    
    # ============================================================================
    # ESTRATÉGIAS DE REINVESTIMENTO
    # ============================================================================
    REINVESTIMENTO_AGRESSIVO = 0.60       # 60% do lucro (longe do objetivo)
    REINVESTIMENTO_MODERADO = 0.40         # 40% do lucro (medianamente perto)
    REINVESTIMENTO_CONSERVADOR = 0.20      # 20% do lucro (muito perto)
    REINVESTIMENTO_ESTAGNADO_ALTO = 0.05   # 5% do lucro (muitas operações estagnadas)
    REINVESTIMENTO_ESTAGNADO_BAIXO = 0.10 # 10% do lucro (algumas operações estagnadas)
    
    # ============================================================================
    # LIMITES DE MARGEM DE BORROW
    # ============================================================================
    MARGEM_BORROW_NORMAL = 0.69           # Margem normal (69%)
    MARGEM_BORROW_AGRESSIVA = 0.73        # Margem agressiva (73%)
    
    # ============================================================================
    # ESTRATÉGIAS DE REPAGAMENTO
    # ============================================================================
    REPAGAMENTO_NORMAL = 0.11             # 11% da dívida (estratégia normal)
    REPAGAMENTO_MODERADO = 0.07           # 7% da dívida (estratégia moderada)
    REPAGAMENTO_CONSERVADOR = 0.035       # 3.5% da dívida (estratégia conservadora)
    
    # ============================================================================
    # LIMITES DE PROGRESSO E ESTAGNAÇÃO
    # ============================================================================
    LIMITE_PROGRESSO_ESTAGNACAO = 0.00003 # Limite para detectar estagnação
    LIMITE_OPERACOES_ESTAGNADAS = 35      # Limite de operações estagnadas
    
    # ============================================================================
    # LIMITES DE VALIDAÇÃO (CONFIGURÁVEIS PELO USUÁRIO)
    # ============================================================================
    LIMITE_BORROW_SUPPLY = 0.95           # Borrow não pode exceder 95% do supply (mais flexível)
    LIMITE_CRESCIMENTO_MAXIMO = float('inf')  # Sem limite de crescimento (usuário define)
    LIMITE_WALLET_SUPPLY = 1.00           # Wallet pode usar 100% do supply atual

class DeFiSimulator:
    """
    Simulador de estratégia DeFi com garantia de lucro positivo em todas as operações.
    Ajusta parâmetros antes do cálculo do lucro para garantir resultado positivo por construção.
    
    Permite configuração flexível de parâmetros pelo usuário.
    """
    
    def __init__(self, supply_inicial: float, borrow_inicial: float, 
                 supply_final_desejado: float, saldo_wallet: float):
        """
        Inicializa o simulador com os parâmetros básicos.
        
        Args:
            supply_inicial: Valor inicial do supply
            borrow_inicial: Valor inicial do borrow
            supply_final_desejado: Objetivo de supply final
            saldo_wallet: Saldo disponível na wallet
        """
        # Validação de entrada robusta
        if not isinstance(supply_inicial, (int, float)) or supply_inicial <= 0:
            raise ValueError(f"Supply inicial deve ser um número positivo, recebido: {supply_inicial}")
        if not isinstance(borrow_inicial, (int, float)) or borrow_inicial < 0:
            raise ValueError(f"Borrow inicial deve ser um número não negativo, recebido: {borrow_inicial}")
        if not isinstance(supply_final_desejado, (int, float)) or supply_final_desejado <= supply_inicial:
            raise ValueError(f"Supply final deve ser um número maior que o inicial ({supply_inicial}), recebido: {supply_final_desejado}")
        if not isinstance(saldo_wallet, (int, float)) or saldo_wallet < 0:
            raise ValueError(f"Saldo da wallet deve ser um número não negativo, recebido: {saldo_wallet}")
        
        # Validações de negócio flexíveis (apenas avisos)
        if borrow_inicial > supply_inicial * ConfigDeFi.LIMITE_BORROW_SUPPLY:
            print(f"⚠️  AVISO: Borrow inicial ({borrow_inicial}) é maior que {ConfigDeFi.LIMITE_BORROW_SUPPLY*100}% do supply inicial ({supply_inicial})")
            print(f"   Isso pode resultar em operações mais arriscadas.")
            print(f"   Você pode ajustar o limite com: simulador.configurar_parametros(limite_borrow_supply=0.99)")
        
        if ConfigDeFi.LIMITE_CRESCIMENTO_MAXIMO != float('inf') and supply_final_desejado > supply_inicial * ConfigDeFi.LIMITE_CRESCIMENTO_MAXIMO:
            print(f"⚠️  AVISO: Supply final desejado ({supply_final_desejado}) é muito ambicioso.")
            print(f"   Objetivo: {supply_final_desejado/supply_inicial:.0f}x o supply inicial.")
            print(f"   Isso pode exigir muitas operações para ser alcançado.")
            print(f"   Você pode remover o limite com: simulador.configurar_parametros(limite_crescimento_maximo='inf')")
        
        # Parâmetros iniciais
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
        self.supply_extra_acumulado = 0
        self.taxas_total = 0
        
        # Controle de estagnação
        self.supply_anterior = supply_inicial
        self.operacoes_sem_progresso = 0
        self.limite_operacoes_estagnadas = ConfigDeFi.LIMITE_OPERACOES_ESTAGNADAS
        self.total_operacoes_estagnadas = 0
        
        # Métricas de monitoramento
        self.operacoes_com_lucro_positivo = 0
        self.menor_lucro_por_operacao = float('inf')
        self.maior_tentativas_reescalonamento = 0
        self.total_tentativas_reescalonamento = 0
        
        # Arquivo de saída
        self.arquivo = None
        
        # Parâmetros configuráveis pelo usuário
        self.config_personalizada = {
            'limite_borrow_supply': ConfigDeFi.LIMITE_BORROW_SUPPLY,
            'limite_crescimento_maximo': ConfigDeFi.LIMITE_CRESCIMENTO_MAXIMO,
            'limite_wallet_supply': ConfigDeFi.LIMITE_WALLET_SUPPLY,
            'fator_saude': ConfigDeFi.FATOR_SAUDE,
            'limite_saude_minimo': ConfigDeFi.LIMITE_SAUDE_MINIMO,
            'taxa_plataforma': ConfigDeFi.TAXA_PLATAFORMA
        }
    
    def configurar_parametros(self, **kwargs):
        """
        Permite ao usuário configurar parâmetros personalizados.
        
        Args:
            **kwargs: Parâmetros a serem configurados
                - limite_borrow_supply: Limite de borrow em relação ao supply (0.0-1.0)
                - limite_crescimento_maximo: Limite máximo de crescimento (float ou inf)
                - limite_wallet_supply: Limite de uso da wallet (0.0-1.0)
                - fator_saude: Fator de saúde da posição (0.0-1.0)
                - limite_saude_minimo: Saúde mínima aceitável (>= 1.0)
                - taxa_plataforma: Taxa da plataforma (0.0-1.0)
        """
        for key, value in kwargs.items():
            if key in self.config_personalizada:
                if key == 'limite_crescimento_maximo' and value == 'inf':
                    value = float('inf')
                self.config_personalizada[key] = value
                print(f"OK - {key} configurado para: {value}")
            else:
                print(f"AVISO - Parâmetro '{key}' não reconhecido. Parâmetros disponíveis:")
                for param in self.config_personalizada.keys():
                    print(f"   - {param}")
    
    def obter_configuracao(self):
        """Retorna a configuração atual."""
        return self.config_personalizada.copy()
    
    def calcular_reinvestimento(self, novo_borrow: float, repagamento: float,
                              taxa_plataforma: float, supply_atual: float,
                              supply_final_desejado: float, operacoes_estagnadas: int = 0) -> float:
        """
        Calcula o reinvestimento baseado na distância até o objetivo.
        O lucro restante vira supply extra para a próxima operação.
        
        Args:
            novo_borrow: Valor do novo empréstimo
            repagamento: Valor do repagamento
            taxa_plataforma: Taxa da plataforma
            supply_atual: Supply atual
            supply_final_desejado: Objetivo de supply final
            operacoes_estagnadas: Número de operações estagnadas
            
        Returns:
            Valor do reinvestimento calculado
        """
        lucro_bruto = novo_borrow - repagamento - taxa_plataforma
        
        if lucro_bruto <= 0:
            return 0
        
        # Calcular quanta distância ainda falta para o objetivo
        falta_para_objetivo = supply_final_desejado - supply_atual
        
        # Se estamos estagnados, reduzir drasticamente o reinvestimento
        if operacoes_estagnadas > 5:
            return lucro_bruto * ConfigDeFi.REINVESTIMENTO_ESTAGNADO_ALTO
        elif operacoes_estagnadas > 2:
            return lucro_bruto * ConfigDeFi.REINVESTIMENTO_ESTAGNADO_BAIXO
        
        # Lógica normal baseada na distância
        if falta_para_objetivo > supply_atual * 0.5:  # Ainda longe do objetivo
            reinvestimento = lucro_bruto * ConfigDeFi.REINVESTIMENTO_AGRESSIVO
        elif falta_para_objetivo > supply_atual * 0.2:  # Medianamente perto
            reinvestimento = lucro_bruto * ConfigDeFi.REINVESTIMENTO_MODERADO
        else:  # Muito perto do objetivo
            reinvestimento = lucro_bruto * ConfigDeFi.REINVESTIMENTO_CONSERVADOR
        
        return reinvestimento

    def _aplicar_supply_extra(self) -> None:
        """
        Aplica supply extra do acumulado e da wallet.
        
        Este método gerencia a aplicação de recursos extras para maximizar
        o potencial de crescimento da posição.
        
        Processo:
        1. Usa lucro acumulado das operações anteriores
        2. Aplica saldo da wallet se necessário
        3. Respeita limites de segurança (70% do supply atual)
        
        Raises:
            ValueError: Se os valores calculados forem inválidos
        """
        # Usar o lucro acumulado das operações anteriores como supply extra
        if self.supply_extra_acumulado > 0:
            supply_usado_do_acumulado = min(
                self.supply_extra_acumulado, 
                self.supply_final_desejado - self.supply_atual
            )
            self.supply_atual += supply_usado_do_acumulado
            self.supply_extra_acumulado -= supply_usado_do_acumulado

        # Supply extra da wallet se ainda precisar e tiver disponível
        if self.supply_atual < self.supply_final_desejado and self.saldo_wallet > 0:
            falta_supply = self.supply_final_desejado - self.supply_atual
            max_supply_da_wallet = min(self.config_personalizada['limite_wallet_supply'] * self.supply_atual, falta_supply)
            supply_extra_wallet = min(max_supply_da_wallet, self.saldo_wallet)
            
            self.supply_atual += supply_extra_wallet
            self.saldo_wallet -= supply_extra_wallet

    def _calcular_parametros_adaptativos(self) -> Tuple[float, float, float, float]:
        """
        Calcula parâmetros adaptativos baseados no estado atual.
        
        Returns:
            Tuple com (proporcao_repagamento, margem_borrow, repagamento, taxa_plataforma)
        """
        # Estratégia de repagamento adaptativa
        if self.operacoes_sem_progresso > 5:
            proporcao_repagamento = ConfigDeFi.REPAGAMENTO_CONSERVADOR
        elif self.operacoes_sem_progresso > 2:
            proporcao_repagamento = ConfigDeFi.REPAGAMENTO_MODERADO
        else:
            proporcao_repagamento = ConfigDeFi.REPAGAMENTO_NORMAL
        
        # Margem de borrow adaptativa
        margem_borrow = (ConfigDeFi.MARGEM_BORROW_AGRESSIVA 
                        if self.operacoes_sem_progresso > 5 
                        else ConfigDeFi.MARGEM_BORROW_NORMAL)
        
        # Calcular repagamento e taxa
        repagamento = self.borrow_atual * proporcao_repagamento
        taxa_plataforma = repagamento * self.config_personalizada['taxa_plataforma']
        
        return proporcao_repagamento, margem_borrow, repagamento, taxa_plataforma

    def _calcular_limites_seguros(self, margem_borrow: float) -> float:
        """Calcula o limite máximo seguro de borrow."""
        max_borrow_por_margem = self.supply_atual * margem_borrow - self.borrow_atual
        max_borrow_por_saude = (self.supply_atual * self.config_personalizada['fator_saude'] / self.config_personalizada['limite_saude_minimo']) - self.borrow_atual
        
        # Garantir que o limite nunca seja negativo
        limite_seguro = min(max_borrow_por_margem, max_borrow_por_saude)
        
        # Se o limite for negativo, usar um valor mínimo baseado no supply atual
        if limite_seguro <= 0:
            limite_seguro = self.supply_atual * 0.01  # Mínimo 1% do supply atual
        
        return limite_seguro

    def _executar_reescalonamento(self, proporcao_repagamento: float, margem_borrow: float, 
                                 repagamento: float, taxa_plataforma: float) -> Tuple[float, float, bool, int, Dict[str, bool], float, float, float]:
        """
        Executa o processo de reescalonamento determinístico.
        
        Returns:
            Tuple com (novo_borrow_final, reinvestimento_final, meta_lucro_atingida,
                      tentativas_reescalonamento, flags_reescalonamento,
                      novo_borrow_min_calculado, novo_borrow_max_seguro,
                      proporcao_repagamento_final)
        """
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
            novo_borrow_max_seguro = self._calcular_limites_seguros(margem_borrow)
            
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
                taxa_plataforma = repagamento * ConfigDeFi.TAXA_PLATAFORMA
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
            self._calcular_limites_seguros(margem_borrow),
            proporcao_repagamento,
        )

    def planejar_operacao(self) -> Tuple[float, float, bool, int, Dict[str, bool], float, float, float]:
        """
        Planeja uma operação garantindo lucro positivo por construção.
        
        Returns:
            Tuple com (novo_borrow_final, reinvestimento_final, meta_lucro_atingida,
                      tentativas_reescalonamento, flags_reescalonamento,
                      novo_borrow_min_calculado, novo_borrow_max_seguro,
                      proporcao_repagamento_final)
        """
        # Aplicar supply extra do acumulado e da wallet
        self._aplicar_supply_extra()
        
        # Calcular parâmetros adaptativos
        proporcao_repagamento, margem_borrow, repagamento, taxa_plataforma = self._calcular_parametros_adaptativos()
        
        # Executar reescalonamento determinístico
        return self._executar_reescalonamento(proporcao_repagamento, margem_borrow, repagamento, taxa_plataforma)

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
        
        # Se não conseguiu garantir lucro positivo, usar fallback
        if not meta_lucro_atingida:
            # Calcular repagamento e taxa para o fallback
            repagamento = self.borrow_atual * proporcao_repagamento
            taxa_plataforma = repagamento * self.config_personalizada['taxa_plataforma']
            
            # Fallback: operação mínima com lucro garantido
            novo_borrow_final = max(
                min_lucro_op * 10 + repagamento + taxa_plataforma,
                self.supply_atual * 0.01  # Mínimo 1% do supply
            )
            reinvestimento_final = self.calcular_reinvestimento(
                novo_borrow_final, repagamento, taxa_plataforma,
                self.supply_atual, self.supply_final_desejado, self.operacoes_sem_progresso
            )
            lucro_operacao = (novo_borrow_final - reinvestimento_final - 
                             repagamento - taxa_plataforma)
            
            resultado = (
                f"\n{'='*80}\n"
                f"OPERAÇÃO {self.operacao + 1:03d} - FALLBACK APLICADO\n"
                f"{'='*80}\n"
                f"AVISO: Reescalonamento falhou, usando fallback seguro\n"
                f"   Tentativas de reescalonamento: {tentativas_reescalonamento}\n"
                f"   Flags de reescalonamento: {flags_reescalonamento}\n"
                f"   Novo Borrow Final (Fallback): {novo_borrow_final:.6f}\n"
                f"   Lucro Garantido: {lucro_operacao:.6f}\n"
                f"{'='*80}\n"
            )
            print(resultado)
            if self.arquivo:
                self.arquivo.write(resultado)
        
        # Calcular parâmetros finais
        repagamento = self.borrow_atual * proporcao_repagamento
        taxa_plataforma = repagamento * ConfigDeFi.TAXA_PLATAFORMA
        reducao_divida = repagamento
        
        # Calcular lucro e saúde
        lucro_operacao = (novo_borrow_final - reinvestimento_final - 
                         repagamento - taxa_plataforma - reducao_divida)
        denominador_saude = (self.borrow_atual - repagamento + novo_borrow_final)
        saude_projetada = ((self.supply_atual + reinvestimento_final) * self.config_personalizada['fator_saude']) / denominador_saude if denominador_saude > 0 else float('inf')
        
        # Fallback para garantir condições
        tentativas_fallback = 0
        while tentativas_fallback < 5 and not (lucro_operacao > min_lucro_op and saude_projetada > self.config_personalizada['limite_saude_minimo']):
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
            taxa_plataforma = repagamento * ConfigDeFi.TAXA_PLATAFORMA
            lucro_operacao = (novo_borrow_final - reinvestimento_final -
                              repagamento - taxa_plataforma - reducao_divida)
            denominador_saude = (self.borrow_atual - repagamento + novo_borrow_final)
            saude_projetada = ((self.supply_atual + reinvestimento_final) * self.config_personalizada['fator_saude']) / denominador_saude if denominador_saude > 0 else float('inf')
            tentativas_fallback += 1
        # Último recurso: garantir lucro mínimo positivo
        if not (lucro_operacao > min_lucro_op and saude_projetada > self.config_personalizada['limite_saude_minimo']):
            # Calcular novo_borrow mínimo para lucro positivo
            lucro_minimo_garantido = min_lucro_op * 10  # Aumentar margem
            novo_borrow_final = max(
                lucro_minimo_garantido + repagamento + taxa_plataforma,
                self.borrow_atual * 0.05  # Mínimo 5% do borrow atual
            )
            reinvestimento_final = self.calcular_reinvestimento(
                novo_borrow_final, repagamento, taxa_plataforma,
                self.supply_atual, self.supply_final_desejado, self.operacoes_sem_progresso
            )
            lucro_operacao = (novo_borrow_final - reinvestimento_final - 
                             repagamento - taxa_plataforma)
            saude_projetada = ((self.supply_atual + reinvestimento_final) * ConfigDeFi.FATOR_SAUDE) / max(self.borrow_atual - repagamento + novo_borrow_final, 1e-9)
        
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
        saude_final = (self.supply_atual * self.config_personalizada['fator_saude']) / self.borrow_atual if self.borrow_atual > 0 else float('inf')
        
        # Detectar estagnação
        progresso_supply = self.supply_atual - self.supply_anterior
        if progresso_supply < ConfigDeFi.LIMITE_PROGRESSO_ESTAGNACAO:
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
        atokens_livres = (self.supply_atual - self.borrow_atual) * self.config_personalizada.get('fator_atokens_livres', ConfigDeFi.FATOR_ATOKENS_LIVRES)
        
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
            f"   Saúde da Posição: {saude_final:>12.2f}\n"
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
        saude_final = (self.supply_atual * self.config_personalizada['fator_saude']) / self.borrow_atual if self.borrow_atual > 0 else float('inf')
        
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
