from setuptools import setup, find_packages

setup(
    name="forex-analysis-bot",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'python-telegram-bot>=20.7',
        'yfinance>=0.2.33',
        'pandas>=2.1.3',
        'numpy>=1.26.2',
        'psycopg2-binary>=2.9.9',
        'Flask>=3.0.0',
        'Werkzeug>=3.0.1',
        'psutil>=5.9.6',
        'requests>=2.31.0',
        'python-dotenv>=1.0.0',
        'matplotlib>=3.10.1',
    ],
    python_requires='>=3.9',
)