import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import DictionaryManager from './pages/DictionaryManager';
import TestInterface from './pages/TestInterface';
import Analytics from './pages/Analytics';
import ImportExport from './pages/ImportExport';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Noto Sans Thai", sans-serif',
  },
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <Box sx={{ display: 'flex', minHeight: '100vh' }}>
            <Sidebar />
            <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
              <Header />
              <Box component="main" sx={{ flexGrow: 1, p: 3, bgcolor: 'grey.50' }}>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/dictionary" element={<DictionaryManager />} />
                  <Route path="/test" element={<TestInterface />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/import-export" element={<ImportExport />} />
                </Routes>
              </Box>
            </Box>
          </Box>
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;