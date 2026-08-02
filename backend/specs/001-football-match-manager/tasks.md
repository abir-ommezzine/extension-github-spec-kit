---

description: "Task list for Football Match Manager implementation"
---

# Tasks: Football Match Manager

**Input**: Design documents from `/specs/001-football-match-manager/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/api.md

**Tests**: Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize backend project with Node.js 18, Express.js, TypeScript 4.9 dependencies
- [ ] T003 Initialize frontend project with React 18, TypeScript dependencies
- [ ] T004 [P] Configure ESLint and Prettier for code quality
- [ ] T005 [P] Setup TypeScript configuration for backend (tsconfig.json)
- [ ] T006 [P] Setup TypeScript configuration for frontend (tsconfig.json)
- [ ] T007 [P] Configure Vite for frontend development
- [ ] [ ] T008 Create .env file for backend environment variables
- [ ] [ ] T009 Setup package.json scripts for dev, build, test
- [ ] [ ] T010 Create README.md with setup instructions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T011 Setup PostgreSQL database schema and migrations framework
- [ ] T012 [P] Create database models for Match, Team, League, User, UserFollow entities
- [ ] T013 [P] Implement database connection and configuration
- [ ] T014 [P] Setup Express.js middleware (cors, morgan, json)
- [ ] T015 [P] Create base Express app structure in backend/src/app.ts
- [ ] T016 [P] Create server entry point in backend/src/server.ts
- [ ] T017 [P] Setup JWT authentication middleware
- [ ] T018 [P] Create error handling middleware
- [ ] T019 [P] Setup API routes structure (auth, matches, follows, teams, leagues)
- [ ] T020 Create initial seed data for teams, leagues, and matches

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Viewing Match List (Priority: P1) 🎯 MVP

**Goal**: Display a list of upcoming football matches with filtering capabilities

**Independent Test**: User can view matches on the homepage and filter by league/date

### Implementation for User Story 1

- [ ] T021 [US1] Create Match model in backend/src/models/Match.ts
- [ ] T022 [US1] Create Team model in backend/src/models/Team.ts
- [ ] T023 [US1] Create League model in backend/src/models/League.ts
- [ ] [ ] T024 [US1] Implement MatchService in backend/src/services/MatchService.ts
- [ ] [ ] T025 [US1] Create GET /matches endpoint in backend/src/routes/matches.ts
- [ ] [ ] T026 [US1] Implement match filtering logic (by league, date, search)
- [ ] [ ] T027 [US1] Create MatchList component in frontend/src/components/MatchList.tsx
- [ ] [ ] T028 [US1] Create MatchCard component in frontend/src/components/MatchCard.tsx
- [ ] [ ] T029 [US1] Implement match listing in frontend/src/App.tsx
- [ ] [ ] T030 [US1] Add filter UI for league and date in frontend/src/App.tsx

**Checkpoint**: User Story 1 complete - matches can be viewed and filtered

---

## Phase 4: User Story 2 - Adding Match to Interests (Priority: P2)

**Goal**: Allow users to follow matches and mark them as interesting

**Independent Test**: User can follow a match and see it in their followed list

### Implementation for User Story 2

- [ ] T031 [US2] Create User model in backend/src/models/User.ts
- [ ] [ ] T032 [US2] Create UserFollow model in backend/src/models/UserFollow.ts
- [ ] [ ] T033 [US2] Implement AuthService in backend/src/services/AuthService.ts
- [ ] [ ] T034 [US2] Implement FollowService in backend/src/services/FollowService.ts
- [ ] [ ] T035 [US2] Create POST /follows endpoint in backend/src/routes/follows.ts
- [ ] [ ] T036 [US2] Create FollowButton component in frontend/src/components/FollowButton.tsx
- [ ] [ ] T037 [US2] Add follow functionality to MatchCard component
- [ ] [ ] T038 [US2] Implement JWT authentication in frontend
- [ ] [ ] T039 [US2] Add "Following" state management in frontend

**Checkpoint**: User Story 2 complete - users can follow matches

---

## Phase 5: User Story 3 - Removing Match from Interests (Priority: P3)

**Goal**: Allow users to unfollow matches they no longer want to track

**Independent Test**: User can unfollow a match and remove it from their list

### Implementation for User Story 3

- [ ] T040 [US3] Create DELETE /follows/:matchId endpoint in backend/src/routes/follows.ts
- [ ] [ ] T041 [US3] Implement unfollow logic in FollowService
- [ ] [ ] T042 [US3] Add unfollow functionality to FollowButton component
- [ ] [ ] T043 [US3] Update match status in UI after unfollowing
- [ ] [ ] T044 [US3] Add confirmation dialog for unfollow action

**Checkpoint**: User Story 3 complete - users can unfollow matches

---

## Phase 6: User Story 4 - Viewing Match Details (Priority: P4)

**Goal**: Display detailed information about a specific match

**Independent Test**: User can click on a match and see detailed view

### Implementation for User Story 4

- [ ] T045 [US4] Create GET /matches/:id endpoint in backend/src/routes/matches.ts
- [ ] [ ] T046 [US4] Implement match detail retrieval in MatchService
- [ ] [ ] T047 [US4] Create MatchDetail component in frontend/src/components/MatchDetail.tsx
- [ ] [ ] T048 [US4] Create match detail page/route in frontend/src/App.tsx
- [ ] [ ] T049 [US4] Display team crests, venue, league info in MatchDetail
- [ ] [ ] T050 [US4] Show match status and scores (if finished)

**Checkpoint**: User Story 4 complete - users can view match details

---

## Phase 7: User Story 5 - Viewing Followed Matches (Priority: P5)

**Goal**: Show a list of matches that the user is following

**Independent Test**: User can navigate to followed matches section

### Implementation for User Story 5

- [ ] T051 [US5] Create GET /follows endpoint in backend/src/routes/follows.ts
- [ ] [ ] T052 [US5] Implement get followed matches in FollowService
- [ ] [ ] T053 [US5] Create FollowedMatches component in frontend/src/components/FollowedMatches.tsx
- [ ] [ ] T054 [US5] Create "My Matches" page in frontend/src/App.tsx
- [ ] [ ] T055 [US5] Display followed matches with status indicators
- [ ] [ ] T056 [US5] Add navigation to followed matches page

**Checkpoint**: User Story 5 complete - users can view followed matches

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements, testing, and documentation

- [ ] T057 [P] Add unit tests for MatchService
- [ ] [ ] T058 [P] Add unit tests for FollowService
- [ ] [ ] T059 [P] Add integration tests for API endpoints
- [ ] [ ] T060 [P] Add frontend unit tests for components
- [ ] [ ] T061 [P] Implement error handling and user feedback
- [ ] [ ] T062 [P] Add loading states and spinners
- [ ] [ ] T063 [P] Implement responsive design for mobile
- [ ] [ ] T064 [P] Add accessibility attributes (ARIA labels)
- [ ] [ ] T065 [P] Create API documentation (Swagger/OpenAPI)
- [ ] [ ] T066 [P] Update README with API usage examples
- [ ] [ ] T067 [P] Add .gitignore for node_modules, .env, etc.
- [ ] [ ] T068 [P] Setup ESLint and Prettier configurations
- [ ] [ ] T069 [P] Run final code quality checks
- [ ] [ ] T070 [P] Create deployment configuration (Dockerfile, docker-compose)

---

## Dependencies

```
T001 → T002, T003, T004, T005, T006, T007, T008, T009, T010
T010 → T011, T012, T013, T014, T015, T016, T017, T018, T019, T020
T020 → T021, T022, T023, T024, T025, T026, T027, T028, T029, T030
T030 → T031, T032, T033, T034, T035, T036, T037, T038, T039
T039 → T040, T041, T042, T043, T044
T044 → T045, T046, T047, T048, T049, T050
T050 → T051, T052, T053, T054, T055, T056
T056 → T057, T058, T059, T060, T061, T062, T063, T064, T065, T066, T067, T068, T069, T070
```

---

## Parallel Execution Examples

**Phase 1** (Setup): T002, T003, T004, T005, T006, T007 can run in parallel
**Phase 2** (Foundational): T011-T020 can largely run in parallel with proper coordination
**Phase 3** (US1): T021-T023 can run in parallel, T024 depends on models, T025 depends on service

---

## Implementation Strategy

**MVP Scope**: Phase 1 + Phase 2 + Phase 3 (Viewing Match List)

This provides a working application where users can:
- View a list of football matches
- Filter matches by league and date
- See match details (teams, venue, time, league)

**Incremental Delivery**:
1. Start with Phase 1 (Setup) - establishes project foundation
2. Complete Phase 2 (Foundational) - database and API infrastructure
3. Implement Phase 3 (US1) - core user-facing feature
4. Add remaining user stories incrementally
5. Finish with Phase 8 (Polish) - testing and documentation