import logging
import hashlib
import time
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from config import *
from market_analyzer import MarketAnalyzer
from utils import get_currency_keyboard, get_language_keyboard, format_signal_message
try:
    from generate_sample import create_analysis_image
except ImportError:
    logging.error("Could not import generate_sample module. Chart generation will be disabled.")
    def create_analysis_image(*args, **kwargs):
        logging.warning("Chart generation is disabled due to missing module")
        return False
from datetime import datetime
from models import (
    add_user, get_user, approve_user, verify_user_password, update_user_language,
    get_all_users, get_pending_users, delete_user, set_user_admin_status,
    create_admin_user, get_approved_user_ids, ADMIN_USERNAME, ADMIN_PASSWORD_HASH
)
from keep_alive import keep_alive

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler('bot.log')]
)

# Словарь для хранения пользователей, ожидающих подтверждения
PENDING_USERS = {}
logger = logging.getLogger(__name__)

# Состояния для админа
ADMIN_PASSWORD, ADMIN_MENU, ADMIN_USER_MANAGEMENT, ADMIN_BROADCAST_MESSAGE = range(4)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        user_id = user.id
        username = user.username

        # Add user to database
        add_user(user_id, username)
        user_data = get_user(user_id)

        # Set default language
        lang_code = user_data['language_code'] if user_data else 'tg'
        
        # Проверяем подтверждение пользователя
        if user_data and user_data.get('is_approved'):
            # Если пользователь подтвержден, показываем основной интерфейс
            keyboard = get_currency_keyboard(current_lang=lang_code)
            await update.message.reply_text(
                MESSAGES[lang_code]['WELCOME'],
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
        elif username and username.lower() == ADMIN_USERNAME.lower():
            # Если это администратор, создаем учетную запись администратора и показываем интерфейс
            create_admin_user(user_id, username)
            keyboard = get_currency_keyboard(current_lang=lang_code)
            admin_welcome = f"👑 Вы вошли как администратор @{username}.\n\n"
            await update.message.reply_text(
                admin_welcome,
                reply_markup=keyboard
            )
            # Отправляем сообщение с приветствием отдельно, чтобы избежать проблем с escape-символами
            await update.message.reply_text(
                MESSAGES[lang_code]['WELCOME'],
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
        else:
            # Если пользователь не подтвержден, предлагаем зарегистрироваться
            register_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📝 Отправить заявку", callback_data="send_request")
            ]])
            
            await update.message.reply_text(
                f"👋 Добро пожаловать, @{username}!\n\n"
                "Для использования бота необходимо отправить заявку на регистрацию.\n"
                "Администратор рассмотрит вашу заявку и предоставит доступ к боту.\n\n"
                "Вы можете отправить заявку прямо сейчас или воспользоваться командой /register позже.",
                reply_markup=register_keyboard
            )

    except Exception as e:
        logger.error(f"Start error: {str(e)}")
        await update.message.reply_text(MESSAGES['tg']['ERRORS']['GENERAL_ERROR'])

