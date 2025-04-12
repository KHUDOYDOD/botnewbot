from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import io
import random
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_welcome_image():
    try:
        # Создаем изображение с высоким качеством
        width, height = 1200, 700
        image = Image.new('RGB', (width, height), color=(15, 20, 30))
        draw = ImageDraw.Draw(image)
        
        # Создаем градиентный фон - темно-синий к темно-фиолетовому с глубиной
        for i in range(height):
            progress = i / height
            color = (
                int(15 + progress * 15),  # темно-синий
                int(20 + progress * 10),  # с оттенком фиолетового
                int(30 + progress * 20)   # более глубокий синий
            )
            draw.line([(0, i), (width, i)], fill=color)
        
        # Добавляем сетку с лёгким эффектом глубины
        grid_spacing = 40
        for x in range(0, width, grid_spacing):
            opacity = int(30 + 10 * math.sin(x / 100))
            draw.line([(x, 0), (x, height)], fill=(255, 255, 255, opacity), width=1)
        
        for y in range(0, height, grid_spacing):
            opacity = int(30 + 10 * math.sin(y / 100))
            draw.line([(0, y), (width, y)], fill=(255, 255, 255, opacity), width=1)
        
        # Добавляем декоративные круги и световые эффекты на фоне
        for _ in range(10):
            circle_x = random.randint(50, width-50)
            circle_y = random.randint(50, height-50)
            circle_size = random.randint(100, 300)
            circle_opacity = random.randint(10, 30)
            
            # Используем разные цвета для разных кругов
            circle_colors = [
                (60, 80, 170, circle_opacity),  # голубой
                (80, 40, 120, circle_opacity),  # фиолетовый
                (30, 100, 120, circle_opacity)  # сине-зеленый
            ]
            
            circle_color = random.choice(circle_colors)
            
            # Создаем круг с градиентной прозрачностью
            for r in range(circle_size):
                # Радиальный градиент прозрачности
                alpha = int(circle_opacity * (1 - r/circle_size))
                if alpha <= 0:
                    continue
                    
                current_color = (circle_color[0], circle_color[1], circle_color[2], alpha)
                draw.ellipse(
                    [(circle_x - r, circle_y - r), (circle_x + r, circle_y + r)],
                    outline=current_color
                )

        # Создаем реалистичный график с matplotlib
        fig = Figure(figsize=(8, 6), dpi=100)
        fig.patch.set_alpha(0.0)  # Прозрачный фон
        ax = fig.add_subplot(111)
        
        # Создаем более реалистичный график торговли
        n_candles = 40
        
        # Начальная точка
        start_price = 100
        
        # Создаем тренд с реалистичным движением цены
        # Создаем микро-тренды
        trend_changes = np.random.choice([-1, 0, 1], size=8) * 5
        trends = []
        for change in trend_changes:
            trends.extend([change] * 5)
        
        # Добавляем случайные колебания
        volatility = np.random.normal(0, 0.8, n_candles)
        
        # Строим цену
        price = start_price
        prices = [price]
        
        for i in range(1, n_candles):
            # Применяем тренд и волатильность
            price += trends[i % len(trends)] * 0.1 + volatility[i]
            prices.append(price)
        
        prices = np.array(prices)
        
        # Генерируем OHLC данные
        dates = np.arange(n_candles)
        highs = prices + np.random.uniform(0.1, 0.5, n_candles)
        lows = prices - np.random.uniform(0.1, 0.5, n_candles)
        
        # Генерируем open/close с учетом направления свечей
        is_up = np.random.choice([True, False], size=n_candles, p=[0.55, 0.45])  # Больше растущих свечей для позитивного вида
        
        opens = np.zeros(n_candles)
        closes = np.zeros(n_candles)
        
        for i in range(n_candles):
            if i > 0:
                opens[i] = closes[i-1] + np.random.normal(0, 0.1)
            else:
                opens[i] = prices[i] - 0.2
            
            if is_up[i]:
                closes[i] = opens[i] + abs(np.random.normal(0, 0.4))
            else:
                closes[i] = opens[i] - abs(np.random.normal(0, 0.3))
            
            # Корректируем high/low
            highs[i] = max(highs[i], opens[i], closes[i]) + np.random.uniform(0.05, 0.15)
            lows[i] = min(lows[i], opens[i], closes[i]) - np.random.uniform(0.05, 0.15)
        
        # Рисуем свечи
        width_candle = 0.6
        up_color = '#00cc66'  # Более профессиональный зеленый
        down_color = '#ff3b3b'  # Более профессиональный красный
        
        for i in range(n_candles):
            if closes[i] >= opens[i]:
                color = up_color
            else:
                color = down_color
            
            # Рисуем тело свечи
            ax.bar(dates[i], closes[i] - opens[i], width_candle, bottom=min(opens[i], closes[i]), color=color, alpha=0.85)
            
            # Рисуем тени (фитили)
            ax.plot([dates[i], dates[i]], [lows[i], highs[i]], color='white', linewidth=0.8)
        
        # Добавляем визуальные индикаторы
        # Скользящие средние
        ma20 = np.convolve(closes, np.ones(10)/10, mode='valid')
        ma50 = np.convolve(closes, np.ones(20)/20, mode='valid')
        
        # График объемов внизу (гистограмма)
        volumes = np.random.uniform(100000, 1000000, n_candles)
        volumes[is_up] *= 1.5  # Больше объема на растущих свечах
        
        # Создаем подграфик для объемов (занимает 20% высоты основного графика)
        ax_volumes = ax.twinx()
        ax_volumes.set_ylim(0, max(volumes) * 1.5)
        
        # Рисуем гистограмму объемов с цветами соответствующими свечам
        for i in range(n_candles):
            if closes[i] >= opens[i]:
                color = '#33ff99'  # Более светлый зеленый для объема
            else:
                color = '#ff6666'  # Более светлый красный для объема
                
            ax_volumes.bar(dates[i], volumes[i], width=0.8, color=color, alpha=0.3)
        
        # Настраиваем вид оси объемов
        ax_volumes.set_yticks([])
        ax_volumes.set_xticks([])
        
        # Добавляем МА на график
        ma_start_idx = 9
        ma_dates = dates[ma_start_idx:]
        ax.plot(ma_dates, ma20, color='#ffcc00', linewidth=1.5, alpha=0.8, label='MA10')
        
        ma_start_idx2 = 19
        ma_dates2 = dates[ma_start_idx2:]
        ax.plot(ma_dates2, ma50, color='#ff00ff', linewidth=1.5, alpha=0.8, label='MA20')
        
        # Добавляем уровни поддержки и сопротивления
        resistance_level = np.percentile(highs, 85)
        support_level = np.percentile(lows, 15)
        
        ax.axhline(y=resistance_level, color='#ffff77', linestyle='--', alpha=0.6, linewidth=1)
        ax.axhline(y=support_level, color='#77ffff', linestyle='--', alpha=0.6, linewidth=1)
        
        # Настройка внешнего вида графика
        ax.set_facecolor('#151b2c')  # Темно-синий фон
        ax.grid(color='#2a3a5a', linestyle='--', linewidth=0.5, alpha=0.5)
        
        # Настройка осей
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#ffffff')
        ax.spines['left'].set_color('#ffffff')
        ax.tick_params(axis='x', colors='white', labelsize=8)
        ax.tick_params(axis='y', colors='white', labelsize=8)
        
        # Добавляем подписи цен по оси Y
        min_price = min(lows)
        max_price = max(highs)
        ax.set_yticks([min_price, (min_price + max_price)/2, max_price])
        ax.set_yticklabels([f"{min_price:.2f}", f"{(min_price + max_price)/2:.2f}", f"{max_price:.2f}"])
        
        # Метки времени по оси X
        time_labels = ['09:30', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00']
        time_positions = np.linspace(0, n_candles-1, len(time_labels)).astype(int)
        ax.set_xticks(time_positions)
        ax.set_xticklabels(time_labels, rotation=45)
        
        # Добавляем аннотации
        ax.annotate('Восходящий тренд', xy=(n_candles//2, max_price*0.95), 
                   xytext=(n_candles//2-5, max_price*1.01),
                   color='white', alpha=0.7, fontsize=8,
                   arrowprops=dict(arrowstyle='->', color='white', alpha=0.5))
        
        ax.annotate('Уровень поддержки', xy=(n_candles-10, support_level), 
                   xytext=(n_candles-15, support_level-1),
                   color='#77ffff', alpha=0.7, fontsize=8,
                   arrowprops=dict(arrowstyle='->', color='#77ffff', alpha=0.5))
        
        # Преобразуем график в изображение
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        buf = io.BytesIO()
        canvas.print_png(buf)
        buf.seek(0)
        chart_img = Image.open(buf)
        
        # Добавляем лёгкую тень к графику для эффекта парения
        shadow = Image.new('RGBA', chart_img.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rectangle([(5, 5), (chart_img.width-5, chart_img.height-5)], fill=(0, 0, 0, 50))
        shadow = shadow.filter(ImageFilter.GaussianBlur(10))
        
        # Размещаем график на основном изображении с тенью
        image.paste(shadow.convert('RGB'), (670, 120), shadow)
        image.paste(chart_img, (650, 100))
        
        # Добавляем стильный терминал трейдера слева
        terminal_width = 550
        terminal_height = 400
        terminal_x = 50
        terminal_y = 150
        
        # Создаем эффект цифрового интерфейса терминала
        terminal = Image.new('RGBA', (terminal_width, terminal_height), (0, 0, 0, 0))
        terminal_draw = ImageDraw.Draw(terminal)
        
        # Фон терминала с эффектом стекла
        terminal_draw.rectangle(
            [(0, 0), (terminal_width, terminal_height)],
            fill=(20, 30, 60, 180),
            outline=(100, 130, 200, 150),
            width=2
        )
        
        # Добавляем линии разделения на экране терминала
        terminal_draw.line([(20, 60), (terminal_width-20, 60)], fill=(100, 150, 220, 180), width=1)
        
        # Добавляем цифровые данные на терминале
        pairs = [
            ("BTC/USD", "41,235.67", "+2.45%", "#33ff99"),
            ("ETH/USD", "2,876.45", "+1.83%", "#33ff99"),
            ("EUR/USD", "1.0824", "-0.26%", "#ff6666"),
            ("GBP/USD", "1.2651", "+0.31%", "#33ff99"),
            ("USD/JPY", "143.87", "-0.15%", "#ff6666"),
            ("XAU/USD", "2,354.28", "+0.77%", "#33ff99")
        ]
        
        y_pos = 80
        for pair, price, change, color in pairs:
            # Валютная пара
            terminal_draw.text((30, y_pos), pair, fill=(220, 220, 255), font=ImageFont.load_default())
            
            # Цена
            terminal_draw.text((170, y_pos), price, fill=(255, 255, 255), font=ImageFont.load_default())
            
            # Изменение
            terminal_draw.text((300, y_pos), change, fill=color, font=ImageFont.load_default())
            
            y_pos += 30
        
        # Добавляем заголовок терминала
        terminal_draw.text((20, 20), "ТОРГОВЫЙ ТЕРМИНАЛ", fill=(255, 255, 255), font=ImageFont.load_default())
        
        # Добавляем мини-индикаторы на терминале
        mini_chart_width = 150
        mini_chart_height = 60
        mini_chart_x = terminal_width - mini_chart_width - 20
        mini_chart_y = 80
        
        # Создаем мини-график
        mini_chart = Image.new('RGBA', (mini_chart_width, mini_chart_height), (30, 40, 70, 200))
        mini_chart_draw = ImageDraw.Draw(mini_chart)
        
        # Рисуем линию графика
        points = []
        for i in range(30):
            x = i * (mini_chart_width / 30)
            # Создаем восходящий тренд для эффекта оптимизма
            y = mini_chart_height - (30 + i/1.5 + random.uniform(-5, 5))
            points.append((x, y))
        
        # Рисуем линию с градиентом
        for i in range(len(points)-1):
            mini_chart_draw.line([points[i], points[i+1]], fill="#00ffaa", width=2)
        
        # Добавляем заливку под линией графика
        fill_points = points.copy()
        fill_points.append((mini_chart_width, mini_chart_height))
        fill_points.append((0, mini_chart_height))
        mini_chart_draw.polygon(fill_points, fill=(0, 255, 170, 30))
        
        # Добавляем мини-график на терминал
        terminal.paste(mini_chart, (mini_chart_x, mini_chart_y), mini_chart)
        
        # Добавляем текст над мини-графиком
        terminal_draw.text((mini_chart_x, mini_chart_y - 20), "BTC/USD - H4", fill=(180, 230, 255), font=ImageFont.load_default())
        
        # Добавляем фейковую кнопку для анализа
        button_width = 200
        button_height = 40
        button_x = (terminal_width - button_width) // 2
        button_y = terminal_height - 70
        
        button = Image.new('RGBA', (button_width, button_height), (0, 0, 0, 0))
        button_draw = ImageDraw.Draw(button)
        
        # Градиент для кнопки
        for i in range(button_height):
            progress = i / button_height
            color = (
                int(30 + progress * 50),
                int(100 + progress * 80),
                int(200 + progress * 50),
                180
            )
            button_draw.line([(0, i), (button_width, i)], fill=color)
        
        # Добавляем контур кнопки
        button_draw.rectangle([(0, 0), (button_width, button_height)], outline=(150, 200, 255), width=1)
        
        # Добавляем текст на кнопке
        button_text = "ТЕХНИЧЕСКИЙ АНАЛИЗ"
        button_draw.text((30, button_height//2 - 4), button_text, fill=(255, 255, 255), font=ImageFont.load_default())
        
        # Добавляем кнопку на терминал
        terminal.paste(button, (button_x, button_y), button)
        
        # Добавляем индикаторы статуса вверху терминала
        for i in range(5):
            led_color = random.choice([(0, 255, 0, 200), (255, 255, 0, 200)])
            terminal_draw.ellipse([(terminal_width - 30 - i*20, 25), (terminal_width - 20 - i*20, 35)], fill=led_color)
        
        # Накладываем терминал на основное изображение
        image.paste(terminal, (terminal_x, terminal_y), terminal)
        
        # Используем системные шрифты DejaVu для текста
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            feature_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            contact_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except:
            logger.warning("Не удалось загрузить шрифты, используем стандартные.")
            # Используем стандартный шрифт
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            feature_font = ImageFont.load_default()
            contact_font = ImageFont.load_default()
        
        # Добавляем основной заголовок с эффектом свечения
        title_text = "Торговый Аналитический Бот"
        try:
            title_bbox = title_font.getbbox(title_text)
            title_width = title_bbox[2] - title_bbox[0]
        except:
            title_width = len(title_text) * 20
        
        title_x = (width - title_width) // 2
        title_y = 40
        
        # Эффект тени для заголовка
        for offset in range(1, 4):
            draw.text((title_x, title_y + offset), title_text, font=title_font, fill=(0, 0, 50, 50))
        
        # Основной текст заголовка
        draw.text((title_x, title_y), title_text, font=title_font, fill=(255, 255, 255))
        
        # Добавляем линию под заголовком
        draw.line([(width//4, title_y + 60), (width - width//4, title_y + 60)], fill=(100, 150, 255, 150), width=2)
        
        # Добавляем ключевые функции внизу с иконками
        features = [
            ("✓", "Автоматический анализ активов"),
            ("📊", "Торговые сигналы в реальном времени"),
            ("🔔", "Мгновенные оповещения"),
            ("📱", "Доступ с любого устройства")
        ]
        
        y_pos = height - 130
        x_start = 100
        for i, (icon, text) in enumerate(features):
            # Создаем фон для функции
            feature_width = 250
            feature_bg = Image.new('RGBA', (feature_width, 50), (30, 45, 90, 100))
            feature_draw = ImageDraw.Draw(feature_bg)
            
            # Добавляем контур
            feature_draw.rectangle([(0, 0), (feature_width, 50)], outline=(100, 150, 255, 100), width=1)
            
            # Добавляем текст с иконкой
            feature_draw.text((15, 15), icon, fill=(255, 255, 255), font=feature_font)
            feature_draw.text((50, 15), text, fill=(200, 220, 255), font=ImageFont.load_default())
            
            # Позиционируем функции в ряд
            x_position = x_start + i * (feature_width + 30)
            if x_position + feature_width > width - 50:
                # Переносим на следующую строку
                y_pos += 60
                x_position = x_start
            
            # Накладываем на основное изображение
            image.paste(feature_bg, (x_position, y_pos), feature_bg)
        
        # Добавляем нижнюю информационную строку
        support_text = "Служба поддержки: @tradeporu"
        try:
            support_bbox = contact_font.getbbox(support_text)
            support_width = support_bbox[2] - support_bbox[0]
        except:
            support_width = len(support_text) * 12
        
        support_x = (width - support_width) // 2
        support_y = height - 50
        
        # Добавляем фон для контактной информации
        support_bg = Image.new('RGBA', (support_width + 60, 36), (0, 0, 0, 0))
        support_draw = ImageDraw.Draw(support_bg)
        support_draw.rounded_rectangle([(0, 0), (support_width + 60, 36)], radius=10, fill=(40, 60, 120, 180))
        
        # Накладываем на изображение
        image.paste(support_bg, (support_x - 30, support_y - 5), support_bg)
        
        # Добавляем текст поддержки
        draw.text((support_x, support_y), support_text, fill=(255, 215, 0), font=contact_font)
        
        # Сохраняем изображение
        image.save('welcome_image.png')
        logger.info("Изображение успешно создано: welcome_image.png")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании изображения: {e}")
        return False

if __name__ == "__main__":
    create_welcome_image()