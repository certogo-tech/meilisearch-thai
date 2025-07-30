# Thai Tokenizer Admin Frontend

A modern, responsive web application for managing Thai compound words in the tokenizer system. Built with Next.js 15, TypeScript, Tailwind CSS v4, and ShadCN/UI.

## Features

- 🚀 **Next.js 15** with App Router for modern React development
- 🎨 **Tailwind CSS v4** for utility-first styling
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
- **Styling**: Tailwind CSS v4
- **Components**: ShadCN/UI + Radix UI
- **State Management**: TanStack Query v5
- **Forms**: React Hook Form + Zod validation
- **Charts**: Recharts
- **Theme**: next-themes
- **Notifications**: Sonner

## Getting Started

### Prerequisites

- Node.js 18.17.0 or later
- npm, yarn, or pnpm

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

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
│   │   ├── query-provider.tsx
│   │   └── auth-provider.tsx
│   ├── contexts/            # React contexts
│   │   └── notification-context.tsx
│   ├── lib/                 # Utility functions
│   │   └── utils.ts         # Common utilities
│   └── types/               # TypeScript type definitions
│       └── index.ts         # Main types
├── public/                  # Static assets
├── tailwind.config.ts       # Tailwind configuration
├── next.config.ts           # Next.js configuration
├── tsconfig.json            # TypeScript configuration
└── package.json             # Dependencies and scripts
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Development Guidelines

### Code Style

- Use TypeScript for all new code
- Follow the existing ESLint configuration
- Use ShadCN/UI components when possible
- Implement proper error handling and loading states

### Component Structure

- Use functional components with hooks
- Implement proper TypeScript interfaces
- Use Tailwind CSS for styling
- Follow the ShadCN/UI patterns for consistency

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes and commit: `git commit -m 'Add new feature'`
4. Push to the branch: `git push origin feature/new-feature`
5. Submit a pull request