async def get_admin_chat_id(bot):
    """Get admin's chat ID by username"""
    try:
        # Для тестирования можно использовать ID текущего пользователя вместо поиска по имени
        admin_chat = await bot.get_chat(f"@{ADMIN_USERNAME}")
        return admin_chat.id
    except Exception as e:
        logger.error(f"Error getting admin chat ID: {str(e)}")
        # В случае ошибки возвращаем None и обрабатываем это в вызывающем коде
        return None

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Ignore header buttons
    if query.data.startswith('header_'):
        await query.answer()
        return

    admin_username = update.effective_user.username

    if not admin_username or admin_username.lower() != ADMIN_USERNAME.lower():
        await query.answer("❌ У вас нет прав администратора")
        return

    action, user_id = query.data.split('_')
    user_id = int(user_id)

    if user_id not in PENDING_USERS:
        await query.answer("❌ Заявка не найдена или уже обработана")
        return

    user_info = PENDING_USERS[user_id]

    if action == "approve":
        password = ''.join([str(hash(datetime.now()))[i:i+2] for i in range(0, 8, 2)])
        password_hash = hash_password(password)

        if approve_user(user_id, password_hash):
            del PENDING_USERS[user_id]
            
            # Получаем информацию о языке пользователя
            user_data = get_user(user_id)
            lang_code = user_data['language_code'] if user_data and 'language_code' in user_data else 'tg'
            
            # Сообщения об одобрении на разных языках
            approval_messages = {
                'tg': f"✅ Дархости шумо қабул карда шуд!\n\nРамзи шумо барои ворид шудан: `{password}`\n\nЛутфан, онро нигоҳ доред.",
                'ru': f"✅ Ваша заявка одобрена!\n\nВаш пароль для входа: `{password}`\n\nПожалуйста, сохраните его.",
                'uz': f"✅ Arizangiz tasdiqlandi!\n\nKirish uchun parolingiz: `{password}`\n\nIltimos, uni saqlab qoling.",
                'kk': f"✅ Өтінішіңіз мақұлданды!\n\nКіру үшін құпия сөзіңіз: `{password}`\n\nОны сақтап қойыңыз.",
                'en': f"✅ Your request has been approved!\n\nYour password: `{password}`\n\nPlease save it."
            }
            
            # Тексты кнопок на разных языках
            button_texts = {
                'tg': "🚀 Ба бот ворид шавед",
                'ru': "🚀 Войти в бот",
                'uz': "🚀 Botga kirish",
                'kk': "🚀 Ботқа кіру",
                'en': "🚀 Enter the bot"
            }
            
            # Выбираем сообщение и текст кнопки согласно языку пользователя
            message = approval_messages.get(lang_code, approval_messages['tg'])
            button_text = button_texts.get(lang_code, button_texts['tg'])
            
            # Создаем клавиатуру с кнопкой для входа
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(button_text, callback_data="return_to_main")]
            ])
            
            # Отправляем сообщение пользователю
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='MarkdownV2',
                reply_markup=keyboard
            )
            
            # Уведомляем администратора
            await query.edit_message_text(f"✅ Пользователь @{user_info['username']} одобрен")
        else:
            await query.edit_message_text("❌ Ошибка при одобрении пользователя")
    else:
        del PENDING_USERS[user_id]
        
        # Получаем информацию о языке пользователя
        user_data = get_user(user_id)
        lang_code = user_data['language_code'] if user_data and 'language_code' in user_data else 'tg'
        
        # Сообщения об отклонении на разных языках
        rejection_messages = {
            'tg': "❌ Дархости шумо радд карда шуд.",
            'ru': "❌ Ваша заявка отклонена администратором.",
            'uz': "❌ Arizangiz administrator tomonidan rad etildi.",
            'kk': "❌ Сіздің өтінішіңіз әкімші тарапынан қабылданбады.",
            'en': "❌ Your request has been rejected by the administrator."
        }
        
        # Выбираем сообщение согласно языку пользователя
        message = rejection_messages.get(lang_code, rejection_messages['tg'])
        
        # Отправляем сообщение пользователю
        await context.bot.send_message(
            chat_id=user_id,
            text=message
        )
        
        # Уведомляем администратора
        await query.edit_message_text(f"❌ Пользователь @{user_info['username']} отклонен")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    user_data = get_user(user.id)

    if not user_data:
        add_user(user.id, user.username)
        user_data = get_user(user.id)

    lang_code = user_data['language_code'] if user_data else 'tg'
    keyboard = get_currency_keyboard(current_lang=lang_code)
    await update.message.reply_text(
        MESSAGES[lang_code]['WELCOME'],
        reply_markup=keyboard,
        parse_mode='MarkdownV2'
    )

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        lang_code = query.data.split('_')[1]
        user_id = update.effective_user.id
        logger.info(f"Language change request from user {user_id} to {lang_code}")

        # Update user's language in database
        if update_user_language(user_id, lang_code):
            # Get fresh keyboard with new language
            keyboard = get_currency_keyboard(current_lang=lang_code)
            welcome_message = MESSAGES[lang_code]['WELCOME']

            try:
                # Delete previous message if exists
                try:
                    await query.message.delete()
                except Exception:
                    pass  # Ignore if message can't be deleted

                # Send new welcome message
                await update.effective_chat.send_message(
                    text=welcome_message,
                    reply_markup=keyboard,
                    parse_mode='MarkdownV2'
                )

                # Send confirmation in the selected language
                lang_confirmations = {
                    'tg': '✅ Забон иваз карда шуд',
                    'ru': '✅ Язык изменен',
                    'uz': '✅ Til oʻzgartirildi',
                    'kk': '✅ Тіл өзгертілді',
                    'en': '✅ Language changed'
                }
                await query.answer(lang_confirmations.get(lang_code, '✅ OK'))
                logger.info(f"Language successfully changed to {lang_code} for user {user_id}")

            except Exception as e:
                logger.error(f"Error sending message after language change: {e}")
                await query.answer("❌ Error sending message")
        else:
            logger.error(f"Failed to update language to {lang_code} for user {user_id}")
            await query.answer("❌ Error updating language")

    except Exception as e:
        logger.error(f"Language selection error: {str(e)}")
        await query.answer("❌ Error processing language change")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        # Проверка доступа на уровне всех действий
        user_id = update.effective_user.id
        user_data = get_user(user_id)
        is_admin = update.effective_user.username and update.effective_user.username.lower() == ADMIN_USERNAME.lower()
        is_approved = user_data and user_data.get('is_approved')
        
        # Разрешаем некоторые действия даже для неавторизованных пользователей
        allowed_for_all = [
            "send_request",
            "return_to_main",
            "change_language",
        ]
        is_allowed_action = query.data in allowed_for_all or query.data.startswith('lang_')
        
        # Проверка доступа
        if not (is_approved or is_admin or is_allowed_action):
            register_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📝 Отправить заявку", callback_data="send_request")
            ]])
            
            await query.edit_message_text(
                "⚠️ У вас нет доступа к этой функции.\n\n"
                "Для получения доступа к боту необходимо отправить заявку на регистрацию.",
                reply_markup=register_keyboard
            )
            return
            
        # Handle "Return to Main" button
        if query.data == "return_to_main":
            lang_code = user_data['language_code'] if user_data else 'tg'

            keyboard = get_currency_keyboard(current_lang=lang_code)
            try:
                await query.message.delete()
            except Exception:
                pass  # Ignore if message can't be deleted

            await update.effective_chat.send_message(
                text=MESSAGES[lang_code]['WELCOME'],
                reply_markup=keyboard,
                parse_mode='MarkdownV2'
            )
            return
            
        # Обработка кнопки отправки запроса
        if query.data == "send_request":
            user = update.effective_user
            user_id = user.id
            username = user.username
            
            # Проверяем, существует ли уже пользователь и его статус
            user_data = get_user(user_id)
            
            if user_data and user_data.get('is_approved'):
                await query.edit_message_text(
                    "✅ Вы уже зарегистрированы и подтверждены."
                )
                return
            
            # Добавляем пользователя в базу, если его еще нет
            if not user_data:
                add_user(user_id, username)
            
            # Добавляем пользователя в список ожидающих и отправляем запрос админу
            PENDING_USERS[user_id] = {
                'user_id': user_id,
                'username': username,
                'timestamp': datetime.now()
            }
            
            # Получаем язык пользователя
            user_data = get_user(user_id)
            lang_code = user_data['language_code'] if user_data and 'language_code' in user_data else 'tg'
            
            # Сообщения о заявке на разных языках
            request_messages = {
                'tg': "📝 Дархости шумо ба маъмур фиристода шуд. "
                      "Лутфан, тасдиқро интизор шавед. "
                      "Вақте ки дархости шумо баррасӣ мешавад, шумо огоҳинома мегиред.",
                'ru': "📝 Ваша заявка отправлена администратору. "
                      "Пожалуйста, ожидайте подтверждения. "
                      "Вы получите уведомление, когда ваша заявка будет рассмотрена.",
                'uz': "📝 Arizangiz administratorga yuborildi. "
                      "Iltimos, tasdiqlashni kuting. "
                      "Arizangiz ko'rib chiqilganda, sizga xabar beriladi.",
                'kk': "📝 Сіздің өтінішіңіз әкімшіге жіберілді. "
                      "Растауды күтіңіз. "
                      "Өтінішіңіз қаралғанда, сізге хабарлама жіберіледі.",
                'en': "📝 Your request has been sent to the administrator. "
                      "Please wait for confirmation. "
                      "You will receive a notification when your request is reviewed."
            }
            
            # Отправляем сообщение пользователю на его языке
            message = request_messages.get(lang_code, request_messages['tg'])
            await query.edit_message_text(message)
            
            # Получаем чат администратора и отправляем ему уведомление
            admin_chat_id = await get_admin_chat_id(context.bot)
            if admin_chat_id:
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
                        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
                    ]
                ]
                await context.bot.send_message(
                    chat_id=admin_chat_id,
                    text=f"📝 Новая заявка на регистрацию!\n\n"
                        f"👤 Пользователь: @{username}\n"
                        f"🆔 ID: {user_id}\n"
                        f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # Если не удалось найти админа, сохраняем запрос в базе данных,
                # чтобы администратор мог просмотреть его через панель управления
                logger.warning(f"Admin chat not found. Registration request from user @{username} (ID: {user_id}) stored in pending list.")
            return

        # Ignore clicks on header buttons
        if query.data.startswith('header_'):
            await query.answer()
            return

        # Получаем данные пользователя, если нужно
        if not user_data:
            add_user(user_id, update.effective_user.username)
            user_data = get_user(user_id)
        
        lang_code = user_data['language_code'] if user_data else 'tg'
        logger.info(f"Current language for user {user_id}: {lang_code}")

        if query.data.startswith('lang_'):
            await handle_language_selection(update, context)
            return

        if query.data == "change_language":
            keyboard = get_language_keyboard()
            msg = "Выберите язык / Забонро интихоб кунед / Tilni tanlang / Тілді таңдаңыз / Choose language:"
            try:
                if query.message.photo:
                    await query.message.reply_text(msg, reply_markup=keyboard)
                else:
                    await query.message.edit_text(msg, reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Error showing language selection: {e}")
            return

        # Обрабатываем запросы на анализ рынка только для авторизованных пользователей
        if not (is_approved or is_admin):
            register_keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("📝 Отправить заявку", callback_data="send_request")
            ]])
            
            await query.edit_message_text(
                "⚠️ У вас нет доступа к анализу рынка.\n\n"
                "Для получения доступа к боту необходимо отправить заявку на регистрацию.",
                reply_markup=register_keyboard
            )
            return

        pair = query.data
        symbol = CURRENCY_PAIRS.get(pair)
        if not symbol:
            await query.message.reply_text(MESSAGES[lang_code]['ERRORS']['GENERAL_ERROR'])
            return

        analyzing_message = await query.message.reply_text(
            MESSAGES[lang_code]['ANALYZING'],
            parse_mode='MarkdownV2'
        )

        try:
            analyzer = MarketAnalyzer(symbol)
            analyzer.set_language(lang_code)
            analysis_result = analyzer.analyze_market()

            if not analysis_result or 'error' in analysis_result:
                error_msg = analysis_result.get('error', MESSAGES[lang_code]['ERRORS']['ANALYSIS_ERROR'])
                await analyzing_message.edit_text(error_msg, parse_mode='MarkdownV2')
                return

            market_data, error_message = analyzer.get_market_data(minutes=30)
            if error_message or market_data is None or market_data.empty:
                await analyzing_message.edit_text(MESSAGES[lang_code]['ERRORS']['NO_DATA'])
                return

            result_message = format_signal_message(pair, analysis_result, lang_code)

            try:
                create_analysis_image(analysis_result, market_data, lang_code)
                with open('analysis_sample.png', 'rb') as photo:
                    await query.message.reply_photo(
                        photo=photo,
                        caption=result_message,
                        parse_mode='MarkdownV2',
                        reply_markup=get_currency_keyboard(current_lang=lang_code)
                    )
                await analyzing_message.delete()
            except Exception as img_error:
                logger.error(f"Chart error: {str(img_error)}")
                await analyzing_message.edit_text(
                    text=result_message,
                    parse_mode='MarkdownV2',
                    reply_markup=get_currency_keyboard(current_lang=lang_code)
                )

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            await analyzing_message.edit_text(MESSAGES[lang_code]['ERRORS']['ANALYSIS_ERROR'])

    except Exception as e:
        logger.error(f"Button click error: {str(e)}")
        lang_code = 'tg'  # Используем язык по умолчанию в случае ошибки
        await query.message.reply_text(MESSAGES[lang_code]['ERRORS']['GENERAL_ERROR'])

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the website.zip file to the user"""
    try:
        with open('website.zip', 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename='website.zip',
                caption='🌐 Архиви веб-сайт | Архив веб-сайта | Website archive'
            )
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        await update.message.reply_text("❌ Хатогӣ ҳангоми боргирӣ рух дод. Лутфан, дубора кӯшиш кунед.")

def get_admin_keyboard():
    """Создать клавиатуру админ-панели"""
    keyboard = [
        [InlineKeyboardButton("👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton("📨 Рассылка сообщений", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🔄 Обновить базу данных", callback_data="admin_update_db")],
        [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_management_keyboard():
    """Создать клавиатуру управления пользователями"""
    keyboard = [
        [InlineKeyboardButton("✅ Ожидающие подтверждения", callback_data="admin_pending")],
        [InlineKeyboardButton("👤 Все пользователи", callback_data="admin_all_users")],
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_action_keyboard(user_id):
    """Создать клавиатуру действий с пользователем"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
        ],
        [InlineKeyboardButton("↩️ Назад", callback_data="admin_pending")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_list_keyboard(users, page=0, page_size=5, back_command="admin_all_users"):
    """Создать клавиатуру со списком пользователей и пагинацией"""
    total_pages = (len(users) + page_size - 1) // page_size if users else 1
    start = page * page_size
    end = min(start + page_size, len(users)) if users else 0
    
    keyboard = []
    
    # Добавляем пользователей на текущей странице
    if users:
        for user in users[start:end]:
            username = user.get('username', 'Без имени')
            user_id = user.get('user_id')
            is_approved = "✅" if user.get('is_approved') else "⏳"
            is_admin = "👑" if user.get('is_admin') else ""
            button_text = f"{is_approved} {is_admin} @{username}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"user_{user_id}")])
    else:
        keyboard.append([InlineKeyboardButton("Нет пользователей", callback_data="header_none")])
    
    # Добавляем кнопки пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page-1}_{back_command}"))
    nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="header_page"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"page_{page+1}_{back_command}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
        
    # Кнопка "Назад"
    keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="admin_users")])
    
    return InlineKeyboardMarkup(keyboard)

