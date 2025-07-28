# Thai Tokenizer Admin Frontend

A modern, responsive web application for managing Thai compound words in the tokenizer system. Built with Next.js 15, TypeScript, Tailwind CSS v4.x, and ShadCN/UI.

## Features

- 🚀 **Next.js 15** with App Router for modern React development
- 🎨 **Tailwind CSS v4.x** for utility-first styling
- 🧩 **ShadCN/UI** components built on Radix UI primitives
- 📱 **Responsive design** that works on all devices
- 🌙 **Dark/Light mode** with system preference detection
- 🔍 **Real-time search** and filtering capabilities
- 📊 **Analytics dashboard** with interactive charts
- 🔐 **Role-based access control** (Admin, Editor, Viewer)
- 🌐 **Thai language support** with proper font rendering
- ⚡ **Performance optimized** with code splitting and caching

## Technology Stack

- **Framework**: Next.js 15 with TypeScript
- **Styling**: Tailwind CSS v4.x
- **Components**: ShadCN/UI + Radix UI
- **State Management**: TanStack Query v5
- **Forms**: React Hook Form + Zod validation
- **Charts**: Recharts
- **Animations**: Framer Motion
- **Theme**: next-themes
- **Icons**: Lucide React

## Getting Started

### Prerequisites

- Node.js 18.17.0 or later
- npm, yarn, or pnpm

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd admin-frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
# or
pnpm install
```

3. Create environment variables:
```bash
cp .env.example .env.local
```

4. Start the development server:
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
admin-frontend/
├── src/
│   ├── app/                 # Next.js App Router pages
│   │   ├── dashboard/       # Dashboard page
│   │   ├── globals.css      # Global styles
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Home page
│   ├── components/          # Reusable components
│   │   ├── ui/              # ShadCN/UI components
│   │   ├── theme-provider.tsx
│   │   └── query-provider.tsx
│   ├── lib/                 # Utility functions
│   │   └── utils.ts         # Common utilities
│   └── types/               # TypeScript type definitions
│       └── index.ts         # Main types
├── public/                  # Static assets
├── tailwind.config.ts       # Tailwind configuration
├── next.config.js           # Next.js configuration
├── tsconfig.json            # TypeScript configuration
└── package.json             # Dependencies and scripts
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript type checking
- `npm run test` - Run tests
- `npm run test:watch` - Run tests in watch mode
- `npm run test:coverage` - Run tests with coverage

## Environment Variables

Create a `.env.local` file with the following variables:

```env
# API Configuration
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
API_BASE_URL=http://localhost:8000

# Authentication
NEXTAUTH_SECRET=your-secret-key
NEXTAUTH_URL=http://localhost:3000

# Database (if using local database)
DATABASE_URL=sqlite:./admin.db
```

## Development Guidelines

### Code Style

- Use TypeScript for all new code
- Follow the existing ESLint and Prettier configuration
- Use ShadCN/UI components when possible
- Implement proper error handling and loading states
- Write meaningful commit messages

### Component Structure

- Use functional components with hooks
- Implement proper TypeScript interfaces
- Use Tailwind CSS for styling
- Follow the ShadCN/UI patterns for consistency

### API Integration

- Use TanStack Query for data fetching
- Implement proper error handling
- Use optimistic updates where appropriate
- Cache responses appropriately

## Deployment

### Production Build

```bash
npm run build
npm run start
```

### Docker Deployment

```bash
docker build -t thai-tokenizer-admin .
docker run -p 3000:3000 thai-tokenizer-admin
```

### Vercel Deployment

The app is optimized for deployment on Vercel:

```bash
npm install -g vercel
vercel
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes and commit: `git commit -m 'Add new feature'`
4. Push to the branch: `git push origin feature/new-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please contact the development team or create an issue in the repository.