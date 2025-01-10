# AI-Powered Industrial Data Management Platform

## Overview
An advanced AI-powered platform that transforms complex work order and asset information into intelligent, interconnected databases with sophisticated diagnostic capabilities. The system processes industrial data to create meaningful insights and relationships, enabling better asset management and decision-making.

## Architecture

### Tech Stack
- **Frontend**: TypeScript + React + Vite
  - MUI (Material-UI) for component library
  - D3.js for interactive data visualization
  - Axios for API communication
  - Vitest for testing

- **Backend**: Python + Flask
  - Flask-SQLAlchemy for ORM
  - Flask-Migrate for database migrations
  - OpenAI GPT-4 integration for AI capabilities
  - Pytest for testing

- **Databases**:
  - PostgreSQL for relational data
  - Neo4j for graph relationships

### System Components

```
├── api/                 # Backend Flask application
│   ├── app.py          # Main application entry
│   ├── routes.py       # API endpoints
│   ├── models.py       # Database models
│   ├── chat_handler.py # AI chat functionality
│   └── tests/          # Backend tests
│
└── frontend/           # React frontend application
    ├── src/
    │   ├── components/ # React components
    │   ├── services/   # API services
    │   └── types/      # TypeScript types
    └── public/         # Static assets
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+
- Neo4j Database

### Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://[user]:[password]@[host]:[port]/[dbname]
PGUSER=your_pg_user
PGPASSWORD=your_pg_password
PGDATABASE=your_database
PGHOST=your_host
PGPORT=your_port

# API Keys
OPENAI_API_KEY=your_openai_api_key
```

### Installation Steps

1. Clone the repository:
```bash
git clone <repository-url>
cd repository-name
```

2. Backend Setup:
```bash
# Install Python dependencies
pip install -r requirements.txt

# Initialize database
flask db upgrade

# Start the Flask server
python app.py
```

3. Frontend Setup:
```bash
# Install Node.js dependencies
cd frontend
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Core Features

### 1. Data Management
- **CSV Processing**
  ```python
  # Example: Upload work order CSV
  POST /api/upload
  Content-Type: multipart/form-data
  file: work_orders.csv
  ```

- **Automated Entity Extraction**
  ```python
  # Example output
  {
    "entities": [
      ["Asset123", "Asset"],
      ["Facility1", "Facility"]
    ],
    "relationships": [
      {
        "source": "Asset123",
        "target": "Facility1",
        "type": "LOCATED_IN"
      }
    ]
  }
  ```

### 2. Ontology System
- **Validation Rules**
  ```typescript
  // Example rule definition
  interface Rule {
    condition: string;
    action: string;
    priority: number;
  }
  ```

- **Entity Relationship Mapping**
  ```typescript
  interface GraphNode {
    id: string;
    label: string;
    type: string;
  }

  interface GraphLink {
    source: string;
    target: string;
    type: string;
  }
  ```

### 3. AI Integration
- Natural language querying using GPT-4
- Context-aware responses
- Intelligent data analysis

### 4. Visualization
- Interactive D3.js graph visualization
- Real-time updates
- Zoom and pan capabilities
- Node and relationship filtering

## API Documentation

### Authentication
All API endpoints require valid authentication.

### Endpoints

#### File Upload
```http
POST /api/upload
Content-Type: multipart/form-data

file: CSV file containing work order data
```

Response:
```json
{
  "status": "success",
  "ontology": {
    "entities": [...],
    "relationships": [...]
  }
}
```

#### Ontology Validation
```http
POST /api/validate-ontology
Content-Type: application/json

{
  "ontology": {
    "entities": [...],
    "relationships": [...]
  }
}
```

#### Chat Interface
```http
POST /api/chat
Content-Type: application/json

{
  "query": "Show me all assets in Facility A"
}
```

## Frontend Components

### Key Components

#### FileUpload
```typescript
interface FileUploadProps {
  onProcessed: (result: any) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onProcessed }) => {
  // Component implementation
};
```

#### OntologyValidator
```typescript
interface OntologyValidatorProps {
  ontology: {
    entities: [string, string][];
    relationships: {
      source: string;
      target: string;
      type: string;
    }[];
  };
  onValidated: (graph: any) => void;
}
```

#### GraphViewer
```typescript
interface GraphViewerProps {
  graph: {
    nodes: GraphNode[];
    edges: GraphLink[];
  };
}
```

## Database Schema

### PostgreSQL Tables

#### Node
```sql
CREATE TABLE node (
    id SERIAL PRIMARY KEY,
    label VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    properties JSONB
);
```

#### Edge
```sql
CREATE TABLE edge (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES node(id),
    target_id INTEGER REFERENCES node(id),
    type VARCHAR NOT NULL,
    properties JSONB
);
```

## Development Guidelines

### Code Style
- Python: PEP 8 compliance
- TypeScript: ESLint + Prettier
- React: Functional components with hooks

### Testing

#### Backend Tests
```bash
# Run tests with coverage
pytest --cov=api

# Run specific test file
pytest api/tests/test_e2e.py
```

#### Frontend Tests
```bash
# Run all tests
npm run test

# Run with coverage
npm run test:coverage
```

### Git Workflow
1. Feature branches from main
2. Pull request review required
3. CI/CD checks must pass
4. Squash merge to main

## Deployment

### Replit Deployment
1. Fork the repository on Replit
2. Set required environment variables
3. Run the following workflows:
   - Frontend Build
   - Frontend Dev Server
   - API Server

### Production Considerations
1. Enable CORS protection
2. Set up rate limiting
3. Configure proper logging
4. Enable SSL/TLS
5. Set up monitoring


## Troubleshooting

### Common Issues

#### Database Connection
```
Error: could not connect to server: Connection refused
```
- Check PostgreSQL service status
- Verify DATABASE_URL
- Ensure database exists

#### OpenAI API
```
Error: OpenAI API key not found
```
- Set OPENAI_API_KEY environment variable
- Check API key validity
- Verify API quota

#### Frontend Build
```
Error: Type ... is not assignable to type ...
```
- Run `tsc` for type checking
- Update type definitions
- Check component props

### Performance Optimization

#### Database
- Index heavily queried columns
- Use connection pooling
- Implement query caching

#### Frontend
- Use React.memo for heavy components
- Lazy load routes
- Optimize D3.js rendering

#### API
- Cache frequent queries
- Implement rate limiting
- Use compression middleware

## Contributing

1. Fork the repository
2. Create feature branch
3. Follow code style guidelines
4. Add tests for new features
5. Create pull request

### Pull Request Requirements
- All tests must pass
- Code coverage >80%
- No TypeScript errors
- ESLint/Prettier compliance

## Support

For issues and feature requests, please create an issue in the repository.

## License

This project is proprietary and confidential.

## Version History

- v0.1.0 - Initial release
  - Basic ontology extraction
  - Graph visualization
  - Chat interface

## Acknowledgments

- OpenAI for GPT-4 API
- D3.js community
- Material-UI team