from PIL import Image, ImageDraw, ImageFont
import os
import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import io
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_welcome_image():
    try:
        # Создаем изображение
        width, height = 1000, 600
        image = Image.new('RGB', (width, height), color=(14, 22, 33))
        draw = ImageDraw.Draw(image)
        
        # Создаем градиент от темно-синего к темно-фиолетовому (более профессиональный вид)
        for i in range(height):
            # Градиент для трейдинг-фона
            color = (
                int(14 + (i / height) * 15),  # Темно-синий к синему
                int(22 + (i / height) * 10),  
                int(33 + (i / height) * 40)   # Более насыщенный фиолетовый оттенок
            )
            draw.line([(0, i), (width, i)], fill=color)
        
        # Добавляем графический элемент - график свечей (имитация)
        # Создаем график с matplotlib
        fig = Figure(figsize=(4, 3), dpi=100)
        fig.patch.set_alpha(0.0)  # Прозрачный фон
        ax = fig.add_subplot(111)
        
        # Имитируем график трейдинга - свечной график
        n_candles = 30
        dates = np.arange(n_candles)
        opens = np.random.uniform(100, 110, n_candles)
        closes = np.random.uniform(99, 111, n_candles)
        highs = np.maximum(opens, closes) + np.random.uniform(0, 1, n_candles)
        lows = np.minimum(opens, closes) - np.random.uniform(0, 1, n_candles)
        
        # Создаем тренд для более реалистичности
        trend = np.cumsum(np.random.normal(0.05, 0.1, n_candles))
        opens += trend
        closes += trend
        highs += trend
        lows += trend
        
        # Рисуем свечи
        width_candle = 0.8
        up_color = '#00ff00'     # Зеленый для растущих свечей
        down_color = '#ff0000'   # Красный для падающих свечей
        
        for i in range(n_candles):
            if closes[i] > opens[i]:
                color = up_color
            else:
                color = down_color
            
            # Рисуем тело свечи
            ax.bar(dates[i], closes[i] - opens[i], width_candle, bottom=min(opens[i], closes[i]), color=color, alpha=0.8)
            
            # Рисуем тени (фитили)
            ax.plot([dates[i], dates[i]], [lows[i], highs[i]], color='white', linewidth=1)
        
        # Добавим немного пометок уровней сопротивления
        ax.axhline(y=max(highs) - 0.5, color='#ffff00', linestyle='--', alpha=0.5, linewidth=1)
        ax.axhline(y=min(lows) + 0.5, color='#ffff00', linestyle='--', alpha=0.5, linewidth=1)
        
        # Настройка осей
        ax.set_facecolor('#1a2035')  # Темный фон для графика
        ax.grid(color='gray', linestyle='--', linewidth=0.5, alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#ffffff')
        ax.spines['left'].set_color('#ffffff')
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        ax.set_xticks([])  # Убираем метки по оси X
        ax.set_yticks([])  # Убираем метки по оси Y
        
        # Преобразование графика в изображение
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        buf = io.BytesIO()
        canvas.print_png(buf)
        buf.seek(0)
        chart_img = Image.open(buf)
        
        # Размещаем график на основном изображении
        image.paste(chart_img, (600, 170))
        
        # Добавляем контур для создания эффекта карточки
        card_padding = 40
        draw.rectangle(
            ((card_padding, card_padding), (width - card_padding, height - card_padding)),
            outline=(255, 255, 255, 100),
            width=2
        )
        
        # Добавляем элементы робота (стилизованно)
        # Голова робота
        robot_head_size = 80
        robot_x = 150
        robot_y = 350
        
        # Голова и тело
        draw.rectangle(((robot_x, robot_y), (robot_x + robot_head_size, robot_y + robot_head_size)), 
                       fill=(120, 145, 190), outline=(180, 200, 255), width=2)
        
        # Антенны
        draw.line([(robot_x + 20, robot_y), (robot_x + 10, robot_y - 20)], fill=(180, 200, 255), width=3)
        draw.line([(robot_x + 60, robot_y), (robot_x + 70, robot_y - 20)], fill=(180, 200, 255), width=3)
        
        # Глаза
        draw.ellipse(((robot_x + 20, robot_y + 20), (robot_x + 30, robot_y + 30)), fill=(0, 255, 255))
        draw.ellipse(((robot_x + 50, robot_y + 20), (robot_x + 60, robot_y + 30)), fill=(0, 255, 255))
        
        # Рот (монитор с графиком)
        draw.rectangle(((robot_x + 15, robot_y + 45), (robot_x + 65, robot_y + 65)), 
                       fill=(20, 30, 50), outline=(180, 200, 255), width=1)
        
        # Мини-график на мониторе
        line_points = []
        for i in range(6):
            line_points.append((robot_x + 15 + i*10, robot_y + 55 - random.randint(0, 10)))
        
        for i in range(len(line_points)-1):
            draw.line([line_points[i], line_points[i+1]], fill=(0, 255, 0), width=2)
        
        # Попытка загрузить шрифт (если не получается, используем стандартный)
        try:
            # Для заголовка
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
            # Для подзаголовка
            subtitle_font = ImageFont.truetype("DejaVuSans.ttf", 32)
            # Для текста
            text_font = ImageFont.truetype("DejaVuSans.ttf", 24)
            # Для контактной информации
            contact_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
        except:
            logger.warning("Не удалось загрузить шрифты, используем стандартные.")
            # Используем стандартный шрифт
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            contact_font = ImageFont.load_default()
        
        # Добавляем текст заголовка
        title_text = "Trade Analysis Bot"
        # Получаем размеры текста
        try:
            title_bbox = title_font.getbbox(title_text)
            title_width = title_bbox[2] - title_bbox[0]
        except:
            # Альтернативный способ для старых версий PIL
            title_width = title_font.getlength(title_text) if hasattr(title_font, "getlength") else width - 2 * card_padding
        
        title_x = (width - title_width) // 2
        draw.text((title_x, 80), title_text, fill=(255, 255, 255), font=title_font)
        
        # Добавляем подзаголовок
        subtitle_text = "Профессиональный анализ рынка"
        try:
            subtitle_bbox = subtitle_font.getbbox(subtitle_text)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        except:
            subtitle_width = subtitle_font.getlength(subtitle_text) if hasattr(subtitle_font, "getlength") else width - 2 * card_padding
        
        subtitle_x = (width - subtitle_width) // 2
        draw.text((subtitle_x, 150), subtitle_text, fill=(200, 220, 255), font=subtitle_font)
        
        # Добавляем текст описания
        description_text = "• Автоматический анализ рынка\n• Точные торговые сигналы\n• Мониторинг в реальном времени\n\nДля получения доступа необходимо\nотправить запрос администратору."
        
        # Используем многоцветный текст для описания
        lines = description_text.split('\n')
        y_position = 180
        for i, line in enumerate(lines):
            # Выделяем маркеры и заголовки другим цветом
            if line.startswith('•'):
                draw.text((300, y_position), line, fill=(100, 255, 100), font=text_font)
            elif i >= 4:  # Инструкция доступа
                draw.text((300, y_position), line, fill=(255, 220, 100), font=text_font)
            else:
                draw.text((300, y_position), line, fill=(220, 220, 220), font=text_font)
            y_position += 30
        
        # Добавляем контактную информацию
        contact_text = "Служба поддержки: @tradeporu"
        draw.text((width//2 - 200, 520), contact_text, fill=(255, 215, 0), font=contact_font)
        
        # Сохраняем изображение
        image.save('welcome_image.png')
        logger.info("Изображение успешно создано: welcome_image.png")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании изображения: {e}")
        return False

if __name__ == "__main__":
    create_welcome_image()