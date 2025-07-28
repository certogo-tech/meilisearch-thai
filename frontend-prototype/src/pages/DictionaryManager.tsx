import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface CompoundWord {
  id: string;
  word: string;
  category: string;
  components?: string[];
  confidence: number;
  usageCount: number;
  createdAt: string;
}

const mockCompounds: CompoundWord[] = [
  {
    id: '1',
    word: 'วากาเมะ',
    category: 'thai_japanese_compounds',
    components: ['วา', 'กา', 'เมะ'],
    confidence: 0.95,
    usageCount: 1247,
    createdAt: '2024-01-15',
  },
  {
    id: '2',
    word: 'สาหร่ายวากาเมะ',
    category: 'thai_japanese_compounds',
    components: ['สาหร่าย', 'วากาเมะ'],
    confidence: 0.98,
    usageCount: 892,
    createdAt: '2024-01-15',
  },
  {
    id: '3',
    word: 'ซาชิมิ',
    category: 'thai_japanese_compounds',
    confidence: 0.99,
    usageCount: 2156,
    createdAt: '2024-01-10',
  },
  {
    id: '4',
    word: 'คอมพิวเตอร์',
    category: 'thai_english_compounds',
    confidence: 0.97,
    usageCount: 5432,
    createdAt: '2024-01-08',
  },
];

const categories = [
  { value: 'thai_japanese_compounds', label: 'Thai-Japanese' },
  { value: 'thai_english_compounds', label: 'Thai-English' },
  { value: 'technical_terms', label: 'Technical Terms' },
];

export default function DictionaryManager() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [openDialog, setOpenDialog] = useState(false);
  const [editingWord, setEditingWord] = useState<CompoundWord | null>(null);
  const [newWord, setNewWord] = useState({
    word: '',
    category: '',
    components: '',
    confidence: 0.95,
  });

  const queryClient = useQueryClient();

  // Mock API calls - replace with real API
  const { data: compounds = [], isLoading } = useQuery({
    queryKey: ['compounds', searchTerm, selectedCategory],
    queryFn: async () => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500));
      return mockCompounds.filter(compound => {
        const matchesSearch = compound.word.includes(searchTerm);
        const matchesCategory = !selectedCategory || compound.category === selectedCategory;
        return matchesSearch && matchesCategory;
      });
    },
  });

  const addMutation = useMutation({
    mutationFn: async (word: any) => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      return { ...word, id: Date.now().toString(), usageCount: 0, createdAt: new Date().toISOString() };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compounds'] });
      setOpenDialog(false);
      setNewWord({ word: '', category: '', components: '', confidence: 0.95 });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 500));
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compounds'] });
    },
  });

  const handleAddWord = () => {
    addMutation.mutate({
      ...newWord,
      components: newWord.components ? newWord.components.split(',').map(c => c.trim()) : undefined,
    });
  };

  const handleDeleteWord = (id: string) => {
    if (window.confirm('Are you sure you want to delete this compound word?')) {
      deleteMutation.mutate(id);
    }
  };

  const getCategoryLabel = (category: string) => {
    return categories.find(cat => cat.value === category)?.label || category;
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dictionary Manager
      </Typography>

      {/* Controls */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <TextField
            placeholder="Search compound words..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />,
            }}
            sx={{ minWidth: 300 }}
          />
          
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Category</InputLabel>
            <Select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              label="Category"
            >
              <MenuItem value="">All Categories</MenuItem>
              {categories.map(category => (
                <MenuItem key={category.value} value={category.value}>
                  {category.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenDialog(true)}
          >
            Add Compound Word
          </Button>
        </Box>
      </Paper>

      {/* Results */}
      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Word</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Components</TableCell>
                <TableCell>Confidence</TableCell>
                <TableCell>Usage Count</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {compounds.map((compound) => (
                <TableRow key={compound.id}>
                  <TableCell>
                    <Typography variant="h6" sx={{ fontFamily: 'Noto Sans Thai' }}>
                      {compound.word}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={getCategoryLabel(compound.category)} 
                      size="small" 
                      color="primary" 
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    {compound.components ? (
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {compound.components.map((component, index) => (
                          <Chip 
                            key={index} 
                            label={component} 
                            size="small" 
                            variant="outlined"
                            sx={{ fontFamily: 'Noto Sans Thai' }}
                          />
                        ))}
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        No components
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {(compound.confidence * 100).toFixed(1)}%
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {compound.usageCount.toLocaleString()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => setEditingWord(compound)}>
                      <EditIcon />
                    </IconButton>
                    <IconButton 
                      size="small" 
                      color="error"
                      onClick={() => handleDeleteWord(compound.id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Add/Edit Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Compound Word</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField
              label="Compound Word"
              value={newWord.word}
              onChange={(e) => setNewWord({ ...newWord, word: e.target.value })}
              placeholder="e.g., วากาเมะ"
              fullWidth
              required
            />
            
            <FormControl fullWidth required>
              <InputLabel>Category</InputLabel>
              <Select
                value={newWord.category}
                onChange={(e) => setNewWord({ ...newWord, category: e.target.value })}
                label="Category"
              >
                {categories.map(category => (
                  <MenuItem key={category.value} value={category.value}>
                    {category.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="Components (optional)"
              value={newWord.components}
              onChange={(e) => setNewWord({ ...newWord, components: e.target.value })}
              placeholder="e.g., วา, กา, เมะ"
              helperText="Separate components with commas"
              fullWidth
            />

            <TextField
              label="Confidence"
              type="number"
              value={newWord.confidence}
              onChange={(e) => setNewWord({ ...newWord, confidence: parseFloat(e.target.value) })}
              inputProps={{ min: 0, max: 1, step: 0.01 }}
              fullWidth
            />

            {addMutation.isError && (
              <Alert severity="error">
                Failed to add compound word. Please try again.
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button 
            onClick={handleAddWord} 
            variant="contained"
            disabled={!newWord.word || !newWord.category || addMutation.isPending}
          >
            {addMutation.isPending ? 'Adding...' : 'Add Word'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}