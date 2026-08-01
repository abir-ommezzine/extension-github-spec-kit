# Quick Start Guide: Football Match Manager

This guide provides instructions for setting up and running the Football Match Manager application locally for development and testing purposes.

## Prerequisites

Before you begin, ensure you have the following installed on your machine:

- [Node.js](https://nodejs.org/) (v18 or later)
- [npm](https://www.npmjs.com/) (comes with Node.js) or [Yarn](https://yarnpkg.com/)
- [PostgreSQL](https://www.postgresql.org/) (v14 or later)
- [Git](https://git-scm.com/)

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd football-match-manager
```

### 2. Install Dependencies

#### Backend
```bash
cd backend
npm install
```

#### Frontend
```bash
cd ../frontend
npm install
```

### 3. Set Up the Database

1. Start your PostgreSQL server.
2. Create a new database for the application:
   ```sql
   CREATE DATABASE football_match_manager;
   ```
3. Create a user and grant privileges (optional but recommended):
   ```sql
   CREATE USER fm_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE football_match_manager TO fm_user;
   ```

### 4. Configure Environment Variables

Create a `.env` file in the `backend` directory based on the provided `.env.example`:

```bash
cd backend
cp .env.example .env
```

Edit the `.env` file to match your database configuration:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_match_manager
DB_USER=your_username
DB_PASSWORD=your_password

# JWT secret for authentication (use a strong, random string in production)
JWT_SECRET=your_super_secret_jwt_key_change_in_production

# Port for the backend server
PORT=5000

# Optional: Third-party football API key (if required by the chosen API)
FOOTBALL_API_KEY=your_api_key_here
```

### 5. Run Database Migrations

We use Sequelize for ORM and migrations. Run the following to set up the database schema:

```bash
npx sequelize-cli db:migrate
```

### 6. Seed Initial Data (Optional)

If you have seed data for leagues, teams, etc., you can run:

```bash
npx sequelize-cli db:seed:all
```

### 7. Start the Development Servers

#### Backend
```bash
# From the backend directory
npm run dev
```
The backend server will start on `http://localhost:5000` (or the port specified in your .env file).

#### Frontend
```bash
# From the frontend directory (in a new terminal)
npm start
```
The frontend development server will start on `http://localhost:3000`.

### 8. Verify the Setup

Open your browser and navigate to `http://localhost:3000`. You should see the Football Match Manager home page.

## Available Scripts

### Backend (`backend` directory)
- `npm run dev`: Start the server in development mode with auto-restart
- `npm start`: Start the server in production mode
- `npm test`: Run the test suite
- `npm run lint`: Run ESLint for code quality

### Frontend (`frontend` directory)
- `npm start`: Start the development server
- `npm run build`: Build the production bundle
- `npm test`: Run the test suite
- `npm run eject`: Eject from Create React App (use with caution)

## Testing the Application

### Running Tests

#### Backend Tests
```bash
# From the backend directory
npm test
```

#### Frontend Tests
```bash
# From the frontend directory
npm test
```

### API Documentation

Once the backend is running, you can view the API documentation at:
`http://localhost:5000/api-docs` (if Swagger/OpenAPI documentation is enabled)

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify that PostgreSQL is running
   - Check your `.env` file for correct database credentials
   - Ensure the database exists and the user has sufficient privileges

2. **Port Already in Use**
   - Another process is using the port specified in your `.env` file
   - Either change the port or stop the conflicting process

3. **Module Not Found Errors**
   - Ensure you have run `npm install` in both `backend` and `frontend` directories
   - Try deleting `node_modules` and `package-lock.json` (or `yarn.lock`) and reinstalling

4. **Authentication Issues**
   - Verify that the JWT secret is set correctly in the `.env` file
   - Ensure you are sending the token in the `Authorization` header as `Bearer <token>`

## Next Steps

After getting the application running locally, you can:

1. Explore the API endpoints using tools like Postman or curl
2. Begin implementing features based on the specification
3. Write additional tests to improve coverage
4. Prepare for deployment by setting up production environments

## Support

If you encounter any issues or have questions, please refer to the project documentation or contact the development team.