import logging
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

def conectar_plataforma():
    """Conecta ao MetaTrader 5 e exibe as informações da corretora e conta."""
    logger.info("Iniciando conexão com o MetaTrader 5...")
    print("Iniciando conexão com o MetaTrader 5...")
    
    if not mt5.initialize():
        logger.error(f"Falha ao inicializar o MetaTrader 5: {mt5.last_error()}")
        print("Falha ao inicializar o MetaTrader 5.")
        print("Erro:", mt5.last_error())
        mt5.shutdown()
        return False
    
    logger.info("Conectado com sucesso ao MetaTrader 5!")
    print("Conectado com sucesso ao MetaTrader 5!")
    
    terminal_info = mt5.terminal_info()
    if terminal_info is not None:
        logger.info(f"Terminal conectado com a corretora: {terminal_info.company}")
        print(f"Terminal conectado com a corretora: {terminal_info.company}")
        
    account_info = mt5.account_info()
    if account_info is not None:
        logger.info(f"Conta: {account_info.login} | Saldo: {account_info.balance} | Equity: {account_info.equity}")
        print(f"Conta: {account_info.login} | Saldo: {account_info.balance} | Equity: {account_info.equity}")
        
    return True

def desconectar_plataforma():
    """Fecha a conexão com o MetaTrader 5."""
    logger.info("Desconectando do MetaTrader 5...")
    print("Desconectando do MetaTrader 5...")
    mt5.shutdown()

def obter_posicoes(symbol=None):
    """Obtém todas as posições abertas ou filtra por símbolo."""
    if symbol:
        posicoes = mt5.positions_get(symbol=symbol)
    else:
        posicoes = mt5.positions_get()
    return posicoes

def detectar_tipo_preenchimento(symbol):
    """Detecta o tipo de preenchimento suportado pela corretora para o símbolo."""
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return mt5.ORDER_FILLING_FOK
        
    filling_mode = symbol_info.filling_mode
    if filling_mode & mt5.SYMBOL_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    elif filling_mode & mt5.SYMBOL_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    else:
        return mt5.ORDER_FILLING_RETURN

def abrir_posicao(symbol, action, volume, sl_points=None, tp_points=None):
    """Abre uma nova posição de COMPRA (BUY) ou VENDA (SELL).
    
    Args:
        symbol (str): O símbolo do ativo (ex: EURUSD, PETR4).
        action (str): 'BUY' ou 'SELL'.
        volume (float): Tamanho do lote.
        sl_points (int): Pontos de Stop Loss relativos ao preço de entrada.
        tp_points (int): Pontos de Take Profit relativos ao preço de entrada.
    """
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logger.error(f"Símbolo {symbol} não encontrado no MetaTrader 5.")
        print(f"Erro: Símbolo {symbol} não encontrado no MetaTrader 5.")
        return None

    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            logger.error(f"Falha ao selecionar/tornar visível o símbolo {symbol}.")
            print(f"Erro: Falha ao selecionar/tornar visível o símbolo {symbol}.")
            return None

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"Não foi possível obter a cotação (tick) para {symbol}.")
        print(f"Erro: Não foi possível obter a cotação para {symbol}.")
        return None

    filling_type = detectar_tipo_preenchimento(symbol)
    
    if action.upper() == "BUY":
        price = tick.ask
        type_order = mt5.ORDER_TYPE_BUY
        sl = price - (sl_points * symbol_info.point) if sl_points else 0.0
        tp = price + (tp_points * symbol_info.point) if tp_points else 0.0
    elif action.upper() == "SELL":
        price = tick.bid
        type_order = mt5.ORDER_TYPE_SELL
        sl = price + (sl_points * symbol_info.point) if sl_points else 0.0
        tp = price - (tp_points * symbol_info.point) if tp_points else 0.0
    else:
        logger.error(f"Ação desconhecida: {action}")
        print(f"Erro: Ação desconhecida {action}")
        return None

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": type_order,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 202606,
        "comment": "TradingAgents Execution",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_type,
    }

    logger.info(f"Enviando ordem de {action} para {symbol} (Lote: {volume}, Preço: {price})")
    print(f"Enviando ordem de {action} para {symbol} (Lote: {volume}, Preço: {price})...")
    
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Erro ao abrir posição: {result.retcode} - {result.comment}")
        print(f"Erro ao abrir posição: {result.retcode} - {result.comment}")
        return None

    logger.info(f"Posição aberta com sucesso! Ticket: {result.order}")
    print(f"Posição aberta com sucesso! Ticket: {result.order}")
    return result

def fechar_posicao(position):
    """Fecha uma posição aberta específica."""
    symbol = position.symbol
    filling_type = detectar_tipo_preenchimento(symbol)
    tick = mt5.symbol_info_tick(symbol)
    
    if tick is None:
        logger.error(f"Erro ao obter tick para fechar posição {position.ticket}")
        return False

    if position.type == mt5.POSITION_TYPE_BUY:
        price = tick.bid
        type_order = mt5.ORDER_TYPE_SELL
    else:
        price = tick.ask
        type_order = mt5.ORDER_TYPE_BUY

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": position.volume,
        "type": type_order,
        "position": position.ticket,
        "price": price,
        "deviation": 20,
        "magic": 202606,
        "comment": "TradingAgents Close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_type,
    }

    logger.info(f"Fechando posição {position.ticket} ({symbol})")
    print(f"Fechando posição {position.ticket} ({symbol})...")
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Erro ao fechar posição {position.ticket}: {result.retcode} - {result.comment}")
        print(f"Erro ao fechar posição {position.ticket}: {result.retcode} - {result.comment}")
        return False
        
    logger.info(f"Posição {position.ticket} fechada com sucesso.")
    print(f"Posição {position.ticket} fechada com sucesso.")
    return True

def fechar_todas_posicoes(symbol=None):
    """Fecha todas as posições abertas (opcionalmente filtrado por símbolo)."""
    posicoes = obter_posicoes(symbol)
    if not posicoes:
        logger.info("Nenhuma posição aberta encontrada para fechar.")
        print("Nenhuma posição aberta encontrada para fechar.")
        return

    logger.info(f"Fechando {len(posicoes)} posições abertas...")
    print(f"Fechando {len(posicoes)} posições abertas...")
    for pos in posicoes:
        fechar_posicao(pos)
