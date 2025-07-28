# Thai Tokenizer Admin Frontend

A modern React-based admin interface for managing Thai compound words in the tokenizer system.

## 🎯 Features

### ✅ **Dictionary Management**
- **Visual Interface**: Browse, search, and filter compound words
- **Real-time Editing**: Add, edit, and delete compounds with instant validation
- **Category Organization**: Organize words by Thai-Japanese, Thai-English, etc.
- **Usage Analytics**: See how often each compound is used in tokenization

### ✅ **Live Testing Interface**
- **Real-time Tokenization**: Test text and see results instantly
- **Compound Highlighting**: Visual indication of preserved compound words
- **Performance Metrics**: Processing time and token count display
- **Sample Templates**: Pre-built test cases for common scenarios

### ✅ **Analytics Dashboard**
- **Usage Trends**: Charts showing compound word usage over time
- **Performance Monitoring**: Response times and error rates
- **Popular Compounds**: Most/least used compound words
- **System Health**: Real-time status of tokenizer services

### ✅ **Import/Export Tools**
- **Bulk Import**: Upload CSV, JSON, or Excel files with compound words
- **Validation Preview**: See import errors before committing changes
- **Multiple Export Formats**: Download dictionaries in various formats
- **Backup Management**: Automated backups and restore functionality

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Thai Tokenizer API running on localhost:8000

### Installation

```bash
# Clone and setup
git clone <repository>
cd frontend-prototype

# Install dependencies
npm install

# Start development server
npm run dev
```

### Development

```bash
# Run in development mode with hot reload
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Lint code
npm run lint
```

## 🏗️ Architecture

### Technology Stack
- **React 18** with TypeScript for type safety
- **Material-UI (MUI)** for consistent, accessible components
- **React Query** for efficient API state management
- **React Router** for client-side routing
- **Recharts** for analytics visualization

### Project Structure
```
src/
├── components/          # Reusable UI components
│   ├── Sidebar.tsx     # Navigation sidebar
│   ├── Header.tsx      # Top header with user menu
│   └── ...
├── pages/              # Main application pages
│   ├── Dashboard.tsx   # Overview and statistics
│   ├── DictionaryManager.tsx  # Compound word management
│   ├── TestInterface.tsx      # Real-time testing
│   ├── Analytics.tsx   # Usage analytics
│   └── ImportExport.tsx       # Bulk operations
├── hooks/              # Custom React hooks
├── services/           # API integration
├── types/              # TypeScript type definitions
└── utils/              # Helper functions
```

## 🔧 Configuration

### Environment Variables
```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws

# Authentication
VITE_AUTH_ENABLED=true
VITE_JWT_SECRET=your-secret-key

# Features
VITE_ANALYTICS_ENABLED=true
VITE_IMPORT_EXPORT_ENABLED=true
```

### API Integration
The frontend integrates with the existing Thai Tokenizer API:

```typescript
// Example API calls
const api = {
  // Dictionary management
  getCompounds: () => GET('/admin/compounds'),
  addCompound: (word) => POST('/admin/compounds', word),
  updateCompound: (id, word) => PUT(`/admin/compounds/${id}`, word),
  deleteCompound: (id) => DELETE(`/admin/compounds/${id}`),
  
  // Testing
  testTokenization: (text) => POST('/admin/compounds/test', { text }),
  
  // Analytics
  getUsageStats: () => GET('/admin/analytics/usage'),
  getPerformanceMetrics: () => GET('/admin/analytics/performance'),
};
```

## 📱 User Interface

### Dashboard
- **Overview Cards**: Total compounds, categories, recent activity
- **Quick Actions**: Add compound, run test, view analytics
- **System Status**: Health indicators for all services
- **Recent Activity**: Log of recent changes and usage

### Dictionary Manager
- **Searchable Table**: Filter by word, category, usage count
- **Inline Editing**: Click to edit compound words directly
- **Bulk Operations**: Select multiple words for batch actions
- **Category Management**: Organize compounds by type

### Test Interface
- **Live Input**: Type text and see tokenization results instantly
- **Visual Highlighting**: Compound words highlighted in results
- **Performance Metrics**: Processing time and token count
- **Sample Templates**: Common test cases for quick testing