def get_pending_keyboard(pending_users, page=0, page_size=5):
    """Создать клавиатуру со списком ожидающих подтверждения пользователей"""
    return get_user_list_keyboard(pending_users, page, page_size, "admin_pending")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /admin для входа в админ-панель"""
    user = update.effective_user
    user_id = user.id
    username = user.username
    
    # Проверяем, администратор ли это
    if username and username.lower() == ADMIN_USERNAME.lower():
        # Создаем админа, если его нет в базе (с предустановленным паролем)
        create_admin_user(user_id, username)
        
        # Запрашиваем пароль для подтверждения
        await update.message.reply_text(
            "👑 Панель администратора\n\nВведите пароль для доступа:"
        )
        return ADMIN_PASSWORD
    else:
        await update.message.reply_text(
            "❌ У вас нет прав доступа к этой команде."
        )
        return ConversationHandler.END

async def admin_check_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка пароля администратора"""
    password = update.message.text
    password_hash = hash_password(password)
    
    # Проверяем пароль
    if password_hash == ADMIN_PASSWORD_HASH:
        # Отображаем главное меню админа
        await update.message.reply_text(
            "✅ Доступ предоставлен. Добро пожаловать в панель администратора!",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    else:
        await update.message.reply_text(
            "❌ Неверный пароль. Доступ запрещен."
        )
        return ConversationHandler.END

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок в меню администратора"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "admin_users":
        # Переход в раздел управления пользователями
        await query.edit_message_text(
            "👥 Управление пользователями\n\nВыберите действие:",
            reply_markup=get_user_management_keyboard()
        )
        return ADMIN_USER_MANAGEMENT
    
    elif action == "admin_broadcast":
        # Переход в режим рассылки сообщений
        keyboard = [
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            "📨 Рассылка сообщений\n\n"
            "Введите текст сообщения, которое будет отправлено всем подтвержденным пользователям:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ADMIN_BROADCAST_MESSAGE
    
    elif action == "admin_stats":
        # Показать статистику
        users = get_all_users()
        total_users = len(users)
        approved_users = sum(1 for user in users if user.get('is_approved'))
        admin_users = sum(1 for user in users if user.get('is_admin'))
        
        stats_text = (
            "📊 Статистика бота\n\n"
            f"👥 Всего пользователей: {total_users}\n"
            f"✅ Подтвержденных пользователей: {approved_users}\n"
            f"👑 Администраторов: {admin_users}\n"
            f"⏳ Ожидают подтверждения: {total_users - approved_users}\n"
        )
        
        await query.edit_message_text(
            stats_text,
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    elif action == "admin_update_db":
        # Обновить базу данных
        try:
            from models import init_db
            init_db()
            await query.edit_message_text(
                "✅ База данных успешно обновлена!",
                reply_markup=get_admin_keyboard()
            )
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при обновлении базы данных: {str(e)}",
                reply_markup=get_admin_keyboard()
            )
        return ADMIN_MENU
    
    elif action == "change_language":
        # Сменить язык бота
        keyboard = get_language_keyboard()
        await query.edit_message_text(
            "Выберите язык / Забонро интихоб кунед / Tilni tanlang / Тілді таңдаңыз / Choose language:",
            reply_markup=keyboard
        )
        return ADMIN_MENU
    
    elif action == "admin_back":
        # Вернуться в главное меню админа
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    else:
        # Неизвестное действие
        await query.edit_message_text(
            "❓ Неизвестное действие. Пожалуйста, выберите опцию из меню.",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU

async def admin_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода текста для рассылки сообщений"""
    if update.message:
        # Обработка текста рассылки
        broadcast_text = update.message.text
        approved_user_ids = get_approved_user_ids()
        
        success_count = 0
        error_count = 0
        
        progress_message = await update.message.reply_text(
            "📨 Начинаю рассылку сообщений...\n"
            "0% выполнено (0/" + str(len(approved_user_ids)) + ")"
        )
        
        # Рассылка сообщений всем подтвержденным пользователям
        for i, user_id in enumerate(approved_user_ids):
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 Сообщение от администратора:\n\n{broadcast_text}"
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
                error_count += 1
            
            # Обновляем прогресс каждые 5 пользователей или в конце списка
            if (i + 1) % 5 == 0 or i == len(approved_user_ids) - 1:
                progress_percent = int((i + 1) / len(approved_user_ids) * 100)
                await progress_message.edit_text(
                    f"📨 Выполняется рассылка сообщений...\n"
                    f"{progress_percent}% выполнено ({i+1}/{len(approved_user_ids)})"
                )
        
        # Отправляем итоговый отчет
        await update.message.reply_text(
            f"✅ Рассылка завершена!\n\n"
            f"📊 Статистика:\n"
            f"✓ Успешно отправлено: {success_count}\n"
            f"❌ Ошибок: {error_count}\n"
            f"📝 Всего пользователей: {len(approved_user_ids)}",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    elif update.callback_query:
        # Обработка нажатия кнопки "Назад"
        query = update.callback_query
        await query.answer()
        
        if query.data == "admin_back":
            await query.edit_message_text(
                "👑 Панель администратора",
                reply_markup=get_admin_keyboard()
            )
            return ADMIN_MENU
    
    return ADMIN_BROADCAST_MESSAGE

async def admin_user_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню управления пользователями"""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "admin_pending":
        # Показать ожидающих подтверждения пользователей
        pending_users = get_pending_users()
        if pending_users:
            await query.edit_message_text(
                "⏳ Пользователи, ожидающие подтверждения:",
                reply_markup=get_pending_keyboard(pending_users)
            )
        else:
            await query.edit_message_text(
                "✅ Нет пользователей, ожидающих подтверждения.",
                reply_markup=get_user_management_keyboard()
            )
        return ADMIN_USER_MANAGEMENT
    
    elif action == "admin_all_users":
        # Показать всех пользователей
        users = get_all_users()
        await query.edit_message_text(
            "👥 Все пользователи:",
            reply_markup=get_user_list_keyboard(users)
        )
        return ADMIN_USER_MANAGEMENT
    
    elif action == "admin_back":
        # Вернуться в главное меню
        await query.edit_message_text(
            "👑 Панель администратора",
            reply_markup=get_admin_keyboard()
        )
        return ADMIN_MENU
    
    elif action.startswith("page_"):
        # Обработка пагинации
        parts = action.split("_")
        page = int(parts[1])
        back_command = parts[2]
        
        if back_command == "admin_pending":
            pending_users = get_pending_users()
            await query.edit_message_text(
                "⏳ Пользователи, ожидающие подтверждения:",
                reply_markup=get_pending_keyboard(pending_users, page)
            )
        else:  # admin_all_users
            users = get_all_users()
            await query.edit_message_text(
                "👥 Все пользователи:",
                reply_markup=get_user_list_keyboard(users, page)
            )
        return ADMIN_USER_MANAGEMENT
    
    elif action.startswith("user_"):
        # Действия с конкретным пользователем
        user_id = int(action.split("_")[1])
        user_data = get_user(user_id)
        
        if not user_data:
            await query.edit_message_text(
                "❌ Пользователь не найден.",
                reply_markup=get_user_management_keyboard()
            )
            return ADMIN_USER_MANAGEMENT
        
        is_admin = "✅" if user_data.get('is_admin') else "❌"
        is_approved = "✅" if user_data.get('is_approved') else "❌"
        username = user_data.get('username', 'Без имени')
        
        user_info = (
            f"👤 Информация о пользователе:\n\n"
            f"🆔 ID: {user_id}\n"
            f"👤 Имя: @{username}\n"
            f"👑 Администратор: {is_admin}\n"
            f"✅ Подтвержден: {is_approved}\n"
        )
        
        await query.edit_message_text(
            user_info,
            reply_markup=get_user_action_keyboard(user_id)
        )
        return ADMIN_USER_MANAGEMENT
    
    elif action.startswith("approve_") or action.startswith("reject_"):
        # Обработка подтверждения/отклонения пользователя
        is_approve = action.startswith("approve_")
        user_id = int(action.split("_")[1])
        
        if is_approve:
            # Генерируем пароль и одобряем пользователя
            password = ''.join([str(hash(datetime.now()))[i:i+2] for i in range(0, 8, 2)])
            password_hash = hash_password(password)
            
            if approve_user(user_id, password_hash):
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ Ваша заявка одобрена!\n\nВаш пароль для входа: `{password}`\n\nПожалуйста, сохраните его.",
                    parse_mode='MarkdownV2'
                )
                await query.edit_message_text(
                    f"✅ Пользователь с ID {user_id} одобрен. Пароль отправлен пользователю.",
                    reply_markup=get_user_management_keyboard()
                )
            else:
                await query.edit_message_text(
                    "❌ Произошла ошибка при одобрении пользователя.",
                    reply_markup=get_user_management_keyboard()
                )
        else:
            # Отклоняем заявку пользователя
            if delete_user(user_id):
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ Ваша заявка отклонена администратором."
                )
                await query.edit_message_text(
                    f"❌ Пользователь с ID {user_id} отклонен и удален.",
                    reply_markup=get_user_management_keyboard()
                )
            else:
                await query.edit_message_text(
                    "❌ Произошла ошибка при отклонении пользователя.",
                    reply_markup=get_user_management_keyboard()
                )
        
        return ADMIN_USER_MANAGEMENT
    
    else:
        # Неизвестное действие
        await query.edit_message_text(
            "❓ Неизвестное действие. Пожалуйста, выберите опцию из меню.",
            reply_markup=get_user_management_keyboard()
        )
        return ADMIN_USER_MANAGEMENT

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /register для регистрации пользователей"""
    user = update.effective_user
    user_id = user.id
    username = user.username
    
    # Проверяем, существует ли уже пользователь и его статус
    user_data = get_user(user_id)
    
    if user_data and user_data.get('is_approved'):
        await update.message.reply_text(
            "✅ Вы уже зарегистрированы и подтверждены."
        )
        return ConversationHandler.END
    
    # Добавляем пользователя в базу, если его еще нет
    if not user_data:
        add_user(user_id, username)
    
    # Добавляем пользователя в список ожидающих и отправляем запрос админу
    PENDING_USERS[user_id] = {
        'user_id': user_id,
        'username': username,
        'timestamp': datetime.now()
    }
    
    # Отправляем сообщение пользователю
    await update.message.reply_text(
        "📝 Ваша заявка отправлена администратору. "
        "Пожалуйста, ожидайте подтверждения. "
        "Вы получите уведомление, когда ваша заявка будет рассмотрена."
    )
    
    # Получаем чат администратора и отправляем ему уведомление
    admin_chat_id = await get_admin_chat_id(context.bot)
    if admin_chat_id:
        keyboard = [
            [
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{user_id}")
            ]
        ]
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=f"📝 Новая заявка на регистрацию!\n\n"
                f"👤 Пользователь: @{username}\n"
                f"🆔 ID: {user_id}\n"
                f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Если не удалось найти админа, сохраняем запрос в базе данных,
        # чтобы администратор мог просмотреть его через панель управления
        logger.warning(f"Admin chat not found. Registration request from user @{username} (ID: {user_id}) stored in pending list.")
    
    return ConversationHandler.END

def main():
    reconnect_delay = 5  # Start with 5 seconds delay
    max_reconnect_delay = 30  # Maximum delay between reconnection attempts
    max_consecutive_errors = 10
    error_count = 0
    last_error_time = None

    while True:  # Infinite loop for continuous operation
        try:
            # Start the keep-alive server
            keep_alive()
            logger.info("Starting bot...")

            application = Application.builder().token(BOT_TOKEN).build()

            # Add handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("download", download))
            
            # Обработчик регистрации
            application.add_handler(CommandHandler("register", register_command))
            
            # Обработчики для админ-панели
            admin_conv_handler = ConversationHandler(
                entry_points=[CommandHandler("admin", admin_command)],
                states={
                    ADMIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_check_password)],
                    ADMIN_MENU: [CallbackQueryHandler(admin_menu_handler)],
                    ADMIN_USER_MANAGEMENT: [CallbackQueryHandler(admin_user_management)],
                    ADMIN_BROADCAST_MESSAGE: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_message),
                        CallbackQueryHandler(admin_broadcast_message)
                    ],
                },
                fallbacks=[CommandHandler("start", start)]
            )
            application.add_handler(admin_conv_handler)
            
            # Обработчик кнопок действий с пользователями
            application.add_handler(CallbackQueryHandler(handle_admin_action, pattern=r"^(approve|reject)_\d+$"))
            
            # Обработчик текстовых сообщений
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            # Обработчик всех остальных кнопок
            application.add_handler(CallbackQueryHandler(button_click))

            # Set up error handlers
            application.add_error_handler(error_handler)

            # Reset error count on successful startup
            error_count = 0
            last_error_time = None

            # Run the bot with enhanced polling settings
            logger.info("Bot is running...")
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        except Exception as e:
            current_time = datetime.now()

            # Reset error count if last error was more than 1 hour ago
            if last_error_time and (current_time - last_error_time).seconds > 3600:
                error_count = 0

            error_count += 1
            last_error_time = current_time

            logger.error(f"Bot crashed with error: {str(e)}")
            logger.info(f"Attempting to restart in {reconnect_delay} seconds...")

            if error_count >= max_consecutive_errors:
                logger.critical("Too many consecutive errors. Forcing system restart...")
                try:
                    # Additional cleanup before restart
                    if 'application' in locals():
                        try:
                            application.stop()
                        except:
                            pass
                    os.execv(sys.executable, ['python'] + sys.argv)
                except Exception as restart_error:
                    logger.error(f"Failed to restart: {restart_error}")
                continue

            # Implement exponential backoff for reconnection attempts
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

            # Log detailed error information
            logger.error("Detailed error information:", exc_info=True)
            continue
        finally:
            # Reset reconnect delay on successful connection
            reconnect_delay = 5

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the telegram bot."""
    logger.error(f"Exception while handling an update: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Хатогӣ рух дод. Лутфан, дубора кӯшиш кунед."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {str(e)}")

if __name__ == '__main__':
    main()