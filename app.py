import streamlit as st
from streamlit_lightweight_charts import renderLightweightCharts
import json
import numpy as np
import pandas as pd
from binance.client import Client

selected_coin = st.selectbox("Coin", options=["BTCUSDT", "ETHUSDT", "DOGEUSDT"])

COLOR_BULL = 'rgba(38,166,154,0.9)'  # #26a69a
COLOR_BEAR = 'rgba(239,83,80,0.9)'   # #ef5350

# Initialize Binance client
client = Client()

# Request historic pricing data via Binance API
klines = client.get_historical_klines(selected_coin, Client.KLINE_INTERVAL_1DAY, "4 months ago UTC")
df = pd.DataFrame(klines, columns=['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
                                    'Close Time', 'Quote Asset Volume', 'Number of Trades',
                                    'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume', 'Ignore'])

# Data wrangling to match required format
df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
df = df[['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume']]
df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']  # rename columns
df['time'] = df['time'].dt.strftime('%Y-%m-%d')  # Date to string
df['open'] = df['open'].astype(float)
df['close'] = df['close'].astype(float)
df['high'] = df['high'].astype(float)
df['low'] = df['low'].astype(float)
df['volume'] = df['volume'].astype(float)

# Calculate MACD manually
def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    df['EMA_fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
    df['EMA_slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
    df['MACD'] = df['EMA_fast'] - df['EMA_slow']
    df['MACD_signal'] = df['MACD'].ewm(span=signal_period, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    return df

df = calculate_macd(df)

# Export to JSON format
candles = json.loads(df.to_json(orient="records"))
volume = json.loads(df.rename(columns={"volume": "value"}).to_json(orient="records"))
macd_fast = json.loads(df.rename(columns={"MACD": "value"}).to_json(orient="records"))
macd_slow = json.loads(df.rename(columns={"MACD_signal": "value"}).to_json(orient="records"))
macd_hist = json.loads(df.rename(columns={"MACD_hist": "value"}).to_json(orient="records"))

# Determine colors for candlestick and MACD histogram
df['color'] = np.where(df['open'] > df['close'], COLOR_BEAR, COLOR_BULL)  # bull or bear
macd_hist_color = np.where(df['MACD_hist'] > 0, COLOR_BULL, COLOR_BEAR)

chartMultipaneOptions = [
    {
        "width": 600,
        "height": 400,
        "layout": {
            "background": {
                "type": "solid",
                "color": 'white'
            },
            "textColor": "black"
        },
        "grid": {
            "vertLines": {
                "color": "rgba(197, 203, 206, 0.5)"
            },
            "horzLines": {
                "color": "rgba(197, 203, 206, 0.5)"
            }
        },
        "crosshair": {
            "mode": 0
        },
        "priceScale": {
            "borderColor": "rgba(197, 203, 206, 0.8)"
        },
        "timeScale": {
            "borderColor": "rgba(197, 203, 206, 0.8)",
            "barSpacing": 15
        },
        "watermark": {
            "visible": True,
            "fontSize": 48,
            "horzAlign": 'center',
            "vertAlign": 'center',
            "color": 'rgba(171, 71, 188, 0.3)',
            "text": f'{selected_coin} - D1',
        }
    },
    {
        "width": 600,
        "height": 100,
        "layout": {
            "background": {
                "type": 'solid',
                "color": 'transparent'
            },
            "textColor": 'black',
        },
        "grid": {
            "vertLines": {
                "color": 'rgba(42, 46, 57, 0)',
            },
            "horzLines": {
                "color": 'rgba(42, 46, 57, 0.6)',
            }
        },
        "timeScale": {
            "visible": False,
        },
        "watermark": {
            "visible": True,
            "fontSize": 18,
            "horzAlign": 'left',
            "vertAlign": 'top',
            "color": 'rgba(171, 71, 188, 0.7)',
            "text": 'Volume',
        }
    },
    {
        "width": 600,
        "height": 200,
        "layout": {
            "background": {
                "type": "solid",
                "color": 'white'
            },
            "textColor": "black"
        },
        "timeScale": {
            "visible": False,
        },
        "watermark": {
            "visible": True,
            "fontSize": 18,
            "horzAlign": 'left',
            "vertAlign": 'center',
            "color": 'rgba(171, 71, 188, 0.7)',
            "text": 'MACD',
        }
    }
]

seriesCandlestickChart = [
    {
        "type": 'Candlestick',
        "data": candles,
        "options": {
            "upColor": COLOR_BULL,
            "downColor": COLOR_BEAR,
            "borderVisible": False,
            "wickUpColor": COLOR_BULL,
            "wickDownColor": COLOR_BEAR
        }
    }
]

seriesVolumeChart = [
    {
        "type": 'Histogram',
        "data": volume,
        "options": {
            "priceFormat": {
                "type": 'volume',
            },
            "priceScaleId": ""  # set as an overlay setting,
        },
        "priceScale": {
            "scaleMargins": {
                "top": 0,
                "bottom": 0,
            },
            "alignLabels": False
        }
    }
]

seriesMACDchart = [
    {
        "type": 'Line',
        "data": macd_fast,
        "options": {
            "color": 'blue',
            "lineWidth": 2
        }
    },
    {
        "type": 'Line',
        "data": macd_slow,
        "options": {
            "color": 'green',
            "lineWidth": 2
        }
    },
    {
        "type": 'Histogram',
        "data": macd_hist,
        "options": {
            "color": 'red',
            "lineWidth": 1
        }
    }
]


def find_days_with_gape(n, df):
    # Вычисление разницы и процентного соотношения
    df['difference'] = df['high'] - df['low']
    df['percentage_difference'] = (df['difference'] / df['low']) * 100

    # Фильтрация дней с разницей больше n%
    filtered_days = df[df['percentage_difference'] > n]

    if not filtered_days.empty:
        with st.expander("Показать дни с большой разницей"):
            st.dataframe(filtered_days[['time', 'high', 'low', 'percentage_difference']])
    else:
        st.write("Нет дней с разницей больше чем", n, "%")


gape = st.text_input("Какой процент gape должен быть")
gape_btn = st.button("Найти")

if gape_btn:
    if gape != "":
        find_days_with_gape(int(gape), df)


with st.expander("Графики"):
    st.button("Обновить", on_click=renderLightweightCharts([
        {
            "chart": chartMultipaneOptions[0],
            "series": seriesCandlestickChart
        },
        {
            "chart": chartMultipaneOptions[1],
            "series": seriesVolumeChart
        },
        {
            "chart": chartMultipaneOptions[2],
            "series": seriesMACDchart
        }
    ], 'multipane'))