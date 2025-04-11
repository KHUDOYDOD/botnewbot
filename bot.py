import logging
import hashlib
import time
import os
import sys
import random
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
# Состояния для разделов админ-панели
ADMIN_PASSWORD, ADMIN_MENU, ADMIN_USER_MANAGEMENT, ADMIN_BROADCAST_MESSAGE = range(4)
ADMIN_CURRENCY_MANAGEMENT, ADMIN_CURRENCY_ADD, ADMIN_CURRENCY_EDIT = range(4, 7)
ADMIN_TEXT_MANAGEMENT, ADMIN_TEXT_ADD, ADMIN_TEXT_EDIT = range(7, 10)
ADMIN_SETTINGS, ADMIN_CHANGE_PASSWORD, ADMIN_ACTIVITY, ADMIN_ABOUT = range(10, 14)

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
            register_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Отправить заявку", callback_data="send_request")],
                [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")]
            ])
            
            # Пытаемся создать и отправить приветственное изображение
            from create_welcome_image import create_welcome_image
            
            welcome_text = f"👋 Добро пожаловать, @{username}!\n\n" \
                          "Для использования бота необходимо отправить заявку на регистрацию.\n" \
                          "Администратор рассмотрит вашу заявку и предоставит доступ к боту.\n\n" \
                          "Вы можете отправить заявку прямо сейчас или воспользоваться командой /register позже.\n\n" \
                          "📞 Служба поддержки: @tradeporu"
            
            try:
                # Создаем и отправляем изображение
                if create_welcome_image():
                    with open('welcome_image.png', 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            caption=welcome_text,
                            reply_markup=register_keyboard
                        )
                else:
                    # Если изображение не создалось, отправляем текст
                    await update.message.reply_text(
                        welcome_text,
                        reply_markup=register_keyboard
                    )
            except Exception as e:
                logger.error(f"Ошибка при отправке приветственного изображения: {e}")
                # В случае ошибки просто отправляем текст
                await update.message.reply_text(
                    welcome_text,
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
        try:
            password = ''.join([str(hash(datetime.now()))[i:i+2] for i in range(0, 8, 2)])
            password_hash = hash_password(password)
            
            if approve_user(user_id, password_hash):
                del PENDING_USERS[user_id]
                
                # Экранируем специальные символы для Markdown
                escaped_password = password.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]").replace("(", "\\(").replace(")", "\\)").replace("~", "\\~").replace("`", "\\`").replace(">", "\\>").replace("#", "\\#").replace("+", "\\+").replace("-", "\\-").replace("=", "\\=").replace("|", "\\|").replace("{", "\\{").replace("}", "\\}").replace(".", "\\.").replace("!", "\\!")
                
                # Получаем информацию о языке пользователя
                user_data = get_user(user_id)
                lang_code = user_data['language_code'] if user_data and 'language_code' in user_data else 'tg'
                
                # Сообщения об одобрении на разных языках
                approval_messages = {
                    'tg': f"✅ Дархости шумо қабул карда шуд\\!\n\nРамзи шумо барои ворид шудан: `{escaped_password}`\n\nЛутфан, онро нигоҳ доред\\.",
                    'ru': f"✅ Ваша заявка одобрена\\!\n\nВаш пароль для входа: `{escaped_password}`\n\nПожалуйста, сохраните его\\.",
                    'uz': f"✅ Arizangiz tasdiqlandi\\!\n\nKirish uchun parolingiz: `{escaped_password}`\n\nIltimos, uni saqlab qoling\\.",
                    'kk': f"✅ Өтінішіңіз мақұлданды\\!\n\nКіру үшін құпия сөзіңіз: `{escaped_password}`\n\nОны сақтап қойыңыз\\.",
                    'en': f"✅ Your request has been approved\\!\n\nYour password: `{escaped_password}`\n\nPlease save it\\."
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
        except Exception as e:
            logger.error(f"Ошибка при одобрении пользователя через кнопку действия: {e}")
            await query.edit_message_text(f"❌ Ошибка при одобрении пользователя: {str(e)}")
    else:
        # Удаляем пользователя из списка ожидающих
        del PENDING_USERS[user_id]
        
        # Получаем информацию о языке пользователя
        user_data = get_user(user_id)
        lang_code = user_data['language_code'] if user_data and 'language_code' in user_data else 'tg'
        
        # Сбрасываем статус одобрения пользователя, но НЕ удаляем его из базы
        # Это позволит пользователю повторно отправить заявку
        from models import reset_user_approval
        reset_user_approval(user_id)
        
        # Сообщения об отклонении на разных языках
        rejection_messages = {
            'tg': "❌ Дархости шумо радд карда шуд.\n\nШумо метавонед дархости навро фиристед.",
            'ru': "❌ Ваша заявка отклонена администратором.\n\nВы можете отправить новую заявку.",
            'uz': "❌ Arizangiz administrator tomonidan rad etildi.\n\nSiz yangi ariza yuborishingiz mumkin.",
            'kk': "❌ Сіздің өтінішіңіз әкімші тарапынан қабылданбады.\n\nСіз жаңа өтініш жібере аласыз.",
            'en': "❌ Your request has been rejected by the administrator.\n\nYou can send a new request."
        }
        
        # Выбираем сообщение согласно языку пользователя
        message = rejection_messages.get(lang_code, rejection_messages['tg'])
        
        # Создаем клавиатуру с кнопкой для повторной отправки заявки
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Отправить новую заявку", callback_data="send_request")],
            [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")]
        ])
        
        # Отправляем сообщение пользователю с кнопкой повторной отправки
        await context.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=keyboard
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
            
            # Сообщения о заявке на разных языках с инструкциями по регистрации
            request_messages = {
                'tg': "📝 Дархости шумо ба маъмур фиристода шуд.\n\n"
                      "⚠️ Барои гирифтани дастрасӣ ба бот, лутфан:\n"
                      "1️⃣ Дар сайти Pocket Option бо тариқи TRADEPO.RU ба қайд гиред\n"
                      "2️⃣ ID худро ба админ равон кунед (мисол: id 111111)\n\n"
                      "Баъд аз ин, дархости шумо баррасӣ карда мешавад.",
                      
                'ru': "📝 Ваша заявка отправлена администратору.\n\n"
                      "⚠️ Для получения доступа к боту, пожалуйста:\n"
                      "1️⃣ Зарегистрируйтесь на сайте Pocket Option через TRADEPO.RU\n"
                      "2️⃣ Отправьте свой ID администратору (пример: id 111111)\n\n"
                      "После этого ваша заявка будет рассмотрена.",
                      
                'uz': "📝 Arizangiz administratorga yuborildi.\n\n"
                      "⚠️ Botga kirish uchun:\n"
                      "1️⃣ Pocket Option saytida TRADEPO.RU orqali ro'yxatdan o'ting\n"
                      "2️⃣ ID raqamingizni adminga yuboring (misol: id 111111)\n\n"
                      "Shundan so'ng arizangiz ko'rib chiqiladi.",
                      
                'kk': "📝 Сіздің өтінішіңіз әкімшіге жіберілді.\n\n"
                      "⚠️ Ботқа кіру үшін:\n"
                      "1️⃣ Pocket Option сайтында TRADEPO.RU арқылы тіркеліңіз\n"
                      "2️⃣ ID нөміріңізді әкімшіге жіберіңіз (мысалы: id 111111)\n\n"
                      "Осыдан кейін өтінішіңіз қаралады.",
                      
                'en': "📝 Your request has been sent to the administrator.\n\n"
                      "⚠️ To get access to the bot, please:\n"
                      "1️⃣ Register on Pocket Option website through TRADEPO.RU\n"
                      "2️⃣ Send your ID to the administrator (example: id 111111)\n\n"
                      "After that, your request will be reviewed."
            }
            
            # Отправляем сообщение пользователю на его языке
            message = request_messages.get(lang_code, request_messages['tg'])
            
            # Добавляем информацию о контактах службы поддержки
            support_messages = {
                'tg': "\n\n📞 Агар савол дошта бошед, метавонед бо хадамоти дастгирӣ тамос гиред: @tradeporu",
                'ru': "\n\n📞 Если у вас есть вопросы, вы можете связаться со службой поддержки: @tradeporu",
                'uz': "\n\n📞 Savollaringiz bo'lsa, qo'llab-quvvatlash xizmatiga murojaat qilishingiz mumkin: @tradeporu",
                'kk': "\n\n📞 Сұрақтарыңыз болса, қолдау қызметіне хабарласа аласыз: @tradeporu",
                'en': "\n\n📞 If you have any questions, you can contact support: @tradeporu"
            }
            
            # Добавляем информацию о поддержке к сообщению
            support_text = support_messages.get(lang_code, support_messages['tg'])
            message += support_text
            
            # Пробуем создать и отправить изображение
            # Импортируем модуль для создания изображения запроса
            from create_request_image import create_request_image
            try:
                # Создаем красивое изображение запроса с именем пользователя
                if create_request_image(username):
                    # Сначала удаляем текущее сообщение
                    await query.message.delete()
                    
                    # Создаем клавиатуру для кнопок под изображением
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")]
                    ])
                    
                    # Отправляем изображение с новым текстом и клавиатурой
                    with open('request_image.png', 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=photo,
                            caption=message,
                            reply_markup=keyboard
                        )
                else:
                    # Если не удалось создать изображение, просто редактируем текст с клавиатурой
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")]
                    ])
                    await query.edit_message_text(message, reply_markup=keyboard)
            except Exception as e:
                logger.error(f"Ошибка при отправке изображения запроса: {e}")
                # В случае ошибки просто редактируем текст с клавиатурой
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language")]
                ])
                await query.edit_message_text(message, reply_markup=keyboard)
            
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
    """Создать улучшенную клавиатуру админ-панели"""
    keyboard = [
        # Основные функции управления
        [
            InlineKeyboardButton("👥 Управление пользователями", callback_data="admin_users"),
            InlineKeyboardButton("💱 Управление валютами", callback_data="admin_currencies")
        ],
        [
            InlineKeyboardButton("📝 Управление текстами", callback_data="admin_texts"),
            InlineKeyboardButton("📨 Рассылка сообщений", callback_data="admin_broadcast")
        ],
        
        # Аналитические функции и настройки
        [InlineKeyboardButton("📊 Статистика бота", callback_data="admin_stats")],
        [
            InlineKeyboardButton("📈 Анализ активности", callback_data="admin_activity"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")
        ],
        
        # Безопасность и обслуживание
        [
            InlineKeyboardButton("🔐 Сменить пароль", callback_data="admin_change_password"),
            InlineKeyboardButton("🔄 Обновить БД", callback_data="admin_update_db")
        ],
        
        # Разное
        [
            InlineKeyboardButton("🌐 Сменить язык", callback_data="change_language"),
            InlineKeyboardButton("ℹ️ О боте", callback_data="admin_about")
        ]
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
    
    elif action == "admin_currencies":
        # Переход в раздел управления валютами
        from models import get_all_currency_pairs
        currency_pairs = get_all_currency_pairs()
        
        currency_list = "\n".join([
            f"- {pair['display_name']} ({pair['pair_code']}): {'🟢 Активна' if pair['is_active'] else '🔴 Неактивна'}"
            for pair in currency_pairs
        ])
        
        if not currency_list:
            currency_list = "Нет добавленных валютных пар"
        
        currency_keyboard = [
            [InlineKeyboardButton("➕ Добавить валютную пару", callback_data="admin_add_currency")],
            [InlineKeyboardButton("🔄 Обновить все пары", callback_data="admin_refresh_currencies")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        await query.edit_message_text(
            f"💱 Управление валютными парами\n\nСписок валютных пар:\n{currency_list}",
            reply_markup=InlineKeyboardMarkup(currency_keyboard)
        )
        return ADMIN_CURRENCY_MANAGEMENT
        
    elif action == "admin_texts":
        # Переход в раздел управления текстами
        from models import get_all_bot_messages
        messages = get_all_bot_messages()
        
        texts_keyboard = [
            [InlineKeyboardButton("➕ Добавить новый текст", callback_data="admin_add_text")],
            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
        ]
        
        # Группируем сообщения по ключам
        message_keys = {}
        for msg in messages:
            key = msg['message_key']
            if key not in message_keys:
                message_keys[key] = []
            message_keys[key].append(msg)
        
        # Добавляем кнопки для каждого ключа сообщения
        for key in message_keys:
            texts_keyboard.insert(-1, [InlineKeyboardButton(f"📝 {key}", callback_data=f"admin_edit_text_{key}")])
        
        if not message_keys:
            message_summary = "Нет добавленных текстов"
        else:
            message_summary = "Тексты в базе данных:\n" + "\n".join([
                f"- {key} ({len(langs)} языков)" 
                for key, langs in message_keys.items()
            ])
        
        await query.edit_message_text(
            f"📝 Управление текстами бота\n\n{message_summary}",
            reply_markup=InlineKeyboardMarkup(texts_keyboard)
        )
        return ADMIN_TEXT_MANAGEMENT
        
    elif action == "admin_activity":
        # Переход к анализу активности
        await query.edit_message_text(
            "Загрузка анализа активности...",
            reply_markup=None
        )
        return await admin_activity(update, context)
    
    elif action == "admin_settings":
        # Переход к настройкам бота
        await query.edit_message_text(
            "Загрузка настроек бота...",
            reply_markup=None
        )
        return await admin_settings(update, context)
    
    elif action == "admin_change_password":
        # Переход к смене пароля администратора
        await query.edit_message_text(
            "Загрузка страницы смены пароля...",
            reply_markup=None
        )
        return await admin_change_password(update, context)
    
    elif action == "admin_about":
        # Переход к информации о боте
        await query.edit_message_text(
            "Загрузка информации о боте...",
            reply_markup=None
        )
        return await admin_about(update, context)
    
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
            try:
                # Генерируем пароль и одобряем пользователя
                password = ''.join([str(hash(datetime.now()))[i:i+2] for i in range(0, 8, 2)])
                password_hash = hash_password(password)
                
                if approve_user(user_id, password_hash):
                    # Экранируем специальные символы для Markdown
                    escaped_password = password.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]").replace("(", "\\(").replace(")", "\\)").replace("~", "\\~").replace("`", "\\`").replace(">", "\\>").replace("#", "\\#").replace("+", "\\+").replace("-", "\\-").replace("=", "\\=").replace("|", "\\|").replace("{", "\\{").replace("}", "\\}").replace(".", "\\.").replace("!", "\\!")
                    
                    # Получаем язык пользователя
                    user_data = get_user(user_id)
                    lang_code = user_data['language_code'] if user_data and 'language_code' in user_data else 'tg'
                    
                    # Сообщения об одобрении на разных языках
                    approval_messages = {
                        'tg': f"✅ Дархости шумо қабул карда шуд\\!\n\nРамзи шумо барои ворид шудан: `{escaped_password}`\n\nЛутфан, онро нигоҳ доред\\.",
                        'ru': f"✅ Ваша заявка одобрена\\!\n\nВаш пароль для входа: `{escaped_password}`\n\nПожалуйста, сохраните его\\.",
                        'uz': f"✅ Arizangiz tasdiqlandi\\!\n\nKirish uchun parolingiz: `{escaped_password}`\n\nIltimos, uni saqlab qoling\\.",
                        'kk': f"✅ Өтінішіңіз мақұлданды\\!\n\nКіру үшін құпия сөзіңіз: `{escaped_password}`\n\nОны сақтап қойыңыз\\.",
                        'en': f"✅ Your request has been approved\\!\n\nYour password: `{escaped_password}`\n\nPlease save it\\."
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
                    await query.edit_message_text(
                        f"✅ Пользователь с ID {user_id} одобрен. Пароль отправлен пользователю.",
                        reply_markup=get_user_management_keyboard()
                    )
                else:
                    await query.edit_message_text(
                        "❌ Произошла ошибка при одобрении пользователя.",
                        reply_markup=get_user_management_keyboard()
                    )
            except Exception as e:
                logger.error(f"Ошибка при одобрении пользователя: {e}")
                await query.edit_message_text(
                    f"❌ Произошла ошибка при одобрении пользователя: {str(e)}",
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
    
    # Добавляем информацию о контактах службы поддержки
    support_messages = {
        'tg': "\n\n📞 Агар савол дошта бошед, метавонед бо хадамоти дастгирӣ тамос гиред: @tradeporu",
        'ru': "\n\n📞 Если у вас есть вопросы, вы можете связаться со службой поддержки: @tradeporu",
        'uz': "\n\n📞 Savollaringiz bo'lsa, qo'llab-quvvatlash xizmatiga murojaat qilishingiz mumkin: @tradeporu",
        'kk': "\n\n📞 Сұрақтарыңыз болса, қолдау қызметіне хабарласа аласыз: @tradeporu",
        'en': "\n\n📞 If you have any questions, you can contact support: @tradeporu"
    }
    
    # Отправляем сообщение пользователю на его языке
    message = request_messages.get(lang_code, request_messages['tg'])
    support_text = support_messages.get(lang_code, support_messages['tg'])
    message += support_text
    
    # Пробуем создать и отправить изображение
    from create_welcome_image import create_welcome_image
    try:
        # Создаем изображение
        if create_welcome_image():
            # Отправляем изображение с новым текстом
            with open('welcome_image.png', 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=message
                )
        else:
            # Если не удалось создать изображение, просто отправляем текст
            await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Ошибка при отправке приветственного изображения: {e}")
        # В случае ошибки просто отправляем текст
        await update.message.reply_text(message)
    
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
            # Добавляем функции для управления валютами и текстами
            async def admin_currency_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик меню управления валютными парами"""
                query = update.callback_query
                if query:
                    await query.answer()
                    action = query.data
                    
                    if action == "admin_back":
                        # Вернуться в главное меню админа
                        await query.edit_message_text(
                            "👑 Панель администратора",
                            reply_markup=get_admin_keyboard()
                        )
                        return ADMIN_MENU
                    
                    elif action == "admin_add_currency":
                        # Форма добавления новой валютной пары
                        await query.edit_message_text(
                            "➕ Добавление новой валютной пары\n\n"
                            "Введите данные в формате:\n"
                            "Код пары|Символ|Отображаемое название\n\n"
                            "Например:\n"
                            "BTCUSD|BTC-USD|BTC/USD",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                            ]])
                        )
                        return ADMIN_CURRENCY_ADD
                    
                    elif action == "admin_refresh_currencies":
                        # Обновляем список валютных пар из базы
                        from models import import_default_currency_pairs
                        success = import_default_currency_pairs()
                        
                        if success:
                            await query.edit_message_text(
                                "✅ Валютные пары успешно обновлены!",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                                ]])
                            )
                        else:
                            await query.edit_message_text(
                                "ℹ️ Валютные пары уже обновлены или в базе уже есть данные.",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                                ]])
                            )
                        return ADMIN_CURRENCY_MANAGEMENT
                    
                    elif action.startswith("currency_toggle_"):
                        # Включение/отключение валютной пары
                        pair_code = action.replace("currency_toggle_", "")
                        from models import update_currency_pair_status, get_all_currency_pairs
                        
                        # Получаем текущий статус пары
                        pairs = get_all_currency_pairs()
                        current_pair = next((p for p in pairs if p['pair_code'] == pair_code), None)
                        
                        if current_pair:
                            # Меняем статус на противоположный
                            new_status = not current_pair['is_active']
                            success = update_currency_pair_status(pair_code, new_status)
                            
                            if success:
                                status_text = "активирована" if new_status else "деактивирована"
                                await query.edit_message_text(
                                    f"✅ Валютная пара {current_pair['display_name']} успешно {status_text}!",
                                    reply_markup=InlineKeyboardMarkup([[
                                        InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                                    ]])
                                )
                            else:
                                await query.edit_message_text(
                                    "❌ Ошибка при изменении статуса валютной пары.",
                                    reply_markup=InlineKeyboardMarkup([[
                                        InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                                    ]])
                                )
                        else:
                            await query.edit_message_text(
                                "❌ Валютная пара не найдена.",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                                ]])
                            )
                        return ADMIN_CURRENCY_MANAGEMENT
                    
                    elif action == "admin_currencies":
                        # Возврат в меню валют
                        from models import get_all_currency_pairs
                        currency_pairs = get_all_currency_pairs()
                        
                        currency_list = "\n".join([
                            f"- {pair['display_name']} ({pair['pair_code']}): {'🟢 Активна' if pair['is_active'] else '🔴 Неактивна'}"
                            for pair in currency_pairs
                        ])
                        
                        if not currency_list:
                            currency_list = "Нет добавленных валютных пар"
                        
                        currency_keyboard = [
                            [InlineKeyboardButton("➕ Добавить валютную пару", callback_data="admin_add_currency")],
                            [InlineKeyboardButton("🔄 Обновить все пары", callback_data="admin_refresh_currencies")],
                            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                        ]
                        
                        # Добавляем кнопки для каждой валютной пары
                        for pair in currency_pairs:
                            toggle_text = "🔴 Деактивировать" if pair['is_active'] else "🟢 Активировать"
                            currency_keyboard.insert(-1, [
                                InlineKeyboardButton(f"{pair['display_name']} - {toggle_text}", 
                                                    callback_data=f"currency_toggle_{pair['pair_code']}")
                            ])
                        
                        await query.edit_message_text(
                            f"💱 Управление валютными парами\n\nСписок валютных пар:\n{currency_list}",
                            reply_markup=InlineKeyboardMarkup(currency_keyboard)
                        )
                        return ADMIN_CURRENCY_MANAGEMENT
                
                return ADMIN_CURRENCY_MANAGEMENT
            
            async def admin_add_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик добавления новой валютной пары"""
                if update.callback_query:
                    query = update.callback_query
                    await query.answer()
                    
                    if query.data == "admin_currencies":
                        # Возврат в меню валют
                        return await admin_currency_management(update, context)
                    
                    return ADMIN_CURRENCY_ADD
                
                if update.message:
                    # Обработка данных новой валютной пары
                    text = update.message.text
                    parts = text.strip().split('|')
                    
                    if len(parts) != 3:
                        await update.message.reply_text(
                            "❌ Неверный формат данных. Введите данные в формате:\n"
                            "Код пары|Символ|Отображаемое название\n\n"
                            "Например:\n"
                            "BTCUSD|BTC-USD|BTC/USD",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ Назад", callback_data="admin_currencies")
                            ]])
                        )
                        return ADMIN_CURRENCY_ADD
                    
                    pair_code = parts[0].strip()
                    symbol = parts[1].strip()
                    display_name = parts[2].strip()
                    
                    from models import add_or_update_currency_pair
                    pair_id = add_or_update_currency_pair(pair_code, symbol, display_name)
                    
                    if pair_id:
                        # Успешно добавлено
                        await update.message.reply_text(
                            f"✅ Валютная пара {display_name} успешно добавлена!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ К списку валют", callback_data="admin_currencies")
                            ]])
                        )
                    else:
                        # Ошибка при добавлении
                        await update.message.reply_text(
                            "❌ Ошибка при добавлении валютной пары.",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ К списку валют", callback_data="admin_currencies")
                            ]])
                        )
                    
                    return ADMIN_CURRENCY_MANAGEMENT
                
                return ADMIN_CURRENCY_ADD
            
            async def admin_text_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик управления текстами бота"""
                query = update.callback_query
                if query:
                    await query.answer()
                    action = query.data
                    
                    if action == "admin_back":
                        # Вернуться в главное меню админа
                        await query.edit_message_text(
                            "👑 Панель администратора",
                            reply_markup=get_admin_keyboard()
                        )
                        return ADMIN_MENU
                    
                    elif action == "admin_add_text":
                        # Форма добавления нового текста
                        await query.edit_message_text(
                            "➕ Добавление нового текста\n\n"
                            "Введите данные в формате:\n"
                            "Ключ|Язык|Текст\n\n"
                            "Например:\n"
                            "WELCOME|ru|Добро пожаловать в бот!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ Назад", callback_data="admin_texts")
                            ]])
                        )
                        return ADMIN_TEXT_ADD
                    
                    elif action.startswith("admin_edit_text_"):
                        # Редактирование конкретного текста
                        key = action.replace("admin_edit_text_", "")
                        
                        from models import get_all_bot_messages
                        messages = get_all_bot_messages()
                        
                        # Фильтруем сообщения по ключу
                        key_messages = [msg for msg in messages if msg['message_key'] == key]
                        
                        message_text = f"📝 Редактирование текста: {key}\n\n"
                        
                        for msg in key_messages:
                            lang_code = msg['language_code']
                            text = msg['message_text']
                            message_text += f"*{lang_code}*: {text[:50]}{'...' if len(text) > 50 else ''}\n\n"
                        
                        edit_keyboard = [
                            [InlineKeyboardButton("➕ Добавить перевод", callback_data=f"admin_add_translation_{key}")],
                            [InlineKeyboardButton("↩️ Назад", callback_data="admin_texts")]
                        ]
                        
                        # Добавляем кнопки для редактирования каждого языка
                        for msg in key_messages:
                            lang_code = msg['language_code']
                            edit_keyboard.insert(-1, [
                                InlineKeyboardButton(f"✏️ Изменить {lang_code}", 
                                                    callback_data=f"admin_edit_translation_{key}_{lang_code}")
                            ])
                        
                        await query.edit_message_text(
                            message_text,
                            reply_markup=InlineKeyboardMarkup(edit_keyboard)
                        )
                        return ADMIN_TEXT_EDIT
                    
                    elif action == "admin_texts":
                        # Возврат в меню текстов
                        from models import get_all_bot_messages
                        messages = get_all_bot_messages()
                        
                        texts_keyboard = [
                            [InlineKeyboardButton("➕ Добавить новый текст", callback_data="admin_add_text")],
                            [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                        ]
                        
                        # Группируем сообщения по ключам
                        message_keys = {}
                        for msg in messages:
                            key = msg['message_key']
                            if key not in message_keys:
                                message_keys[key] = []
                            message_keys[key].append(msg)
                        
                        # Добавляем кнопки для каждого ключа сообщения
                        for key in message_keys:
                            texts_keyboard.insert(-1, [InlineKeyboardButton(f"📝 {key}", callback_data=f"admin_edit_text_{key}")])
                        
                        if not message_keys:
                            message_summary = "Нет добавленных текстов"
                        else:
                            message_summary = "Тексты в базе данных:\n" + "\n".join([
                                f"- {key} ({len(langs)} языков)" 
                                for key, langs in message_keys.items()
                            ])
                        
                        await query.edit_message_text(
                            f"📝 Управление текстами бота\n\n{message_summary}",
                            reply_markup=InlineKeyboardMarkup(texts_keyboard)
                        )
                        return ADMIN_TEXT_MANAGEMENT
                
                return ADMIN_TEXT_MANAGEMENT
            
            async def admin_text_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик добавления нового текста"""
                if update.callback_query:
                    query = update.callback_query
                    await query.answer()
                    
                    if query.data == "admin_texts":
                        # Возврат в меню текстов
                        return await admin_text_management(update, context)
                    
                    return ADMIN_TEXT_ADD
                
                if update.message:
                    # Обработка данных нового текста
                    text = update.message.text
                    parts = text.strip().split('|', 2)  # Разделяем на 3 части (ключ, язык, текст)
                    
                    if len(parts) != 3:
                        await update.message.reply_text(
                            "❌ Неверный формат данных. Введите данные в формате:\n"
                            "Ключ|Язык|Текст\n\n"
                            "Например:\n"
                            "WELCOME|ru|Добро пожаловать в бот!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ Назад", callback_data="admin_texts")
                            ]])
                        )
                        return ADMIN_TEXT_ADD
                    
                    key = parts[0].strip()
                    lang_code = parts[1].strip()
                    message_text = parts[2].strip()
                    
                    from models import update_bot_message
                    msg_id = update_bot_message(key, lang_code, message_text)
                    
                    if msg_id:
                        # Успешно добавлено
                        await update.message.reply_text(
                            f"✅ Текст с ключом {key} для языка {lang_code} успешно добавлен!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                            ]])
                        )
                    else:
                        # Ошибка при добавлении
                        await update.message.reply_text(
                            "❌ Ошибка при добавлении текста.",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                            ]])
                        )
                    
                    return ADMIN_TEXT_MANAGEMENT
                
                return ADMIN_TEXT_ADD
            
            async def admin_text_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик редактирования текстов"""
                if update.callback_query:
                    query = update.callback_query
                    await query.answer()
                    action = query.data
                    
                    if action == "admin_texts":
                        # Возврат в меню текстов
                        return await admin_text_management(update, context)
                    
                    elif action.startswith("admin_add_translation_"):
                        # Добавление перевода для существующего ключа
                        key = action.replace("admin_add_translation_", "")
                        
                        await query.edit_message_text(
                            f"➕ Добавление перевода для ключа: {key}\n\n"
                            "Введите данные в формате:\n"
                            "Язык|Текст\n\n"
                            "Например:\n"
                            "en|Welcome to the bot!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("↩️ Назад", callback_data=f"admin_edit_text_{key}")
                            ]])
                        )
                        # Сохраняем ключ в контексте для последующего использования
                        context.user_data['current_edit_key'] = key
                        return ADMIN_TEXT_ADD
                    
                    elif action.startswith("admin_edit_translation_"):
                        # Редактирование конкретного перевода
                        parts = action.replace("admin_edit_translation_", "").split('_')
                        if len(parts) >= 2:
                            key = parts[0]
                            lang_code = parts[1]
                            
                            from models import get_bot_message
                            current_text = get_bot_message(key, lang_code)
                            
                            if current_text:
                                await query.edit_message_text(
                                    f"✏️ Редактирование текста для ключа: {key}, язык: {lang_code}\n\n"
                                    f"Текущий текст:\n{current_text}\n\n"
                                    "Введите новый текст:",
                                    reply_markup=InlineKeyboardMarkup([[
                                        InlineKeyboardButton("↩️ Назад", callback_data=f"admin_edit_text_{key}")
                                    ]])
                                )
                                # Сохраняем данные в контексте для последующего использования
                                context.user_data['current_edit_key'] = key
                                context.user_data['current_edit_lang'] = lang_code
                                return ADMIN_TEXT_EDIT
                            else:
                                await query.edit_message_text(
                                    "❌ Текст не найден.",
                                    reply_markup=InlineKeyboardMarkup([[
                                        InlineKeyboardButton("↩️ Назад", callback_data="admin_texts")
                                    ]])
                                )
                                return ADMIN_TEXT_MANAGEMENT
                    
                    return ADMIN_TEXT_EDIT
                
                if update.message:
                    # Обработка нового текста
                    text = update.message.text
                    
                    # Определяем режим (добавление перевода или редактирование)
                    if 'current_edit_key' in context.user_data and 'current_edit_lang' in context.user_data:
                        # Режим редактирования существующего перевода
                        key = context.user_data['current_edit_key']
                        lang_code = context.user_data['current_edit_lang']
                        
                        from models import update_bot_message
                        msg_id = update_bot_message(key, lang_code, text)
                        
                        if msg_id:
                            # Успешно обновлено
                            await update.message.reply_text(
                                f"✅ Текст с ключом {key} для языка {lang_code} успешно обновлен!",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                                ]])
                            )
                        else:
                            # Ошибка при обновлении
                            await update.message.reply_text(
                                "❌ Ошибка при обновлении текста.",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                                ]])
                            )
                        
                        # Очищаем контекст
                        if 'current_edit_key' in context.user_data:
                            del context.user_data['current_edit_key']
                        if 'current_edit_lang' in context.user_data:
                            del context.user_data['current_edit_lang']
                        
                        return ADMIN_TEXT_MANAGEMENT
                    
                    elif 'current_edit_key' in context.user_data:
                        # Режим добавления нового перевода
                        key = context.user_data['current_edit_key']
                        parts = text.strip().split('|', 1)  # Разделяем на 2 части (язык, текст)
                        
                        if len(parts) != 2:
                            await update.message.reply_text(
                                "❌ Неверный формат данных. Введите данные в формате:\n"
                                "Язык|Текст\n\n"
                                "Например:\n"
                                "en|Welcome to the bot!",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ Назад", callback_data=f"admin_edit_text_{key}")
                                ]])
                            )
                            return ADMIN_TEXT_ADD
                        
                        lang_code = parts[0].strip()
                        message_text = parts[1].strip()
                        
                        from models import update_bot_message
                        msg_id = update_bot_message(key, lang_code, message_text)
                        
                        if msg_id:
                            # Успешно добавлено
                            await update.message.reply_text(
                                f"✅ Перевод для ключа {key} на язык {lang_code} успешно добавлен!",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                                ]])
                            )
                        else:
                            # Ошибка при добавлении
                            await update.message.reply_text(
                                "❌ Ошибка при добавлении перевода.",
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("↩️ К списку текстов", callback_data="admin_texts")
                                ]])
                            )
                        
                        # Очищаем контекст
                        if 'current_edit_key' in context.user_data:
                            del context.user_data['current_edit_key']
                        
                        return ADMIN_TEXT_MANAGEMENT
                
                return ADMIN_TEXT_EDIT
            
            # Создаем обработчик для админ-панели
            # Создаем функции для обработки новых опций админ-панели
            async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик настроек бота"""
                query = update.callback_query
                await query.answer()
                
                action = query.data
                
                if action == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                # Настройки бота
                settings_keyboard = [
                    [InlineKeyboardButton("⏱️ Частота обновления данных", callback_data="admin_setting_update_freq")],
                    [InlineKeyboardButton("🔔 Настройки уведомлений", callback_data="admin_setting_notifications")],
                    [InlineKeyboardButton("🌐 Региональные настройки", callback_data="admin_setting_regional")],
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                await query.edit_message_text(
                    "⚙️ Настройки бота\n\n"
                    "Выберите категорию настроек:",
                    reply_markup=InlineKeyboardMarkup(settings_keyboard)
                )
                return ADMIN_SETTINGS
            
            async def admin_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик анализа активности"""
                query = update.callback_query
                await query.answer()
                
                action = query.data
                
                if action == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                # Подготовка данных об активности (заглушка)
                users = get_all_users()
                total_users = len(users)
                approved_users = sum(1 for user in users if user.get('is_approved'))
                
                # Имитация данных об активности по дням недели
                days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                activity = [random.randint(5, 20) for _ in range(7)]
                
                activity_text = "📈 Анализ активности\n\n"
                activity_text += f"👥 Всего пользователей: {total_users}\n"
                activity_text += f"✅ Активных пользователей: {approved_users}\n\n"
                
                activity_text += "📊 Активность по дням недели:\n"
                for i, day in enumerate(days):
                    activity_text += f"{day}: {'▮' * (activity[i] // 2)} ({activity[i]})\n"
                
                activity_keyboard = [
                    [InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_activity_details")],
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                await query.edit_message_text(
                    activity_text,
                    reply_markup=InlineKeyboardMarkup(activity_keyboard)
                )
                return ADMIN_ACTIVITY
            
            async def admin_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Информация о боте"""
                query = update.callback_query
                await query.answer()
                
                if query.data == "admin_back":
                    await query.edit_message_text(
                        "👑 Панель администратора",
                        reply_markup=get_admin_keyboard()
                    )
                    return ADMIN_MENU
                
                about_text = (
                    "ℹ️ О боте\n\n"
                    "✨ *Trade Analysis Bot* ✨\n\n"
                    "Версия: 2.0.0\n"
                    "Разработан: Replit AI\n"
                    "Лицензия: Proprietary\n\n"
                    "📝 Описание:\n"
                    "Профессиональный бот для анализа рынка "
                    "с системой управления пользователями.\n\n"
                    "🛠 Технологии:\n"
                    "• Python 3.11\n"
                    "• Python-telegram-bot\n"
                    "• PostgreSQL\n"
                    "• YFinance API\n\n"
                    "📞 Контакты:\n"
                    "Поддержка: @tradeporu\n"
                )
                
                about_keyboard = [
                    [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                ]
                
                await query.edit_message_text(
                    about_text,
                    reply_markup=InlineKeyboardMarkup(about_keyboard),
                    parse_mode='Markdown'
                )
                return ADMIN_ABOUT
            
            async def admin_change_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
                """Обработчик смены пароля администратора"""
                query = update.callback_query
                if query:
                    await query.answer()
                    
                    if query.data == "admin_back":
                        await query.edit_message_text(
                            "👑 Панель администратора",
                            reply_markup=get_admin_keyboard()
                        )
                        return ADMIN_MENU
                    
                    # Первый заход в функцию
                    keyboard = [
                        [InlineKeyboardButton("↩️ Назад", callback_data="admin_back")]
                    ]
                    
                    await query.edit_message_text(
                        "🔐 Смена пароля администратора\n\n"
                        "Введите новый пароль администратора.\n"
                        "Пароль должен содержать минимум 6 символов.",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    context.user_data['admin_changing_password'] = True
                    return ADMIN_CHANGE_PASSWORD
                
                elif update.message and context.user_data.get('admin_changing_password'):
                    new_password = update.message.text
                    
                    # Проверка минимальной длины пароля
                    if len(new_password) < 6:
                        await update.message.reply_text(
                            "❌ Пароль должен содержать минимум 6 символов!\n\n"
                            "Пожалуйста, введите другой пароль или нажмите /admin для отмены."
                        )
                        return ADMIN_CHANGE_PASSWORD
                    
                    # Хеширование нового пароля и обновление в config
                    new_password_hash = hash_password(new_password)
                    
                    # Обновление пароля администратора (заглушка)
                    global ADMIN_PASSWORD_HASH
                    ADMIN_PASSWORD_HASH = new_password_hash
                    
                    # Уведомление о смене пароля
                    await update.message.reply_text(
                        "✅ Пароль администратора успешно изменен!",
                        reply_markup=get_admin_keyboard()
                    )
                    
                    # Очистка контекста
                    if 'admin_changing_password' in context.user_data:
                        del context.user_data['admin_changing_password']
                    
                    return ADMIN_MENU
                
                return ADMIN_MENU
            
            # Добавляем обработчик для админ-панели с новыми функциями
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
                    ADMIN_CURRENCY_MANAGEMENT: [CallbackQueryHandler(admin_currency_management)],
                    ADMIN_CURRENCY_ADD: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_currency),
                        CallbackQueryHandler(admin_add_currency)
                    ],
                    ADMIN_CURRENCY_EDIT: [CallbackQueryHandler(admin_currency_management)],
                    ADMIN_TEXT_MANAGEMENT: [CallbackQueryHandler(admin_text_management)],
                    ADMIN_TEXT_ADD: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_add),
                        CallbackQueryHandler(admin_text_add)
                    ],
                    ADMIN_TEXT_EDIT: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_edit),
                        CallbackQueryHandler(admin_text_edit)
                    ],
                    ADMIN_SETTINGS: [CallbackQueryHandler(admin_settings)],
                    ADMIN_CHANGE_PASSWORD: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_change_password),
                        CallbackQueryHandler(admin_change_password)
                    ],
                    ADMIN_ACTIVITY: [CallbackQueryHandler(admin_activity)],
                    ADMIN_ABOUT: [CallbackQueryHandler(admin_about)],
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