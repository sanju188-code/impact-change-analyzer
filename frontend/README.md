# Change Impact Analyzer

A React + Vite frontend for analyzing how a proposed software change could affect downstream services and dependencies before deployment.

## Overview

This project helps teams answer a critical pre-deployment question:

> If we make this change, which components or services are likely to be impacted, and how risky is that impact?

The app combines:

- a graph-based dependency model
- historical incident data
- LLM-assisted analysis via an OpenRouter-compatible API
- interactive risk summaries and mitigation suggestions

Users can submit a proposed change, inspect impacted components, review risk levels, and ask follow-up questions about the analysis.

## Features

- Change description input for proposed production or config updates
- Dependency graph visualization of affected components
- Risk scoring with evidence and hop-distance context
- Historical incident correlation for affected nodes
- Mitigation recommendations for medium/high/critical risks
- Follow-up Q&A based on the current analysis
- Recent analysis history for revisiting prior results

## Tech Stack

- Frontend: React, Vite, Lucide icons
- Visualization: React Force Graph
- Backend: FastAPI + Python
- AI layer: OpenAI-compatible OpenRouter client
- Data model: NetworkX graph + incident metadata

## Project Structure

```text
.
├── agent.py                 # LLM analysis and graph reasoning logic
├── app.py                   # Streamlit prototype entry point
├── data.py                  # Graph and incident data
├── db.py                    # SQLite history persistence
├── graph.py                 # Dependency graph utilities
├── main.py                  # FastAPI backend
├── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/                 # React components and app logic
│   ├── public/              # Static public assets
│   ├── package.json         # Frontend scripts and dependencies
│   ├── vite.config.js       # Vite config
│   └── README.md            # Frontend documentation
└── .env                     # Local environment variables (not committed)
```

## Prerequisites

Before running the app, make sure you have:

- Python 3.10+
- Node.js 18+
- npm
- An OpenRouter-compatible API key

## Environment Variables

Create a `.env` file in the project root with values similar to:

```env
OPENAI_ROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENAI_ROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_API_KEY=your_api_key_here
```

You can also use `OPENAI_API_KEY` as a fallback depending on how the backend is configured.

## Running the Backend

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

The backend API runs on:

```text
http://localhost:8000
```

### API endpoints

- `POST /analyze-change`
- `POST /chat`
- `GET /history`
- `GET /health`

## Running the Frontend

From the frontend folder:

```bash
cd frontend
npm install
npm run dev
```

Then open the local Vite URL shown in the terminal, usually:

```text
http://localhost:5173
```

## Typical Workflow

1. Start the backend API.
2. Start the React frontend.
3. Enter a proposed change, such as:
   - "Increase auth token expiry from 1 hour to 24 hours"
   - "Update the payment retry policy"
   - "Apply a new database failover configuration"
4. Review the impacted components and associated risks.
5. Ask follow-up questions to clarify findings and mitigation steps.

## Development Notes

This app is designed for rapid architecture review and risk assessment rather than full production deployment automation. The graph and incident model can be extended with real system topology and historical outage data as the project evolves.

## Contributing

To extend the project:

- add more dependency graph nodes and relations in the data layer
- improve risk scoring logic in the analysis backend
- refine prompts and mitigation generation for better recommendations
- expand the UI with filtering, export, and deeper graph interactions

## License

This project is currently provided as a local application for internal analysis and experimentation.
