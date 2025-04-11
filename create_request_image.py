from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import os
import logging
import io
import math
import random
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_request_image(username=None):
    """
    Создает элегантное изображение для формы запроса на доступ
    с минимализмом и современными элементами дизайна
    """
    try:
        # Создаем изображение с более высоким разрешением для лучшего качества
        width, height = 900, 600
        image = Image.new('RGB', (width, height), color=(20, 24, 35))
        draw = ImageDraw.Draw(image)
        
        # Создаем стильный градиентный фон
        for i in range(height):
            # Создаем элегантный градиент: темный внизу, более светлый вверху
            progress = i / height
            color = (
                int(20 + (1 - progress) * 8),    # Темно-синий
                int(24 + (1 - progress) * 10),   # С легким фиолетовым оттенком
                int(35 + (1 - progress) * 15)    # К черному
            )
            draw.line([(0, i), (width, i)], fill=color)
        
        # Добавляем стильную сетку на фоне (очень тонкие линии)
        grid_spacing = 50
        grid_color = (255, 255, 255, 15)  # Очень прозрачный белый
        
        for x in range(0, width, grid_spacing):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        
        for y in range(0, height, grid_spacing):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)
        
        # Добавляем декоративные элементы на фоне
        
        # 1. Стильные круги на фоне
        for _ in range(6):
            circle_x = random.randint(50, width-50)
            circle_y = random.randint(50, height-50)
            circle_size = random.randint(80, 200)
            circle_color = (random.randint(30, 60), 
                           random.randint(40, 70), 
                           random.randint(70, 120), 
                           random.randint(10, 25))  # Полупрозрачный оттенок фона
            
            draw.ellipse(
                [(circle_x - circle_size//2, circle_y - circle_size//2), 
                 (circle_x + circle_size//2, circle_y + circle_size//2)],
                fill=circle_color,
                outline=None
            )
        
        # 2. Элегантные линии финансового графика (минималистичные)
        chart_height = 80
        chart_y = 80
        chart_start_x = 50
        chart_end_x = width - 50
        chart_width = chart_end_x - chart_start_x
        
        # Создаем гладкую линию для графика (не ломаную)
        points = []
        num_points = 20
        for i in range(num_points):
            x = chart_start_x + (chart_width / (num_points - 1)) * i
            # Создаем реалистичную волну для финансового графика
            progress = i / (num_points - 1)
            wave1 = math.sin(progress * math.pi * 1.5) * 25
            wave2 = math.sin(progress * math.pi * 3) * 10
            trend = -progress * 15 + 20  # Общий восходящий тренд
            
            y = chart_y + chart_height/2 + wave1 + wave2 + trend
            points.append((x, y))
        
        # Рисуем линию графика с плавным градиентом
        for i in range(len(points) - 1):
            start_point = points[i]
            end_point = points[i+1]
            
            # Определяем цвет линии с градиентом (зеленый для растущего тренда)
            progress = i / (len(points) - 2)
            line_color = (
                int(30 + progress * 20),
                int(150 + progress * 55),
                int(100 + progress * 20),
                200
            )
            
            draw.line([start_point, end_point], fill=line_color, width=2)
        
        # Добавляем несколько горизонтальных пунктирных линий (уровни)
        for level in [chart_y + 20, chart_y + chart_height - 20]:
            for x in range(chart_start_x, chart_end_x, 10):
                draw.line([(x, level), (x+5, level)], fill=(255, 255, 255, 30), width=1)
        
        # Основная карточка для формы запроса (современный дизайн)
        card_width = 550
        card_height = 380
        card_x = (width - card_width) // 2
        card_y = (height - card_height) // 2 + 20
        
        # Рисуем карточку с закругленными углами
        # Сначала создаем маску для закругленных углов
        corner_radius = 15
        rectangle_image = Image.new('RGBA', (card_width, card_height), (0, 0, 0, 0))
        rectangle_draw = ImageDraw.Draw(rectangle_image)
        
        # Рисуем прямоугольник с закругленными углами
        rectangle_draw.rounded_rectangle(
            [(0, 0), (card_width, card_height)],
            radius=corner_radius,
            fill=(30, 37, 60, 230)
        )
        
        # Накладываем скругленный прямоугольник на основное изображение
        image.paste(rectangle_image, (card_x, card_y), rectangle_image)
        
        # Добавляем блик на верхней части карточки (стеклянный эффект)
        for i in range(card_width):
            progress = i / card_width
            alpha = int(math.sin(progress * math.pi) * 50)
            highlight_color = (255, 255, 255, alpha)
            
            x = card_x + i
            draw.point((x, card_y + 2), fill=highlight_color)
            draw.point((x, card_y + 3), fill=highlight_color)
        
        # Добавляем разделительную линию после заголовка
        divider_y = card_y + 70
        draw.line(
            [(card_x + 25, divider_y), (card_x + card_width - 25, divider_y)],
            fill=(100, 120, 200, 150),
            width=1
        )
        
        # Используем DejaVu шрифты, которые есть в системе
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            text_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            button_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            username_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        except:
            logger.warning("Не удалось загрузить шрифты DejaVu, используем стандартные.")
            # Используем стандартный шрифт
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            button_font = ImageFont.load_default()
            username_font = ImageFont.load_default()
        
        # Добавляем заголовок
        title_text = "Запрос на доступ"
        try:
            title_bbox = title_font.getbbox(title_text)
            title_width = title_bbox[2] - title_bbox[0]
        except:
            title_width = len(title_text) * 14  # примерная оценка ширины
        
        title_x = card_x + (card_width - title_width) // 2
        draw.text((title_x, card_y + 25), title_text, fill=(255, 255, 255), font=title_font)
        
        # Добавляем имя пользователя, если предоставлено
        if username:
            username_text = f"@{username}"
            try:
                username_bbox = username_font.getbbox(username_text)
                username_width = username_bbox[2] - username_bbox[0]
            except:
                username_width = len(username_text) * 12
            
            username_x = card_x + (card_width - username_width) // 2
            
            # Рисуем элегантный фон для имени пользователя
            username_bg_height = 40
            username_bg_width = username_width + 60
            username_bg_x = card_x + (card_width - username_bg_width) // 2
            username_bg_y = card_y + 90
            
            # Эффект свечения для имени пользователя
            draw.rectangle(
                [(username_bg_x, username_bg_y), 
                 (username_bg_x + username_bg_width, username_bg_y + username_bg_height)],
                fill=(60, 70, 120, 100),
                outline=(100, 120, 200, 150),
                width=1
            )
            
            # Текст имени пользователя
            draw.text(
                (username_x, username_bg_y + (username_bg_height - 22) // 2),
                username_text,
                fill=(220, 220, 255),
                font=username_font
            )
        
        # Добавляем описание процесса с иконками
        description_items = [
            ("✓", "Отправьте заявку на рассмотрение"),
            ("⏱", "Дождитесь проверки администратором"),
            ("🔑", "Получите доступ к аналитическим данным"),
            ("📊", "Используйте профессиональные инструменты")
        ]
        
        y_pos = card_y + 150
        for icon, text in description_items:
            # Рисуем иконку
            draw.text((card_x + 40, y_pos), icon, fill=(255, 255, 255), font=subtitle_font)
            
            # Рисуем текст описания
            draw.text((card_x + 80, y_pos + 3), text, fill=(200, 210, 255), font=text_font)
            
            y_pos += 45
        
        # Рисуем кнопку запроса доступа
        button_width = 300
        button_height = 50
        button_x = card_x + (card_width - button_width) // 2
        button_y = card_y + card_height - 80
        
        # Создаем закругленные углы для кнопки
        button_image = Image.new('RGBA', (button_width, button_height), (0, 0, 0, 0))
        button_draw = ImageDraw.Draw(button_image)
        
        # Градиент для кнопки (синий к голубому)
        for i in range(button_height):
            progress = i / button_height
            color = (
                int(40 + progress * 40),
                int(80 + progress * 60),
                int(180 + progress * 40),
                230
            )
            button_draw.line(
                [(0, i), (button_width, i)],
                fill=color
            )
        
        # Рисуем кнопку с закругленными углами
        button_draw.rounded_rectangle(
            [(0, 0), (button_width, button_height)],
            radius=10,
            fill=None,
            outline=(150, 200, 255, 180),
            width=1
        )
        
        # Накладываем кнопку на основное изображение
        image.paste(button_image, (button_x, button_y), button_image)
        
        # Добавляем текст кнопки
        button_text = "Отправить запрос"
        try:
            button_text_bbox = button_font.getbbox(button_text)
            button_text_width = button_text_bbox[2] - button_text_bbox[0]
        except:
            button_text_width = len(button_text) * 10
        
        button_text_x = button_x + (button_width - button_text_width) // 2
        button_text_y = button_y + (button_height - 22) // 2
        
        # Добавляем легкое свечение для текста кнопки
        for offset in range(1, 3):
            draw.text(
                (button_text_x, button_text_y + offset),
                button_text,
                fill=(200, 220, 255, 100),
                font=button_font
            )
        
        # Основной текст кнопки
        draw.text(
            (button_text_x, button_text_y),
            button_text,
            fill=(255, 255, 255),
            font=button_font
        )
        
        # Добавляем информацию о службе поддержки внизу
        support_text = "Служба поддержки: @tradeporu"
        try:
            support_text_bbox = text_font.getbbox(support_text)
            support_text_width = support_text_bbox[2] - support_text_bbox[0]
        except:
            support_text_width = len(support_text) * 8
        
        support_text_x = (width - support_text_width) // 2
        support_text_y = height - 50
        
        # Рисуем фон для контактной информации
        support_bg_width = support_text_width + 40
        support_bg_height = 30
        support_bg_x = (width - support_bg_width) // 2
        support_bg_y = support_text_y - 5
        
        support_bg = Image.new('RGBA', (support_bg_width, support_bg_height), (0, 0, 0, 0))
        support_bg_draw = ImageDraw.Draw(support_bg)
        support_bg_draw.rounded_rectangle(
            [(0, 0), (support_bg_width, support_bg_height)],
            radius=8,
            fill=(40, 45, 80, 150)
        )
        
        image.paste(support_bg, (support_bg_x, support_bg_y), support_bg)
        
        # Рисуем текст поддержки
        draw.text(
            (support_text_x, support_text_y),
            support_text,
            fill=(255, 215, 0),
            font=text_font
        )
        
        # Добавляем декоративные элементы
        # 1. Линии соединяющие поддержку и карточку
        draw.line(
            [(card_x + card_width//4, card_y + card_height), 
             (support_bg_x + support_bg_width//4, support_bg_y)],
            fill=(60, 90, 150, 80),
            width=1
        )
        
        draw.line(
            [(card_x + 3*card_width//4, card_y + card_height), 
             (support_bg_x + 3*support_bg_width//4, support_bg_y)],
            fill=(60, 90, 150, 80),
            width=1
        )
        
        # 2. Стилизованный символ трейдинга
        trade_icon_x = card_x - 80
        trade_icon_y = card_y + 100
        
        # Стилизованная свеча
        draw.rectangle(
            [(trade_icon_x - 5, trade_icon_y), (trade_icon_x + 5, trade_icon_y + 40)],
            fill=(0, 200, 100),
            outline=(255, 255, 255, 100),
            width=1
        )
        
        # Фитиль свечи
        draw.line(
            [(trade_icon_x, trade_icon_y - 10), (trade_icon_x, trade_icon_y)],
            fill=(255, 255, 255),
            width=1
        )
        
        draw.line(
            [(trade_icon_x, trade_icon_y + 40), (trade_icon_x, trade_icon_y + 50)],
            fill=(255, 255, 255),
            width=1
        )
        
        # Сохраняем изображение
        image.save('request_image.png')
        logger.info("Изображение успешно создано: request_image.png")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании изображения: {e}")
        return False

if __name__ == "__main__":
    create_request_image("example_user")