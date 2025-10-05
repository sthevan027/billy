# Documentação Técnica - Simulador DeFi

## 📚 Índice
1. [Arquitetura do Sistema](#arquitetura-do-sistema)
2. [Algoritmos Implementados](#algoritmos-implementados)
3. [Estrutura de Classes](#estrutura-de-classes)
4. [Fluxo de Execução](#fluxo-de-execução)
5. [Configurações e Parâmetros](#configurações-e-parâmetros)
6. [Algoritmo de Reescalonamento](#algoritmo-de-reescalonamento)
7. [Validações e Garantias](#validações-e-garantias)
8. [Testes e Validação](#testes-e-validação)
9. [Análise de Performance](#análise-de-performance)
10. [Troubleshooting](#troubleshooting)

## 🏗️ Arquitetura do Sistema

### Visão Geral
O simulador implementa uma arquitetura orientada a objetos com separação clara de responsabilidades:

```
DeFiSimulator
├── __init__()           # Inicialização e configuração
├── calcular_reinvestimento()  # Lógica de reinvestimento
├── planejar_operacao()        # Planejamento com garantia de lucro
├── executar_operacao()        # Execução e validação
└── executar_simulacao()       # Orquestração principal
```

### Princípios de Design
- **Encapsulamento**: Estado interno protegido
- **Responsabilidade única**: Cada método tem uma função específica
- **Imutabilidade**: Configurações não alteram durante execução
- **Determinismo**: Resultados reproduzíveis e previsíveis

## 🔧 Algoritmos Implementados

### 1. Algoritmo de Reinvestimento

```python
def calcular_reinvestimento(self, novo_borrow, repagamento, taxa_plataforma, 
                          supply_atual, supply_final_desejado, operacoes_estagnadas):
    lucro_bruto = novo_borrow - repagamento - taxa_plataforma
    
    if lucro_bruto <= 0:
        return 0
    
    falta_para_objetivo = supply_final_desejado - supply_atual
    
    # Estratégia baseada em estagnação
    if operacoes_estagnadas > 5:
        return lucro_bruto * 0.05    # 5% para maximizar lucro
    elif operacoes_estagnadas > 2:
        return lucro_bruto * 0.10    # 10% moderado
    
    # Estratégia baseada na distância
    if falta_para_objetivo > supply_atual * 0.5:
        return lucro_bruto * 0.60    # 60% agressivo
    elif falta_para_objetivo > supply_atual * 0.2:
        return lucro_bruto * 0.40    # 40% moderado
    else:
        return lucro_bruto * 0.20    # 20% conservador
```

**Características:**
- **Adaptativo**: Ajusta baseado na distância do objetivo
- **Anti-estagnação**: Reduz reinvestimento quando estagnado
- **Conservador**: Prioriza lucro líquido próximo ao objetivo

### 2. Algoritmo de Garantia de Lucro

```python
def planejar_operacao(self):
    # 1. Calcular limites seguros
    max_borrow_por_margem = supply_atual * margem_borrow - borrow_atual
    max_borrow_por_saude = (supply_atual * 0.74 / 1.01) - borrow_atual
    novo_borrow_max_seguro = min(max_borrow_por_margem, max_borrow_por_saude)
    
    # 2. Calcular mínimo necessário
    novo_borrow_min = min_lucro_op + reinvestimento + repagamento + taxa_plataforma
    
    # 3. Verificar viabilidade
    if novo_borrow_min <= novo_borrow_max_seguro:
        return novo_borrow_min, reinvestimento, True  # Viável
    else:
        return 0, 0, False  # Inviável - pular operação
```

**Garantias:**
- **Lucro mínimo**: Sempre ≥ `min_lucro_op`
- **Saúde mínima**: Sempre > 1.01
- **Margem segura**: Respeita limites de borrow

## 🏛️ Estrutura de Classes

### Classe `DeFiSimulator`

#### Atributos de Estado
```python
# Parâmetros iniciais
self.supply_inicial: float
self.borrow_inicial: float
self.supply_final_desejado: float
self.saldo_wallet: float

# Estado atual
self.supply_atual: float
self.borrow_atual: float
self.repagamento_total: float
self.lucro_total: float
self.operacao: int
self.supply_extra_acumulado: float
self.taxas_total: float

# Controle de estagnação
self.supply_anterior: float
self.operacoes_sem_progresso: int
self.total_operacoes_estagnadas: int

# Métricas de monitoramento
self.operacoes_com_lucro_positivo: int
self.menor_lucro_por_operacao: float
self.maior_tentativas_reescalonamento: int
self.total_tentativas_reescalonamento: int
```

#### Métodos Principais

##### `__init__(supply_inicial, borrow_inicial, supply_final_desejado, saldo_wallet)`
**Propósito**: Inicializa o simulador com parâmetros básicos
**Complexidade**: O(1)
**Validações**: Nenhuma (aceita valores do usuário)

##### `calcular_reinvestimento(novo_borrow, repagamento, taxa_plataforma, supply_atual, supply_final_desejado, operacoes_estagnadas)`
**Propósito**: Calcula reinvestimento baseado na estratégia adaptativa
**Complexidade**: O(1)
**Retorno**: `float` - Valor do reinvestimento
**Características**:
- Adaptativo baseado na distância do objetivo
- Anti-estagnação com redução progressiva
- Conservador próximo ao objetivo

##### `planejar_operacao()`
**Propósito**: Planeja operação garantindo lucro positivo
**Complexidade**: O(k) onde k ≤ max_tentativas_reescalonamento
**Retorno**: `Tuple[float, float, bool, int, Dict[str, bool], float, float, float]`
**Algoritmo**:
1. Aplica supply extra acumulado
2. Aplica supply da wallet (até 70% do supply atual)
3. Calcula estratégias adaptativas (repagamento e margem)
4. Loop de reescalonamento até viabilidade
5. Retorna parâmetros finais ou operação nula

##### `executar_operacao()`
**Propósito**: Executa operação com validações rigorosas
**Complexidade**: O(k) onde k ≤ 5 (tentativas de fallback)
**Retorno**: `bool` - True se continuar, False se atingiu objetivo
**Validações**:
- Lucro > min_lucro_op
- Saúde > 1.01
- Fallback automático se falhar

##### `executar_simulacao()`
**Propósito**: Orquestra a simulação completa
**Complexidade**: O(n) onde n é o número de operações
**Retorno**: `Dict[str, Any]` - Estatísticas finais
**Características**:
- Loop principal até atingir objetivo
- Geração de relatórios
- Cálculo de estatísticas finais

## 🔄 Fluxo de Execução

### 1. Inicialização
```
Usuário → Input parâmetros → DeFiSimulator.__init__() → Estado inicial
```

### 2. Loop Principal
```
while supply_atual < supply_final_desejado:
    planejar_operacao() → executar_operacao() → Atualizar estado
```

### 3. Planejamento da Operação
```
1. Aplicar supply extra acumulado
2. Aplicar supply da wallet (se necessário)
3. Calcular estratégias adaptativas
4. Loop de reescalonamento:
   a. Calcular limites seguros
   b. Calcular reinvestimento
   c. Calcular mínimo necessário
   d. Verificar viabilidade
   e. Se inviável: reescalar parâmetros
5. Retornar parâmetros finais
```

### 4. Execução da Operação
```
1. Validar meta de lucro atingida
2. Se não atingida: pular operação
3. Calcular parâmetros finais
4. Validar lucro e saúde
5. Se inválido: tentar fallback
6. Atualizar estado
7. Detectar estagnação
8. Atualizar métricas
9. Gerar relatório
10. Verificar objetivo
```

## ⚙️ Configurações e Parâmetros

### Parâmetros Globais

| Parâmetro | Valor Padrão | Descrição | Impacto |
|-----------|--------------|-----------|---------|
| `min_lucro_op` | 1e-6 | Lucro mínimo por operação | Garantia de lucro |
| `margem_borrow_min` | 0.50 | Margem mínima de borrow | Limite de segurança |
| `repagamento_min` | 0.03 | Repagamento mínimo | Limite de agressividade |
| `max_tentativas_reescalonamento` | 50 | Máximo tentativas por operação | Prevenção de loops |

### Estratégias Adaptativas

#### Repagamento
```python
if operacoes_sem_progresso > 5:
    proporcao_repagamento = 0.035    # 3.5% - Muito conservador
elif operacoes_sem_progresso > 2:
    proporcao_repagamento = 0.07     # 7.0% - Moderado
else:
    proporcao_repagamento = 0.11     # 11.0% - Normal
```

#### Margem de Borrow
```python
if operacoes_sem_progresso > 5:
    margem_borrow = 0.73    # 73% - Mais agressivo
else:
    margem_borrow = 0.69    # 69% - Normal
```

### Taxas e Custos
- **Taxa da plataforma**: 0.25% do repagamento
- **Fator de saúde**: 0.74 (supply colateralizado)
- **Limite de saúde**: 1.01 (mínimo seguro)
- **Fator aTokens livres**: 0.80

## 🔄 Algoritmo de Reescalonamento

### Estratégia de Reescalonamento

O algoritmo implementa um reescalonamento determinístico com prioridades claras:

```python
while tentativas < max_tentativas_reescalonamento:
    # 1. Tentar reinvestimento reduzido
    if reinvestimento_inicial > 0:
        multiplicador_reinv *= 0.95  # Reduz 5%
        if multiplicador_reinv < 1.0:
            flags_reescalonamento['reescalou_reinvestimento'] = True
    
    # 2. Tentar margem reduzida
    elif margem_borrow > margem_borrow_min:
        margem_borrow = max(margem_borrow_min, margem_borrow - 0.01)
        flags_reescalonamento['reescalou_margem'] = True
    
    # 3. Tentar repagamento reduzido
    elif proporcao_repagamento > repagamento_min:
        proporcao_repagamento = max(repagamento_min, proporcao_repagamento - 0.005)
        flags_reescalonamento['reescalou_repagamento'] = True
    
    # 4. Último recurso: aumentar margem
    else:
        margem_necessaria = (borrow_atual + novo_borrow_min) / supply_atual
        margem_borrow = min(0.73, max(margem_borrow, margem_necessaria + 1e-6))
```

### Características do Reescalonamento

1. **Determinístico**: Sempre segue a mesma ordem de prioridade
2. **Incremental**: Pequenos ajustes por tentativa
3. **Conservador**: Prioriza reinvestimento sobre margem
4. **Seguro**: Nunca excede limites de segurança
5. **Eficiente**: Para quando encontra solução viável

## ✅ Validações e Garantias

### Validações em Runtime

#### 1. Validação de Lucro
```python
lucro_operacao = novo_borrow_final - reinvestimento_final - repagamento - taxa_plataforma
assert lucro_operacao > min_lucro_op, f"Lucro deve ser positivo: {lucro_operacao}"
```

#### 2. Validação de Saúde
```python
saude = (supply_atual * 0.74) / borrow_atual
assert saude > 1.01, f"Saúde deve ser > 1.01: {saude}"
```

#### 3. Validação de Viabilidade
```python
if not meta_lucro_atingida:
    # Pular operação sem custos
    return self.supply_atual < self.supply_final_desejado
```

### Garantias Implementadas

1. **Lucro Positivo**: 100% das operações têm lucro ≥ min_lucro_op
2. **Saúde Mínima**: Todas as operações mantêm saúde > 1.01
3. **Sem Mascaramento**: Lucro garantido por construção, não por correção
4. **Determinismo**: Resultados reproduzíveis e previsíveis
5. **Limite de Tentativas**: Máximo 50 tentativas por operação
6. **Operação Nula**: Pula operação quando inviável

## 🧪 Testes e Validação

### Estrutura de Testes

```python
def rodar_testes():
    # Cenário A: Valores médios
    simulador_a = DeFiSimulator(1000, 600, 1500, 200)
    
    # Cenário B: Configuração agressiva
    simulador_b = DeFiSimulator(500, 300, 2000, 50)
    
    # Cenário C: 5 combinações pseudo-aleatórias
    for i in range(5):
        # Parâmetros aleatórios controlados
```

### Validações Automatizadas

```python
# Validações do Cenário A
assert estatisticas_a['porcentagem_lucro_positivo'] == 100.0
assert estatisticas_a['menor_lucro_por_operacao'] > 0
assert estatisticas_a['saude_final'] > 1.01
```

### Métricas de Qualidade

- **Cobertura de testes**: 100% dos cenários críticos
- **Validação de garantias**: Assertions rigorosas
- **Reprodutibilidade**: Seed fixo para resultados consistentes
- **Performance**: Testes em cenários extremos

## 📊 Análise de Performance

### Complexidade Computacional

| Operação | Complexidade | Descrição |
|----------|--------------|-----------|
| `calcular_reinvestimento()` | O(1) | Cálculo direto |
| `planejar_operacao()` | O(k) | k ≤ max_tentativas_reescalonamento |
| `executar_operacao()` | O(k) | k ≤ 5 (fallback) |
| `executar_simulacao()` | O(n×k) | n operações × k tentativas |

### Otimizações Implementadas

1. **Early Return**: Para quando encontra solução viável
2. **Caching**: Reutiliza cálculos quando possível
3. **Incremental**: Pequenos ajustes por tentativa
4. **Determinístico**: Evita loops desnecessários

### Limitações de Performance

- **Máximo tentativas**: 50 por operação (configurável)
- **Fallback limitado**: 5 tentativas por operação
- **Complexidade linear**: Cresce com número de operações

## 🔧 Troubleshooting

### Problemas Comuns

#### 1. Operações Anuladas
**Sintoma**: Logs "Operação ANULADA"
**Causa**: Sem passo viável para garantir lucro positivo
**Solução**: Ajustar parâmetros de configuração

#### 2. Alto Número de Tentativas
**Sintoma**: Tentativas próximas ao limite (50)
**Causa**: Configurações muito restritivas
**Solução**: Aumentar `max_tentativas_reescalonamento`

#### 3. Estagnação Excessiva
**Sintoma**: Muitas operações sem progresso
**Causa**: Objetivo muito agressivo
**Solução**: Reduzir `supply_final_desejado`

### Debugging

#### Logs Importantes
```python
# Verificar limites calculados
f"Novo Borrow Min Calculado: {novo_borrow_min_calculado:.6f}"
f"Novo Borrow Max Seguro: {novo_borrow_max_seguro:.6f}"

# Verificar tentativas de reescalonamento
f"Tentativas de Reescalonamento: {tentativas_reescalonamento}"
f"Flags Reescalonamento: {flags_reescalonamento}"
```

#### Métricas de Monitoramento
- **Menor lucro por operação**: Deve ser ≥ min_lucro_op
- **Porcentagem de lucro positivo**: Deve ser 100.0%
- **Saúde final**: Deve ser > 1.01
- **Total de tentativas**: Indicador de eficiência

### Configurações de Debug

```python
# Para debug detalhado
min_lucro_op = 1e-3  # Aumentar para facilitar
max_tentativas_reescalonamento = 100  # Aumentar limite
```

---

**Versão da Documentação**: 1.0  
**Última Atualização**: 2024  
**Compatibilidade**: Python 3.7+
