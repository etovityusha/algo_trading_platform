import asyncio
import datetime
from decimal import Decimal

from environs import Env

from producers.trand.strategy import TrandStrategy
from src.core.backtest import Backtester
from src.core.clients.bybit_async import BybitAsyncClient


async def main():
    env = Env()
    env.read_env()
    apikey = env.str("BYBIT_RO__API_KEY")
    api_secret = env.str("BYBIT_RO__API_SECRET")

    if apikey is None or apikey is None:
        raise ValueError("APIKEY or APISECRET is not configured")
    client = BybitAsyncClient(api_key=apikey, api_secret=api_secret, is_demo=False)

    strategy = TrandStrategy(client)
    backtester = Backtester(client)
    symbol = "BTCUSDT"
    start_date = datetime.datetime(2025, 8, 10)
    end_date = datetime.datetime(2025, 8, 31)

    print(f"Запускаем бэктест для {symbol}")
    print(f"Период: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
    print(f"Стратегия: {strategy.get_config().name}")
    print("-" * 50)

    # Запускаем бэктест
    result = await backtester.run(strategy, symbol, start_date, end_date)

    # Выводим результаты
    print(f"Всего сделок: {result.total_trades}")
    print(f"Общая доходность: {result.total_return_percent:.2f}%")
    print(f"Процент прибыльных сделок: {result.win_rate:.2f}%")
    print(f"Доход USD: {round(result.total_income, 2)}")
    print(
        f"Объем торгов USD: {round(result.total_volume, 2)}, "
        f"Расходы на комиссию USD: {round(result.total_volume * Decimal(0.006), 2)}"
    )
    print("-" * 50)

    # Показываем детали по сделкам
    for i, trade in enumerate(result.trades[:5]):  # Первые 5 сделок
        status = "✅ Закрыта" if trade.is_closed else "⏳ Открыта"
        pnl = f"{trade.pnl_percent:.2f}%" if trade.is_closed else "N/A"
        print(f"Сделка {i + 1}: {status}, PnL: {pnl}")
        print(f"  Открытие: {trade.open_time.strftime('%Y-%m-%d %H:%M')} по ${trade.open_price}")
        if trade.is_closed:
            print(f"  Закрытие: {trade.close_time.strftime('%Y-%m-%d %H:%M')} по ${trade.close_price}")

    if len(result.trades) > 5:
        print(f"... и еще {len(result.trades) - 5} сделок")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
