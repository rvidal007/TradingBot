import logging
import MetaTrader5 as mt5
import pandas as pd

logger = logging.getLogger(__name__)

def get_mt5_candles(symbol: str, timeframe=mt5.TIMEFRAME_D1, n_candles: int = 100) -> pd.DataFrame:
    """Obtém os últimos n_candles históricos de preços do MetaTrader 5 para o símbolo informado."""
    logger.info(f"Buscando {n_candles} candles do MetaTrader 5 para o ativo {symbol}...")
    print(f"Buscando {n_candles} candles do MetaTrader 5 para o ativo {symbol}...")
    
    # Verifica se o símbolo está disponível e visível
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logger.error(f"Símbolo {symbol} não encontrado para consulta de histórico.")
        print(f"Erro: Símbolo {symbol} não encontrado para consulta de histórico.")
        return pd.DataFrame()
        
    if not symbol_info.visible:
        mt5.symbol_select(symbol, True)
        
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_candles)
    if rates is None or len(rates) == 0:
        err = mt5.last_error()
        logger.error(f"Falha ao obter candles para {symbol}. Código de erro: {err}")
        print(f"Erro ao obter candles para {symbol}: {err}")
        return pd.DataFrame()
        
    # Converter para DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Renomear as colunas para o padrão do Pandas/YFinance esperado pelas ferramentas
    df.rename(columns={
        'time': 'Date',
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'tick_volume': 'Volume'
    }, inplace=True)
    
    df.set_index('Date', inplace=True)
    logger.info(f"Sucesso: {len(df)} candles carregados.")
    print(f"Sucesso: {len(df)} candles carregados.")
    return df
