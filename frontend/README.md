# OpenConvert frontend

React and Vite frontend for the OpenConvert conversion API.

## Development

```bash
npm install
npm run dev
```

The development server expects the API to be available at `/api/v1`. For Docker Compose, nginx proxies `/api/` and `/health` to the API service.

## Validation

```bash
npm run build
npm run lint
```
