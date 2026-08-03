# API Contract: Football Match Manager

This document defines the RESTful API endpoints for the Football Match Manager backend.

## Base URL
`/api/v1`

## Authentication
All endpoints (except auth endpoints) require a valid JWT token in the Authorization header:
```
Authorization: Bearer <token>
```

## Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and receive JWT token
- `POST /auth/logout` - logout (client-side token removal)

### Matches
- `GET /matches` - Get list of matches with optional filtering
  - Query Parameters:
    - `leagueId` (UUID): Filter by league
    - `dateFrom` (ISO string): Matches on or after this date
    - `dateTo` (ISO string): Matches on or before this date
    - `status` (string): Filter by status (upcoming, live, finished)
    - `search` (string): Search by team name (home or away)
    - `page` (int): Page number for pagination (default: 1)
    - `limit` (int): Items per page (default: 20)...
- `GET /matches/:id` - Get a specific match by ID
- `GET /matches/:id/followers` - Get users following a specific match (requires auth)

### User Follows
- `POST /follows` - Follow a match
  - Body: `{ "matchId": "uuid" }`
- `DELETE /follows/:matchId` - Unfollow a match
- `GET /follows` - Get all matches followed by the current user (requires auth)

### Teams
- `GET /teams` - Get list of teams (optional search)
  - Query Parameters:
    - `search` (string): Search by team name
    - `limit` (int): Limit results (default: 50)

### Leagues
- `GET /leagues` - Get list of leagues
  - Query Parameters:
    - `country` (string): Filter by country
    - `active` (boolean): Filter by active leagues

## Data Models

### Match
```json
{
  "id": "uuid",
  "homeTeam": {
    "id": "uuid",
    "name": "string",
    "abbreviation": "string",
    "crestUrl": "url"
  },
  "awayTeam": {
    "id": "uuid",
    "name": "string",
    "abbreviation": "string",
    "crestUrl": "url"
  },
  "dateTime": "ISO string",
  "venue": "string",
  "league": {
    "id": "uuid",
    "name": "string",
    "country": "string"
  },
  "status": "upcoming|live|finished|postponed|cancelled",
  "homeScore": "integer (nullable)",
  "awayScore": "integer (nullable)",
  "lastUpdated": "ISO string"
}
```

### Team
```json
{
  "id": "uuid",
  "name": "string",
  "abbreviation": "string",
  "crestUrl": "url",
  "foundedYear": "integer"
}
```

### League
```json
{
  "id": "uuid",
  "name": "string",
  "sport": "string",
  "country": "string",
  "logoUrl": "url",
  "currentSeason": "string"
}
```

### User (authenticated user only)
```json
{
  "id": "uuid",
  "email": "string",
  "displayName": "string",
  "avatarUrl": "url"
}
```

### Follow Response
```json
{
  "userId": "uuid",
  "matchId": "uuid",
  "followedAt": "ISO string",
  "notificationsEnabled": "boolean"
}
```

## Error Responses
All endpoints return appropriate HTTP status codes:
- 200: Success
- 201: Created
- 400: Bad Request (validation error)
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Too Many Requests (rate limiting)
- 500: Internal Server Error

Error response body:
```json
{
  "error": "string",
  "message": "string",
  "details": "object (optional)"
}
```

## Rate Limiting
- Auth endpoints: 5 requests per minute per IP
- All other endpoints: 60 requests per minute per user

## Versioning
API version is included in the URL path (`/api/v1/`). Breaking changes will increment the version number.