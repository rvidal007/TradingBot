import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import scipy.signal
import matplotlib.pyplot as plt
import MetaTrader5 as mt5

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Importação dos módulos customizados de execução e dados do MT5
from tradingagents.execution.mt5_execution import (
    conectar_plataforma,
    desconectar_plataforma,
    obter_posicoes,
    abrir_posicao,
    fechar_posicao,
)
from tradingagents.dataflows.metatrader import get_mt5_candles

# Configuração de logging básico
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Parâmetros de Execução do Robô
SYMBOL = "EURUSD"        # Ativo para ser negociado no MetaTrader 5
VOLUME = 0.01            # Volume da ordem (Lote padrão mínimo)
SL_POINTS = 100          # Stop Loss em pontos (opcional)
TP_POINTS = 200          # Take Profit em pontos (opcional)

def map_to_yfinance(symbol: str) -> str:
    """Mapeia símbolos do MetaTrader 5 para o formato esperado pelo yfinance."""
    sym = symbol.upper()
    if sym == "EURUSD":
        return "EURUSD=X"
    if sym == "GBPUSD":
        return "GBPUSD=X"
    if sym == "USDJPY":
        return "USDJPY=X"
    if sym == "AUDUSD":
        return "AUDUSD=X"
    return symbol

def main():
    print("==================================================")
    print("           TRADINGBOT - METATRADER 5 ROBOT        ")
    print("==================================================")
    
    # 1. Conectar à plataforma MetaTrader 5
    if not conectar_plataforma():
        print("Erro: Não foi possível conectar ao MetaTrader 5. Encerrando bot.")
        return

    try:
        # 2. Obter os candles recentes do MT5
        # Usamos 100 candles diários como base
        df = get_mt5_candles(SYMBOL, timeframe=mt5.TIMEFRAME_D1, n_candles=100)
        if df.empty:
            print(f"Erro: Não foi possível carregar os dados históricos para o ativo {SYMBOL}.")
            return
            
        # 3. Processamento de Séries Temporais com Scipy
        closes = df['Close'].values
        
        # Filtro Savitzky-Golay para suavizar o ruído de preço e identificar tendência
        # window_length deve ser ímpar. 15 barras representa cerca de 3 semanas de dados.
        smoothed = scipy.signal.savgol_filter(closes, window_length=15, polyorder=3)
        
        # Detecção de Picos e Vales locais usando scipy.signal.find_peaks
        # Isto nos ajuda a identificar suportes e resistências matemáticas locais
        peaks, _ = scipy.signal.find_peaks(closes, distance=10)
        valleys, _ = scipy.signal.find_peaks(-closes, distance=10)
        
        print("Processamento de dados com Numpy e Scipy concluído.")
        
        # 4. Executar Motor de Inteligência Artificial (TradingAgents Graph)
        print("Preparando o motor de dados do agente...")
        config = DEFAULT_CONFIG.copy()
        
        # Inicializa o grafo com as configurações padrão (carregadas do arquivo .env)
        ta = TradingAgentsGraph(debug=True, config=config)
        
        # A data de análise será a data do último candle obtido
        trade_date = df.index[-1].strftime("%Y-%m-%d")
        yf_symbol = map_to_yfinance(SYMBOL)
        
        print(f"Iniciando a propagação do agente para {yf_symbol} na data {trade_date}...")
        _, signal = ta.propagate(yf_symbol, trade_date)
        
        print(f"\nSinal de negociação retornado pelo agente: {signal.upper()}")
        
        # 5. Execução de Ordens baseada no sinal do agente
        # Mapeamento:
        # - BUY/OVERWEIGHT -> Compra (fecha vendas abertas)
        # - SELL/UNDERWEIGHT -> Venda (fecha compras abertas)
        # - HOLD -> Nenhuma ação tomada
        
        posicoes = obter_posicoes(SYMBOL)
        compras_abertas = [p for p in posicoes if p.type == mt5.POSITION_TYPE_BUY]
        vendas_abertas = [p for p in posicoes if p.type == mt5.POSITION_TYPE_SELL]
        
        if signal.lower() in ["buy", "overweight"]:
            print("Sinal COMPRADOR recebido!")
            # Fechar qualquer venda aberta
            for v in vendas_abertas:
                fechar_posicao(v)
            # Se não houver compras abertas, abrir uma nova compra
            if not compras_abertas:
                abrir_posicao(SYMBOL, "BUY", VOLUME, sl_points=SL_POINTS, tp_points=TP_POINTS)
            else:
                print("Já existe uma posição de compra ativa para este símbolo.")
                
        elif signal.lower() in ["sell", "underweight"]:
            print("Sinal VENDEDOR recebido!")
            # Fechar qualquer compra aberta
            for c in compras_abertas:
                fechar_posicao(c)
            # Se não houver vendas abertas, abrir uma nova venda
            if not vendas_abertas:
                abrir_posicao(SYMBOL, "SELL", VOLUME, sl_points=SL_POINTS, tp_points=TP_POINTS)
            else:
                print("Já existe uma posição de venda ativa para este símbolo.")
                
        else: # HOLD
            print("Sinal NEUTRO (HOLD). Nenhuma operação de trading executada.")
            
        # 6. Geração de Gráfico com Matplotlib
        plt.figure(figsize=(12, 6))
        plt.plot(df.index, closes, label="Preço de Fechamento Real", color="#3b82f6", linewidth=1.5)
        plt.plot(df.index, smoothed, label="Tendência Suavizada (Savitzky-Golay)", color="#10b981", linestyle="--", linewidth=1.5)
        plt.scatter(df.index[peaks], closes[peaks], color="#ef4444", marker="^", s=80, label="Picos Locais (Resistência)")
        plt.scatter(df.index[valleys], closes[valleys], color="#8b5cf6", marker="v", s=80, label="Vales Locais (Suporte)")
        
        plt.title(f"TradingBot - Análise de Preços para {SYMBOL} | Decisão: {signal}", fontsize=14, fontweight="bold")
        plt.xlabel("Data")
        plt.ylabel("Preço")
        plt.grid(True, linestyle=":", alpha=0.6)
        plt.legend()
        plt.tight_layout()
        
        # Salva o gráfico
        chart_name = "trading_bot_chart.png"
        plt.savefig(chart_name)
        print(f"Gráfico de análise salvo com sucesso como '{chart_name}'!")
        
    except Exception as e:
        logger.error(f"Erro durante a execução do robô: {e}", exc_info=True)
        print(f"Erro na execução do bot: {e}")
    finally:
        # 7. Desconectar da plataforma de forma limpa
        desconectar_plataforma()
        print("Bot finalizado com sucesso.")

if __name__ == "__main__":
    main()
