import os

# Bot configuration and constants
BOT_TOKEN = os.environ.get('BOT_TOKEN')

LANGUAGES = {
    'tg': 'Тоҷикӣ 🇹🇯',
    'ru': 'Русский 🇷🇺',
    'uz': 'O\'zbek 🇺🇿',
    'kk': 'Қазақша 🇰🇿',
    'en': 'English 🇬🇧'
}

CURRENCY_PAIRS = {
    # Major Pairs with Emojis
    '💶 EUR/USD': 'EURUSD=X',
    '💷 GBP/USD': 'GBPUSD=X',
    '💴 USD/JPY': 'USDJPY=X',
    '💰 USD/CHF': 'USDCHF=X',
    '🦘 AUD/USD': 'AUDUSD=X',
    '🍁 USD/CAD': 'USDCAD=X',
    '🥝 NZD/USD': 'NZDUSD=X',

    # Cross Rates with Emojis
    '🇪🇺 EUR/GBP': 'EURGBP=X',
    '🗾 EUR/JPY': 'EURJPY=X',
    '🇬🇧 GBP/JPY': 'GBPJPY=X',
    '🇦🇺 AUD/JPY': 'AUDJPY=X',
    '🌏 EUR/AUD': 'EURAUD=X',
    '🌍 GBP/AUD': 'GBPAUD=X',
    '🌎 EUR/CAD': 'EURCAD=X',
    '🏔️ EUR/CHF': 'EURCHF=X',
    '🗺️ GBP/CHF': 'GBPCHF=X',
    '🌊 AUD/NZD': 'AUDNZD=X',

    # Popular Crypto
    '₿ BTC/USD': 'BTC-USD',
    '⟠ ETH/USD': 'ETH-USD',
    '✨ XRP/USD': 'XRP-USD',
    '🐕 DOGE/USD': 'DOGE-USD',
    '☀️ SOL/USD': 'SOL-USD',
    '🔷 ADA/USD': 'ADA-USD',

    # Additional Crypto
    '🔷 MATIC/USD': 'MATIC-USD',
    '⚡ DOT/USD': 'DOT-USD',
    '🔗 LINK/USD': 'LINK-USD',
    '🦄 UNI/USD': 'UNI-USD',
    '❄️ AVAX/USD': 'AVAX-USD',
    '⚛️ ATOM/USD': 'ATOM-USD',

    # New Popular Pairs
    '🇨🇳 USD/CNH': 'USDCNH=X',
    '🇮🇳 USD/INR': 'USDINR=X',
    '🇧🇷 USD/BRL': 'USDBRL=X',
    '🇲🇽 USD/MXN': 'USDMXN=X',
    '🇹🇷 USD/TRY': 'USDTRY=X',
    '🇿🇦 USD/ZAR': 'USDZAR=X'
}

