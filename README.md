Arb Finder upgraded for live odds and Telegram alerts

Quick start
1. pip install -r requirements.txt
2. python main.py  (mock mode, sends a Telegram DM)

Live mode
Edit config.yaml and set use_mock_data: false, then run python main.py
It will scan every 60 seconds and DM you on edges at or above 1 percent


Cloud deploy quick start
Option A on Render
1. Create a new private GitHub repo and push these files
2. Go to Render and create a new Worker from your repo
3. Use Docker as the environment so the Dockerfile runs python main.py
4. Edit config.yaml in the repo to set use_mock_data: false
5. Deploy. The worker will run forever and send Telegram alerts

Option B on Railway
1. Install the Railway CLI
2. Run railway init in this folder to create a project
3. Run railway up to build and deploy the Dockerfile
4. Make sure config.yaml has use_mock_data: false before deploy
