import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Chip,
  Grid,
  Card,
  CardContent,
  Alert,
  Divider,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Speed as SpeedIcon,
  Token as TokenIcon,
  Highlight as HighlightIcon,
} from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';

interface TokenizationResult {
  originalText: string;
  tokens: string[];
  wordBoundaries: number[];
  compoundsFound: string[];
  processingTime: number;
  engine: string;
}

const sampleTexts = [
  'วากาเมะมีประโยชน์ต่อสุขภาพ',
  'สาหร่ายวากาเมะเป็นอาหารทะเลที่มีประโยชน์',
  'ร้านอาหารญี่ปุ่นเสิร์ฟซาชิมิและเทมปุระ',
  'คอมพิวเตอร์และอินเทอร์เน็ตเป็นเทคโนโลยีสำคัญ',
  'สลัดสาหร่ายวากาเมะแบบญี่ปุ่นรสชาติดี',
];

export default function TestInterface() {
  const [inputText, setInputText] = useState('วากาเมะมีประโยชน์ต่อสุขภาพ');
  const [result, setResult] = useState<TokenizationResult | null>(null);

  // Mock tokenization API call
  const tokenizeMutation = useMutation({
    mutationFn: async (text: string): Promise<TokenizationResult> => {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 200));
      
      // Mock tokenization logic - in reality this would call your API
      const mockResult: TokenizationResult = {
        originalText: text,
        tokens: text === 'วากาเมะมีประโยชน์ต่อสุขภาพ' 
          ? ['วากาเมะ', 'มีประโยชน์', 'ต่อ', 'สุขภาพ']
          : text.split(''),
        wordBoundaries: [0, 7, 17, 20, 26],
        compoundsFound: text.includes('วากาเมะ') ? ['วากาเมะ'] : [],
        processingTime: Math.random() * 10 + 1,
        engine: 'newmm_custom',
      };
      
      return mockResult;
    },
    onSuccess: (data) => {
      setResult(data);
    },
  });

  // Auto-tokenize when text changes (debounced)
  useEffect(() => {
    if (inputText.trim()) {
      const timer = setTimeout(() => {
        tokenizeMutation.mutate(inputText);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [inputText]);

  const handleSampleTextClick = (text: string) => {
    setInputText(text);
  };

  const renderHighlightedText = () => {
    if (!result) return null;

    const { originalText, tokens, compoundsFound } = result;
    let currentIndex = 0;
    const elements: React.ReactNode[] = [];

    tokens.forEach((token, index) => {
      const isCompound = compoundsFound.includes(token);
      const tokenStart = originalText.indexOf(token, currentIndex);
      
      if (tokenStart > currentIndex) {
        // Add any text between tokens
        elements.push(
          <span key={`gap-${index}`}>
            {originalText.slice(currentIndex, tokenStart)}
          </span>
        );
      }

      elements.push(
        <Chip
          key={`token-${index}`}
          label={token}
          size="small"
          color={isCompound ? 'primary' : 'default'}
          variant={isCompound ? 'filled' : 'outlined'}
          sx={{ 
            m: 0.25,
            fontFamily: 'Noto Sans Thai',
            fontSize: '0.875rem',
          }}
        />
      );

      currentIndex = tokenStart + token.length;
    });

    return <Box sx={{ lineHeight: 2 }}>{elements}</Box>;
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Real-time Tokenization Testing
      </Typography>

      <Grid container spacing={3}>
        {/* Input Section */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Input Text
            </Typography>
            
            <TextField
              multiline
              rows={4}
              fullWidth
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Enter Thai text to test tokenization..."
              sx={{ mb: 2 }}
            />

            <Button
              variant="contained"
              startIcon={<PlayIcon />}
              onClick={() => tokenizeMutation.mutate(inputText)}
              disabled={!inputText.trim() || tokenizeMutation.isPending}
              sx={{ mb: 2 }}
            >
              {tokenizeMutation.isPending ? 'Tokenizing...' : 'Test Tokenization'}
            </Button>

            <Typography variant="subtitle2" gutterBottom>
              Sample Texts:
            </Typography>
            <List dense>
              {sampleTexts.map((text, index) => (
                <ListItem
                  key={index}
                  button
                  onClick={() => handleSampleTextClick(text)}
                  sx={{ 
                    border: 1, 
                    borderColor: 'divider', 
                    borderRadius: 1, 
                    mb: 0.5,
                    fontFamily: 'Noto Sans Thai',
                  }}
                >
                  <ListItemText 
                    primary={text}
                    sx={{ fontFamily: 'Noto Sans Thai' }}
                  />
                </ListItem>
              ))}
            </List>
          </Paper>
        </Grid>

        {/* Results Section */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Tokenization Results
            </Typography>

            {tokenizeMutation.isError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                Failed to tokenize text. Please try again.
              </Alert>
            )}

            {result && (
              <Box>
                {/* Performance Metrics */}
                <Grid container spacing={2} sx={{ mb: 3 }}>
                  <Grid item xs={4}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center', py: 1 }}>
                        <TokenIcon color="primary" />
                        <Typography variant="h6">
                          {result.tokens.length}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Tokens
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={4}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center', py: 1 }}>
                        <SpeedIcon color="primary" />
                        <Typography variant="h6">
                          {result.processingTime.toFixed(1)}ms
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Processing Time
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={4}>
                    <Card variant="outlined">
                      <CardContent sx={{ textAlign: 'center', py: 1 }}>
                        <HighlightIcon color="primary" />
                        <Typography variant="h6">
                          {result.compoundsFound.length}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Compounds
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>

                <Divider sx={{ my: 2 }} />

                {/* Highlighted Tokens */}
                <Typography variant="subtitle2" gutterBottom>
                  Tokenized Output:
                </Typography>
                <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                  {renderHighlightedText()}
                </Box>

                {/* Compound Words Found */}
                {result.compoundsFound.length > 0 && (
                  <>
                    <Typography variant="subtitle2" gutterBottom>
                      Compound Words Detected:
                    </Typography>
                    <Box sx={{ mb: 2 }}>
                      {result.compoundsFound.map((compound, index) => (
                        <Chip
                          key={index}
                          label={compound}
                          color="primary"
                          sx={{ 
                            m: 0.5,
                            fontFamily: 'Noto Sans Thai',
                          }}
                        />
                      ))}
                    </Box>
                  </>
                )}

                {/* Raw Token List */}
                <Typography variant="subtitle2" gutterBottom>
                  Raw Tokens:
                </Typography>
                <Box sx={{ 
                  p: 2, 
                  bgcolor: 'grey.100', 
                  borderRadius: 1,
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                }}>
                  {JSON.stringify(result.tokens, null, 2)}
                </Box>

                {/* Engine Info */}
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  Engine: {result.engine}
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}