MESSAGES = {
    'tg': {
        'WELCOME': """🌟 *Хуш омадед ба боти пешрафтаи таҳлили бозори молиявӣ\!*

        📊 *Имкониятҳои асосӣ:*
• 💹 Таҳлили техникӣ барои 35\+ ҷуфти асъор
• 📈 Нишондиҳандаҳои боэътимод \(RSI, MACD, EMA\)
• ⚡️ Сигналҳои фаврӣ бо дақиқии то 95\%
• 🌍 Дастгирии 5 забон
• 📱 Интерфейси осон ва фаҳмо
• 📊 Графикҳои возеҳ ва муфассал
• ⏱ Таҳлил дар вақтҳои гуногун

        💎 *Ҷуфтҳои асъор:*
• 🏆 Асъорҳои асосӣ: EUR/USD, GBP/USD, USD/JPY
• 🌟 Асъорҳои алоқаманд: EUR/GBP, GBP/JPY, EUR/JPY
• 💰 Криптоасъорҳо: BTC/USD, ETH/USD, XRP/USD
• 🌏 Асъорҳои минтақавӣ: USD/CNH, USD/INR, USD/TRY

        📱 *Дастгирӣ ва алоқа:*
• 💬 Дастгирӣ 24/7: @tradeporu
• 🌐 Сомона: TRADEPO\.RU

        ⭐️ *Барои оғоз забони дилхоҳро интихоб кунед:* 👇""",
        'ANALYZING': "⏳ Дар ҳоли таҳлил\.\.\.",
        'CURRENT_PRICE': "Нарх",
        'EXPIRATION': "Вақти амал",
        'CONFIDENCE': "Боварӣ",
        'MINUTES': "дақиқа",
        'TIMEFRAME': "Сигнал дар {} мин",
        'SIGNALS': {
            'BUY': '⬆️⬆️⬆️ *БОЛО* ⬆️⬆️⬆️\n💹 _Нишондиҳандаҳои техникӣ афзоишро нишон медиҳанд_',
            'SELL': '⬇️⬇️⬇️ *ПОЁН* ⬇️⬇️⬇️\n💢 _Нишондиҳандаҳои техникӣ камшавиро нишон медиҳанд_',
            'NEUTRAL': '↔️↔️↔️ *СИГНАЛ НЕСТ* ↔️↔️↔️\n⚖️ _Дар ин лаҳза тамоюли возеҳ нест_'
        },
        'PAIR_HEADER': "💎 *Ҷуфти асъор:* *{}*",
        'ERRORS': {
            'NO_DATA': "❌ Хатогӣ: Маълумоти бозор дастнорас аст",
            'ANALYSIS_ERROR': "❌ Хатогӣ дар таҳлили бозор",
            'GENERAL_ERROR': "❌ Хатогии техникӣ рух дод",
            'TIMEOUT_ERROR': "❌ Вақти интизорӣ ба охир расид",
            'AUTH_ERROR': "❌ Хатогӣ рух дод. Лутфан, дубора кӯшиш кунед ё ба администратор муроҷиат кунед.",
            'RETRY_ERROR': "❌ Хатогӣ рух дод. Лутфан, дубора кӯшиш кунед."
        },
        'AUTH': {
            'WELCOME': "👋 Салом! Барои истифодаи бот, лутфан, паролро ворид кунед:",
            'SUCCESS': "✅ Хуш омадед! Акнун шумо метавонед аз бот истифода баред.",
            'FAIL': "❌ Пароли нодуруст. Лутфан, такрор кунед ё ба администратор муроҷиат кунед."
        }
    },
    'ru': {
        'WELCOME': """🚀 *Добро пожаловать в продвинутый бот анализа финансовых рынков\!*
        
        📊 *Основные возможности:*
• 💹 Технический анализ для 30\+ валютных пар
• 📈 Надёжные индикаторы \(RSI, MACD, EMA\)
• ⚡️ Мгновенные сигналы с точностью до 95\%
• 📱 Поддержка 5 языков
• 📊 Чёткие и подробные графики
• ⏱ Анализ на разных интервалах \(1, 5, 15, 30 минут\)
        
        💎 *Валютные пары:*
• 🏆 Основные пары: EUR/USD, GBP/USD, USD/JPY и другие
• 🌟 Кросс\-курсы: EUR/GBP, GBP/JPY, EUR/JPY и другие
• 💰 Криптовалюты: BTC/USD, ETH/USD, XRP/USD и другие
        
        📱 *Контакты:*
• Поддержка 24/7: @tradeporu
• Сайт: TRADEPO\.RU
        
        ⚡️ *Выберите валютную пару для начала:* 👇""",
        'ANALYZING': "⏳ Анализирую\.\.\.",
        'CURRENT_PRICE': "Цена",
        'EXPIRATION': "Время экспирации",
        'CONFIDENCE': "Уверенность",
        'MINUTES': "минут",
        'TIMEFRAME': "Сигнал на {} минут",
        'SIGNALS': {
            'BUY': '⬆️⬆️⬆️ *ВВЕРХ* ⬆️⬆️⬆️\n💹 _Технические индикаторы показывают рост_',
            'SELL': '⬇️⬇️⬇️ *ВНИЗ* ⬇️⬇️⬇️\n💢 _Технические индикаторы показывают падение_',
            'NEUTRAL': '↔️↔️↔️ *НЕТ СИГНАЛА* ↔️↔️↔️\n⚖️ _Нет явного тренда_'
        },
        'PAIR_HEADER': "💎 *Валютная пара:* *{}*",
        'ERRORS': {
            'NO_DATA': "❌ Ошибка: Рыночные данные недоступны",
            'ANALYSIS_ERROR': "❌ Ошибка анализа рынка",
            'GENERAL_ERROR': "❌ Произошла техническая ошибка",
            'TIMEOUT_ERROR': "❌ Превышено время ожидания",
            'AUTH_ERROR': "❌ У вас нет доступа к боту. Пожалуйста, обратитесь к администратору."
        },
        'AUTH': {
            'WELCOME': "👋 Здравствуйте! Для использования бота, пожалуйста, введите пароль:",
            'SUCCESS': "✅ Добро пожаловать! Теперь вы можете использовать бота.",
            'FAIL': "❌ Неверный пароль. Пожалуйста, попробуйте снова или обратитесь к администратору."
        }
    },
    'uz': {
        'WELCOME': """🚀 *Moliyaviy bozorlarni tahlil qiluvchi ilg'or botga xush kelibsiz\!*
        
        📊 *Asosiy imkoniyatlar:*
• 💹 30\+ valyuta jufti uchun texnik tahlil
• 📈 Ishonchli indikatorlar \(RSI, MACD, EMA\)
• ⚡️ 95\% aniqlikkacha bo'lgan tezkor signallar
• 📱 5 til qo'llab\-quvvatlash
• 📊 Aniq va batafsil grafiklar
• ⏱ Turli intervallarda tahlil \(1, 5, 15, 30 daqiqa\)
        
        💎 *Valyuta juftlari:*
• 🏆 Asosiy juftlar: EUR/USD, GBP/USD, USD/JPY va boshqalar
• 🌟 Kross\-kurslar: EUR/GBP, GBP/JPY, EUR/JPY va boshqalar
• 💰 Kriptovalyutalar: BTC/USD, ETH/USD, XRP/USD va boshqalar
        
        📱 *Aloqa:*
• 24/7 Qo'llab\-quvvatlash: @tradeporu
• Sayt: TRADEPO\.RU
        
        ⚡️ *Boshlash uchun valyuta juftini tanlang:* 👇""",
        'ANALYZING': "⏳ Tahlil qilinmoqda\.\.\.",
        'CURRENT_PRICE': "Narx",
        'EXPIRATION': "Amal vaqti",
        'CONFIDENCE': "Ishonch",
        'MINUTES': "daqiqa",
        'TIMEFRAME': "Signal {} daqiqada",
        'SIGNALS': {
            'BUY': '⬆️⬆️⬆️ *YUQORIGA* ⬆️⬆️⬆️\n💹 _Texnik ko\'rsatkichlar o\'sishni ko\'rsatmoqda_',
            'SELL': '⬇️⬇️⬇️ *PASTGA* ⬇️⬇️⬇️\n💢 _Texnik ko\'rsatkichlar tushishni ko\'rsatmoqda_',
            'NEUTRAL': '↔️↔️↔️ *SIGNAL YO\'Q* ↔️↔️↔️\n⚖️ _Aniq trend yo\'q_'
        },
        'PAIR_HEADER': "💎 *Valyuta jufti:* *{}*",
        'ERRORS': {
            'NO_DATA': "❌ Xato: Bozor ma'lumotlari mavjud emas",
            'ANALYSIS_ERROR': "❌ Bozorni tahlil qilishda xato",
            'GENERAL_ERROR': "❌ Texnik xato yuz berdi",
            'TIMEOUT_ERROR': "❌ Kutish vaqti tugadi",
            'AUTH_ERROR': "❌ Botdan foydalanish uchun ruxsatingiz yo'q. Iltimos, administratorga murojaat qiling."
        },
        'AUTH': {
            'WELCOME': "👋 Salom! Botdan foydalanish uchun, iltimos, parolni kiriting:",
            'SUCCESS': "✅ Xush kelibsiz! Endi siz botdan foydalanishingiz mumkin.",
            'FAIL': "❌ Noto'g'ri parol. Iltimos, qayta urinib ko'ring yoki administratorga murojaat qiling."
        }
    },
    'kk': {
        'WELCOME': """🚀 *Қаржы нарықтарын талдайтын озық ботқа қош келдіңіз\!*
        
        📊 *Негізгі мүмкіндіктер:*
• 💹 30\+ валюта жұбы үшін техникалық талдау
• 📈 Сенімді индикаторлар \(RSI, MACD, EMA\)
• ⚡️ 95\% дәлдікке дейінгі жылдам сигналдар
• 📱 5 тілді қолдау
• 📊 Нақты және егжей\-тегжейлі графиктер
• ⏱ Әртүрлі интервалдарда талдау \(1, 5, 15, 30 минут\)
        
        💎 *Валюта жұптары:*
• 🏆 Негізгі жұптар: EUR/USD, GBP/USD, USD/JPY және басқалар
• 🌟 Кросс\-бағамдар: EUR/GBP, GBP/JPY, EUR/JPY және басқалар
• 💰 Криптовалюталар: BTC/USD, ETH/USD, XRP/USD және басқалар
        
        📱 *Байланыс:*
• 24/7 Қолдау: @tradeporu
• Сайт: TRADEPO\.RU
        
        ⚡️ *Бастау үшін валюта жұбын таңдаңыз:* 👇""",
        'ANALYZING': "⏳ Талдау жүргізілуде\.\.\.",
        'CURRENT_PRICE': "Баға",
        'EXPIRATION': "Әрекет уақыты",
        'CONFIDENCE': "Сенімділік",
        'MINUTES': "минут",
        'TIMEFRAME': "Сигнал {} минутта",
        'SIGNALS': {
            'BUY': '⬆️⬆️⬆️ *ЖОҒАРЫ* ⬆️⬆️⬆️\n💹 _Техникалық индикаторлар өсуді көрсетеді_',
            'SELL': '⬇️⬇️⬇️ *ТӨМЕН* ⬇️⬇️⬇️\n💢 _Техникалық индикаторлар түсуді көрсетеді_',
            'NEUTRAL': '↔️↔️↔️ *СИГНАЛ ЖОҚ* ↔️↔️↔️\n⚖️ _Нақты тренд жоқ_'
        },
        'PAIR_HEADER': "💎 *Валюта жұбы:* *{}*",
        'ERRORS': {
            'NO_DATA': "❌ Қате: Нарық деректері қол жетімді емес",
            'ANALYSIS_ERROR': "❌ Нарықты талдау кезінде қате",
            'GENERAL_ERROR': "❌ Техникалық қате орын алды",
            'TIMEOUT_ERROR': "❌ Күту уақыты аяқталды",
            'AUTH_ERROR': "❌ Сізде ботты пайдалануға рұқсат жоқ. Әкімшіге хабарласыңыз."
        },
        'AUTH': {
            'WELCOME': "👋 Сәлем! Ботты пайдалану үшін құпия сөзді енгізіңіз:",
            'SUCCESS': "✅ Қош келдіңіз! Енді сіз ботты пайдалана аласыз.",
            'FAIL': "❌ Қате құпия сөз. Қайта көріңіз немесе әкімшіге хабарласыңыз."
        }
    },
    'en': {
        'WELCOME': """🚀 *Welcome to the advanced financial markets analysis bot\!*
        
        📊 *Key Features:*
• 💹 Technical analysis for 30\+ currency pairs
• 📈 Reliable indicators \(RSI, MACD, EMA\)
• ⚡️ Instant signals with up to 95\% accuracy
• 📱 5 language support
• 📊 Clear and detailed charts
• ⏱ Analysis at different intervals \(1, 5, 15, 30 minutes\)
        
        💎 *Currency Pairs:*
• 🏆 Major pairs: EUR/USD, GBP/USD, USD/JPY and others
• 🌟 Cross rates: EUR/GBP, GBP/JPY, EUR/JPY and others
• 💰 Cryptocurrencies: BTC/USD, ETH/USD, XRP/USD and others
        
        📱 *Contact:*
• 24/7 Support: @tradeporu
• Website: TRADEPO\.RU
        
        ⚡️ *Select a currency pair to begin:* 👇""",
        'ANALYZING': "⏳ Analyzing\.\.\.",
        'CURRENT_PRICE': "Price",
        'EXPIRATION': "Expiration time",
        'CONFIDENCE': "Confidence",
        'MINUTES': "minutes",
        'TIMEFRAME': "Signal for {} min",
        'SIGNALS': {
            'BUY': '⬆️⬆️⬆️ *UPWARD* ⬆️⬆️⬆️\n💹 _Technical indicators show growth_',
            'SELL': '⬇️⬇️⬇️ *DOWNWARD* ⬇️⬇️⬇️\n💢 _Technical indicators show decline_',
            'NEUTRAL': '↔️↔️↔️ *NO SIGNAL* ↔️↔️↔️\n⚖️ _No clear trend_'
        },
        'PAIR_HEADER': "💎 *Currency pair:* *{}*",
        'ERRORS': {
            'NO_DATA': "❌ Error: Market data unavailable",
            'ANALYSIS_ERROR': "❌ Market analysis error",
            'GENERAL_ERROR': "❌ Technical error occurred",
            'TIMEOUT_ERROR': "❌ Request timeout",
            'AUTH_ERROR': "❌ You don't have access to the bot. Please contact the administrator."
        },
        'AUTH': {
            'WELCOME': "👋 Hello! To use the bot, please enter the password:",
            'SUCCESS': "✅ Welcome! You can now use the bot.",
            'FAIL': "❌ Incorrect password. Please try again or contact the administrator."
        }
    }
}