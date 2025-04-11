import os
import time
import logging
import threading
from datetime import datetime
from flask import Flask, jsonify
import psutil
import requests

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('keep_alive.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_port_in_use(port):
    """Check if port is already in use"""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if hasattr(conn.laddr, 'port') and conn.laddr.port == port:
                return True
    except Exception as e:
        logger.error(f"Error checking port: {e}")
    return False

def kill_process_on_port(port):
    """Kill process using specified port"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                connections = proc.connections(kind='inet')
                for conn in connections:
                    if hasattr(conn.laddr, 'port') and conn.laddr.port == port:
                        proc.terminate()
                        logger.info(f"Terminated process {proc.pid} using port {port}")
                        proc.wait(timeout=3)
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
    return False

@app.route('/health')
def health_check():
    """Health check endpoint"""
    logger.info("Health check request received")
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route('/')
def home():
    bot_pid = check_bot_process()
    bot_health = check_bot_health() if bot_pid else False
    status = "✅ Bot is running and healthy" if bot_health else "⚠️ Bot is running but not responding" if bot_pid else "❌ Bot is not running"

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # Convert to MB

    return f"""
    <html>
    <head>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="60">
        <title>Bot Status Monitor</title>
        <style>
            body {{ 
                background-color: #1a1b26; 
                color: white; 
                font-family: Arial, sans-serif; 
                padding: 20px;
                max-width: 800px;
                margin: 0 auto;
            }}
            .status-card {{
                background-color: #24283b;
                padding: 20px;
                border-radius: 10px;
                margin: 10px 0;
            }}
            .metric {{
                display: flex;
                justify-content: space-between;
                padding: 10px 0;
                border-bottom: 1px solid #414868;
            }}
            .metric:last-child {{
                border-bottom: none;
            }}
        </style>
    </head>
    <body>
        <h1>Bot Status Monitor</h1>
        <div class="status-card">
            <div class="metric">
                <span>Status:</span>
                <span>{status}</span>
            </div>
            <div class="metric">
                <span>Current Time:</span>
                <span>{current_time}</span>
            </div>
            <div class="metric">
                <span>Server Uptime:</span>
                <span>{time.time() - psutil.boot_time():.0f} seconds</span>
            </div>
            <div class="metric">
                <span>Memory Usage:</span>
                <span>{memory_usage:.1f} MB</span>
            </div>
        </div>
    </body>
    </html>
    """

def check_bot_process():
    """Check if the bot process is running"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'python' in proc.info['name'].lower() and 'bot.py' in cmdline:
                    return proc.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"Error checking bot process: {e}")
    return None

def check_bot_health():
    """Check if the bot is responding to Telegram"""
    try:
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment variables")
            return False

        response = requests.get(f'https://api.telegram.org/bot{bot_token}/getMe', timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Bot health check failed: {e}")
        return False

def monitor_bot():
    """Monitor bot health and restart if needed"""
    while True:
        try:
            bot_pid = check_bot_process()
            bot_healthy = check_bot_health() if bot_pid else False

            if not bot_healthy:
                logger.warning("Bot is not healthy, attempting to restart")
                if bot_pid:
                    try:
                        proc = psutil.Process(bot_pid)
                        proc.terminate()
                        proc.wait(timeout=3)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                        pass

                # Start bot process
                logger.info("Starting bot process...")
                os.system('python bot.py &')
                logger.info("Bot restarted")

            time.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Error in monitor thread: {e}")
            time.sleep(60)

def run():
    """Run the Flask server"""
    # Check for environment variable PORT first
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Using port {port} from environment")

    # Log network interfaces
    logger.info("Available network interfaces:")
    try:
        import socket
        interfaces = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET)
        for interface in interfaces:
            logger.info(f"Interface: {interface}")
    except Exception as e:
        logger.error(f"Error getting network interfaces: {e}")

    retries = 3

    # First, ensure the port is free
    if check_port_in_use(port):
        logger.warning(f"Port {port} is in use, attempting to free it")
        kill_process_on_port(port)
        time.sleep(2)  # Wait for port to be fully released

    for attempt in range(retries):
        try:
            logger.info(f"Starting Flask server on port {port} (attempt {attempt + 1})")
            logger.info("About to call app.run()...")

            app.run(
                host='0.0.0.0',
                port=port,
                threaded=True,
                debug=False
            )

            logger.info("Flask server started successfully")
            return

        except Exception as e:
            logger.error(f"Failed to start server (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                logger.critical("Failed to start server after all retries")
                raise

def keep_alive():
    """Start the Flask server and monitoring in background threads"""
    try:
        logger.info("Starting keep-alive server and monitoring")

        # Start the Flask server in a separate thread
        server_thread = threading.Thread(target=run)
        server_thread.daemon = True
        server_thread.start()

        # Start the monitoring in another thread
        monitor_thread = threading.Thread(target=monitor_bot)
        monitor_thread.daemon = True
        monitor_thread.start()

        logger.info("Keep-alive server and monitoring started successfully")
    except Exception as e:
        logger.error(f"Error in keep_alive: {e}")
        raise

if __name__ == "__main__":
    keep_alive()