# API

## Overview

PersonalAI exposes a local JSON API used by the React frontend and other local tools.

## Primary Routes

- `POST /api/ask`
- `POST /api/auto-route`
- `POST /api/auto-run`
- `POST /api/implementation-scope`
- `POST /api/agent-runtime`
- `POST /api/agent-task-plan`
- `POST /api/analyze-dir`
- `POST /api/draft-note`
- `GET /api/models`
- `GET /api/history`
- `GET /api/ask-history`
- `GET /api/agent-history`
- `GET /api/history-overview`
- `POST /api/reload`

## Error Contract

Production-safe behavior:

- client validation errors return explicit `400` responses
- unexpected server errors return a stable internal-error payload
- detailed stack traces remain in backend logs unless debug mode is enabled

## Notes

- the API is intended for local-first usage
- health and runtime diagnostics are exposed through the backend/runtime shell
- advanced request routing is handled server-side rather than manually in the UI
