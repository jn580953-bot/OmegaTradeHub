OmegaTradeHub
============= 

OmegaTradeHub is a mobile-friendly digit trading platform concept inspired by synthetic-index trading interfaces.

This scaffold provides a clean starting point for the project with:

- a responsive dark trading dashboard
- demo-style digit trading logic
- protected environment variable guidance
- admin dashboard placeholders
- a Flask backend with API endpoints for market and simulated trades

Important security and product notes
------------------------------------

- Live trading is intentionally disabled in this scaffold.
- No payment PINs, API tokens, or secret keys are stored in public source code.
- Demo balances are separate from any future live-account implementation.
- Provider verification and legal/compliance review must happen before enabling live trading.

Local development
-----------------

1. Create a virtual environment:
   python -m venv .venv
   source .venv/bin/activate

2. Install dependencies:
   pip install -r requirements.txt

3. Copy environment example:
   cp .env.example .env

4. Run the app:
   python app.py

5. Open the app in a browser:
   http://localhost:5000

Project structure
-----------------

- app.py: Flask application and demo endpoints
- templates/index.html: dashboard markup
- static/css/style.css: dark trading UI styling
- static/js/app.js: chart rendering and trading interactions
- .env.example: environment variable template
- requirements.txt: Python dependencies

Next milestones
--------------

- implement persistent user accounts and database storage
- add secure registration/login flow
- build proper market simulation and chart history
- implement PostgreSQL or SQLite data persistence
- prepare provider verification checklist for future live integration