### Analytics
- **Usage Charts**: Trends over time with interactive graphs
- **Performance Monitoring**: Response times and error rates
- **Popular Words**: Most/least used compounds with statistics
- **Export Reports**: Download analytics data for external analysis

## 🔒 Security Features

### Authentication & Authorization
- **JWT-based Authentication**: Secure token-based login
- **Role-based Access**: Admin, Editor, Viewer permissions
- **Session Management**: Automatic token refresh and logout
- **Audit Logging**: Track all administrative actions

### Data Protection
- **Input Validation**: Client and server-side validation
- **XSS Protection**: Sanitized inputs and outputs
- **CSRF Protection**: Token-based request validation
- **Rate Limiting**: Prevent API abuse

## 🧪 Testing

### Test Coverage
- **Unit Tests**: Component logic and utility functions
- **Integration Tests**: API communication and data flow
- **E2E Tests**: Complete user workflows
- **Accessibility Tests**: WCAG compliance validation

### Running Tests
```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run E2E tests
npm run test:e2e

# Run accessibility tests
npm run test:a11y
```

## 🚀 Deployment

### Production Build
```bash
# Build optimized production bundle
npm run build

# Preview production build locally
npm run preview
```

### Docker Deployment
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Environment Setup
```bash
# Production environment variables
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_WS_URL=wss://api.yourdomain.com/ws
VITE_AUTH_ENABLED=true
VITE_ANALYTICS_ENABLED=true
```

## 📊 Performance

### Optimization Features
- **Code Splitting**: Lazy load components for faster initial load
- **Virtual Scrolling**: Handle large compound word lists efficiently
- **Debounced Search**: Optimize API calls during typing
- **Smart Caching**: React Query for intelligent data caching
- **Bundle Analysis**: Webpack bundle analyzer for size optimization

### Performance Metrics
- **Initial Load**: <2s for first meaningful paint
- **Search Response**: <200ms for compound word filtering
- **Real-time Testing**: <100ms for tokenization display
- **Bundle Size**: <500KB gzipped main bundle

## 🌐 Internationalization

### Language Support
- **Thai Interface**: Full Thai language support with proper fonts
- **English Interface**: Complete English translation
- **RTL Support**: Right-to-left text rendering for Thai
- **Locale Formatting**: Dates, numbers, and currencies

### Adding Languages
```typescript
// Add new language files
src/locales/
├── en.json     # English translations
├── th.json     # Thai translations
└── ja.json     # Japanese translations (future)
```

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and add tests
4. Run linting and tests: `npm run lint && npm test`
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open Pull Request

### Code Standards
- **TypeScript**: Strict mode enabled, no `any` types
- **ESLint**: Airbnb configuration with React hooks
- **Prettier**: Consistent code formatting
- **Conventional Commits**: Standardized commit messages

## 📞 Support

### Getting Help
- **Documentation**: Check this README and inline code comments
- **Issues**: Create GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions
- **API Docs**: Refer to Thai Tokenizer API documentation

### Common Issues
1. **API Connection**: Ensure tokenizer API is running on correct port
2. **CORS Errors**: Configure API to allow frontend origin
3. **Build Failures**: Check Node.js version and dependencies
4. **Performance**: Enable production build for testing

## 🎉 Benefits

### For Content Administrators
- **No Technical Knowledge Required**: Intuitive web interface
- **Real-time Validation**: See changes immediately
- **Bulk Operations**: Manage hundreds of compounds efficiently
- **Usage Insights**: Understand which compounds are most valuable

### For Developers
- **API Integration**: Seamless connection to existing tokenizer
- **Modern Stack**: React, TypeScript, Material-UI
- **Extensible**: Easy to add new features and customizations
- **Well-tested**: Comprehensive test coverage

### For System Administrators
- **Monitoring**: Real-time system health and performance metrics
- **Analytics**: Usage trends and optimization opportunities
- **Backup/Restore**: Automated data protection
- **Security**: Role-based access and audit logging

---

**The frontend provides a complete solution for managing Thai compound words with a modern, user-friendly interface that makes tokenizer administration accessible to non-technical users while providing powerful features for developers and system administrators.**