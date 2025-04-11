import logging
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from config import MESSAGES

TIMEFRAMES = [1, 5, 15, 30]  # Reduced timeframes for faster response
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for more detailed logs

class MarketAnalyzer:
    def __init__(self, symbol):
        self.symbol = symbol
        self.error_messages = MESSAGES['tg']['ERRORS']
        logger.info(f"Initialized MarketAnalyzer for {symbol}")

    def set_language(self, lang_code):
        self.error_messages = MESSAGES[lang_code]['ERRORS']
        logger.info(f"Language set to {lang_code}")

    def calculate_ema(self, data, period):
        return data.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, data, period=14):
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(self, data):
        exp1 = data.ewm(span=12, adjust=False).mean()
        exp2 = data.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        return macd, signal

    def calculate_bollinger_bands(self, data, period=20):
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper_band = sma + (std * 2)
        lower_band = sma - (std * 2)
        return upper_band, lower_band

    def get_market_data(self, minutes=30):
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=1)  # 1 day lookback for better data availability

            max_retries = 3
            retry_delay = 2

            for attempt in range(max_retries):
                try:
                    logger.debug(f"Attempt {attempt + 1}: Fetching data for {self.symbol}")
                    logger.debug(f"Time range: {start_time} to {end_time}")

                    ticker = yf.Ticker(self.symbol)
                    df = ticker.history(
                        start=start_time,
                        end=end_time,
                        interval='5m',  # Use 5m interval for better availability
                        prepost=True
                    )

                    logger.debug(f"Received data shape: {df.shape}")
                    logger.debug(f"Available columns: {df.columns}")

                    if df.empty:
                        logger.warning(f"Empty DataFrame received for {self.symbol}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay * (attempt + 1))
                            continue
                        return None, self.error_messages['NO_DATA']

                    # Add Volume column if missing (common for forex pairs)
                    if 'Volume' not in df.columns:
                        logger.info(f"Volume data not available for {self.symbol}, using placeholder values")
                        df['Volume'] = 1.0  # Use placeholder value for volume

                    required_columns = ['Open', 'High', 'Low', 'Close']
                    if not all(col in df.columns for col in required_columns):
                        logger.error(f"Missing required columns. Available: {df.columns}")
                        return None, self.error_messages['NO_DATA']

                    # Ensure proper datetime handling
                    df = df.reset_index()
                    if 'Date' in df.columns:
                        df = df.rename(columns={'Date': 'Datetime'})
                    elif 'Datetime' not in df.columns and df.index.name == 'Datetime':
                        df = df.reset_index()

                    df.set_index('Datetime', inplace=True)

                    # Convert to 1-minute data through interpolation
                    df = df.resample('1min').interpolate(method='time')
                    logger.debug(f"After resampling - shape: {df.shape}, columns: {df.columns}")

                    data_points = len(df)
                    logger.info(f"Successfully fetched {data_points} data points for {self.symbol}")

                    if data_points < minutes:
                        logger.warning(f"Insufficient data points: got {data_points}, needed {minutes}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay * (attempt + 1))
                            continue
                        return None, self.error_messages['NO_DATA']

                    return df.tail(minutes), None

                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    return None, self.error_messages['TIMEOUT_ERROR']

        except Exception as e:
            logger.error(f"Critical error in get_market_data: {str(e)}")
            return None, self.error_messages['GENERAL_ERROR']

    def analyze_timeframe(self, df, minutes):
        if df is None or len(df) < minutes:
            return 'NEUTRAL', 0, {'confidence': 50, 'expiration': minutes}, None

        try:
            recent_data = df.tail(minutes)
            close_prices = recent_data['Close']
            volume = recent_data['Volume']

            # Technical Indicators
            ema_7 = self.calculate_ema(close_prices, 7)
            ema_21 = self.calculate_ema(close_prices, 21)
            rsi = self.calculate_rsi(close_prices)
            macd, macd_signal = self.calculate_macd(close_prices)
            upper_band, lower_band = self.calculate_bollinger_bands(close_prices)

            # Price Analysis
            start_price = close_prices.iloc[0]
            end_price = close_prices.iloc[-1]
            price_change = ((end_price - start_price) / start_price) * 100

            # Volume Analysis
            avg_volume = volume.mean()
            current_volume = volume.iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            volume_strength = (
                3 if volume_ratio > 1.5 else  # Снизили порог с 2.0 до 1.5
                2 if volume_ratio > 1.2 else  # Снизили порог с 1.5 до 1.2
                1 if volume_ratio > 1.0 else
                0
            )

            logger.info(f"Volume analysis - ratio: {volume_ratio:.2f}, strength: {volume_strength}")

            # Signal Analysis
            trend_signals = []

            # EMA Signals
            ema_diff_percent = ((ema_7.iloc[-1] - ema_21.iloc[-1]) / ema_21.iloc[-1]) * 100
            if ema_diff_percent > 0.05:  # Снизили порог с 0.1% до 0.05%
                trend_signals.append(1)
            elif ema_diff_percent < -0.05:
                trend_signals.append(-1)

            logger.info(f"EMA analysis - diff: {ema_diff_percent:.2f}%")

            # MACD Signal
            macd_diff = macd.iloc[-1] - macd_signal.iloc[-1]
            macd_trend = macd.iloc[-1] - macd.iloc[-2]  # Изменение MACD
            if macd_diff > 0:
                trend_signals.append(1)
                if macd_trend > 0:  # Тренд MACD растет
                    trend_signals.append(1)
            else:
                trend_signals.append(-1)
                if macd_trend < 0:  # Тренд MACD падает
                    trend_signals.append(-1)

            logger.info(f"MACD analysis - diff: {macd_diff:.4f}, trend: {macd_trend:.4f}")

            # RSI Signals - усилили влияние RSI
            last_rsi = rsi.iloc[-1]
            if last_rsi < 35:
                trend_signals.extend([2, 1])  # Добавили дополнительный сигнал на покупку
            elif last_rsi > 65:
                trend_signals.extend([-2, -1])  # Добавили дополнительный сигнал на продажу
            elif last_rsi < 45:
                trend_signals.append(1)
            elif last_rsi > 55:
                trend_signals.append(-1)

            logger.info(f"RSI analysis - value: {last_rsi:.1f}")

            # Bollinger Bands Signal
            current_price = close_prices.iloc[-1]
            bb_position = 'normal'
            if current_price < lower_band.iloc[-1]:
                trend_signals.append(2)  # Strong buy signal
                bb_position = 'oversold'
            elif current_price > upper_band.iloc[-1]:
                trend_signals.append(-2)  # Strong sell signal
                bb_position = 'overbought'

            logger.info(f"BB analysis - position: {bb_position}")

            # Calculate signal strength
            trend_strength = sum(trend_signals)
            trend_strength *= (1 + (volume_strength * 0.2))  # Volume impact

            logger.info(f"Signal analysis - trend signals: {trend_signals}, final strength: {trend_strength:.2f}")

            # Signal determination
            confidence = 50 + (abs(trend_strength) * 5)  # Base confidence on strength
            confidence = min(95, max(50, confidence))  # Cap between 50-95%

            if abs(trend_strength) >= 1.2:  # Снизили порог с 1.5 до 1.2
                signal = 'BUY' if trend_strength > 0 else 'SELL'
            else:
                signal = 'NEUTRAL'

            logger.info(f"Final signal: {signal} with confidence: {confidence:.1f}%")

            indicators = {
                'confidence': round(confidence, 1),
                'expiration': minutes,
                'rsi': round(last_rsi, 2),
                'macd': round(macd.iloc[-1], 4),
                'bb_position': bb_position
            }

            return signal, price_change, indicators, None

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return 'NEUTRAL', 0, {'confidence': 50, 'expiration': minutes}, str(e)

    def analyze_market(self):
        try:
            logger.info(f"Starting market analysis for {self.symbol}")
            df, error_message = self.get_market_data(minutes=max(TIMEFRAMES) + 5)

            if error_message:
                logger.error(f"Market data error for {self.symbol}: {error_message}")
                return {'error': error_message}

            if df is None or df.empty:
                logger.error(f"No market data available for {self.symbol}")
                return {'error': self.error_messages['NO_DATA']}

            current_price = df['Close'].iloc[-1]
            timeframe_analysis = {}

            for minutes in TIMEFRAMES:
                logger.debug(f"Analyzing {minutes}min timeframe for {self.symbol}")
                signal, change, indicators, error = self.analyze_timeframe(df, minutes)

                if error:
                    logger.error(f"Error analyzing {minutes}min timeframe: {error}")

                timeframe_analysis[minutes] = {
                    'signal': signal,
                    'change': change,
                    'indicators': indicators
                }
                logger.debug(f"{minutes}min analysis complete - Signal: {signal}, Change: {change:.2f}%")

            return {
                'current_price': current_price,
                'timeframes': timeframe_analysis,
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"Market analysis error for {self.symbol}: {str(e)}")
            return {'error': self.error_messages['GENERAL_ERROR']}