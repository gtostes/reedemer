1. Instale dependencias

cd reedem-service
npm install

2. Crie o ambiente

python -m venv venv
source venv/bin/activate
pip install requests py-clob-client python-dotenv

3. Rode o loop

cd ..
python3 loop.py
