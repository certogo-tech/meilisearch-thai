import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TokenizationTestInterface } from '../tokenization-test-interface';

// Mock the debounce hook
jest.mock('@/hooks/use-debounce', () => ({
  useDebounce: (value: any) => value, // Return value immediately for testing
}));

// Mock fetch
global.fetch = jest.fn();

describe('TokenizationTestInterface', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the textarea with Thai font support', () => {
    render(<TokenizationTestInterface />);
    
    const textarea = screen.getByPlaceholderText(/Enter Thai text here to test tokenization/);
    expect(textarea).toBeInTheDocument();
    expect(textarea).toHaveClass('font-thai');
  });

  it('shows loading state when processing text', async () => {
    const mockResponse = {
      success: true,
      data: {
        originalText: 'วากาเมะ',
        tokens: [
          {
            text: 'วากาเมะ',
            startIndex: 0,
            endIndex: 7,
            isCompound: true,
            confidence: 0.95,
            category: 'thai_compound'
          }
        ],
        wordBoundaries: [0],
        compoundsFound: [
          {
            word: 'วากาเมะ',
            startIndex: 0,
            endIndex: 7,
            confidence: 0.95
          }
        ],
        processingTime: 45.2,
        engine: 'pythainlp-mock',
        confidence: 0.95
      }
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<TokenizationTestInterface />);
    
    const textarea = screen.getByPlaceholderText(/Enter Thai text here to test tokenization/);
    fireEvent.change(textarea, { target: { value: 'วากาเมะ' } });

    // Should show loading state
    expect(screen.getByText('Analyzing Thai text patterns...')).toBeInTheDocument();

    // Wait for the API call to complete
    await waitFor(() => {
      expect(screen.queryByText('Analyzing Thai text patterns...')).not.toBeInTheDocument();
    });
  });

  it('displays tokenization results with proper highlighting', async () => {
    const mockResponse = {
      success: true,
      data: {
        originalText: 'วากาเมะ ซาชิมิ',
        tokens: [
          {
            text: 'วากาเมะ',
            startIndex: 0,
            endIndex: 7,
            isCompound: true,
            confidence: 0.95,
            category: 'thai_compound'
          },
          {
            text: 'ซาชิมิ',
            startIndex: 8,
            endIndex: 14,
            isCompound: true,
            confidence: 0.88,
            category: 'thai_compound'
          }
        ],
        wordBoundaries: [0, 8],
        compoundsFound: [
          {
            word: 'วากาเมะ',
            startIndex: 0,
            endIndex: 7,
            confidence: 0.95
          },
          {
            word: 'ซาชิมิ',
            startIndex: 8,
            endIndex: 14,
            confidence: 0.88
          }
        ],
        processingTime: 52.1,
        engine: 'pythainlp-mock',
        confidence: 0.915
      }
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<TokenizationTestInterface />);
    
    const textarea = screen.getByPlaceholderText(/Enter Thai text here to test tokenization/);
    fireEvent.change(textarea, { target: { value: 'วากาเมะ ซาชิมิ' } });

    await waitFor(() => {
      expect(screen.getAllByText('วากาเมะ')).toHaveLength(2); // One in tokens, one in compounds
      expect(screen.getAllByText('ซาชิมิ')).toHaveLength(2); // One in tokens, one in compounds
    });

    // Check that compound words are highlighted
    const compoundBadges = screen.getAllByText(/95%|88%/);
    expect(compoundBadges).toHaveLength(2);
  });

  it('displays processing metrics correctly', async () => {
    const mockResponse = {
      success: true,
      data: {
        originalText: 'วากาเมะ',
        tokens: [
          {
            text: 'วากาเมะ',
            startIndex: 0,
            endIndex: 7,
            isCompound: true,
            confidence: 0.95,
            category: 'thai_compound'
          }
        ],
        wordBoundaries: [0],
        compoundsFound: [
          {
            word: 'วากาเมะ',
            startIndex: 0,
            endIndex: 7,
            confidence: 0.95
          }
        ],
        processingTime: 45.2,
        engine: 'pythainlp-mock',
        confidence: 0.95
      }
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<TokenizationTestInterface />);
    
    const textarea = screen.getByPlaceholderText(/Enter Thai text here to test tokenization/);
    fireEvent.change(textarea, { target: { value: 'วากาเมะ' } });

    await waitFor(() => {
      // Check metrics display - use getAllByText for duplicate values
      const totalTokensElements = screen.getAllByText('1');
      expect(totalTokensElements.length).toBeGreaterThanOrEqual(2); // Total tokens and compound tokens
      const confidenceElements = screen.getAllByText('95.0%');
      expect(confidenceElements.length).toBeGreaterThanOrEqual(1); // Confidence appears in multiple places
    });
  });

  it('shows compound words detection section', async () => {
    const mockResponse = {
      success: true,
      data: {
        originalText: 'วากาเมะ',
        tokens: [
          {
            text: 'วากาเมะ',
            startIndex: 0,
            endIndex: 7,
            isCompound: true,
            confidence: 0.95,
            category: 'thai_compound'
          }
        ],
        wordBoundaries: [0],
        compoundsFound: [
          {
            word: 'วากาเมะ',
            startIndex: 0,
            endIndex: 7,
            confidence: 0.95,
            components: ['วา', 'กาเมะ']
          }
        ],
        processingTime: 45.2,
        engine: 'pythainlp-mock',
        confidence: 0.95
      }
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<TokenizationTestInterface />);
    
    const textarea = screen.getByPlaceholderText(/Enter Thai text here to test tokenization/);
    fireEvent.change(textarea, { target: { value: 'วากาเมะ' } });

    await waitFor(() => {
      expect(screen.getByText('Compound Words Detected')).toBeInTheDocument();
      expect(screen.getByText('1 found')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('API Error'));

    render(<TokenizationTestInterface />);
    
    const textarea = screen.getByPlaceholderText(/Enter Thai text here to test tokenization/);
    fireEvent.change(textarea, { target: { value: 'วากาเมะ' } });

    await waitFor(() => {
      expect(screen.getByText('API Error')).toBeInTheDocument();
    });
  });

  it('clears input and results when clear button is clicked', async () => {
    render(<TokenizationTestInterface />);
    
    const textarea = screen.getByPlaceholderText(/Enter Thai text here to test tokenization/);
    fireEvent.change(textarea, { target: { value: 'วากาเมะ' } });

    const clearButton = screen.getByText('Clear');
    fireEvent.click(clearButton);

    expect(textarea).toHaveValue('');
  });

  it('shows empty state when no text is entered', () => {
    render(<TokenizationTestInterface />);
    
    expect(screen.getByText('Start typing to see tokenization results')).toBeInTheDocument();
    expect(screen.getByText('Enter Thai text above and watch as it gets tokenized in real-time')).toBeInTheDocument();
  });

  it('renders tabs for different testing modes', () => {
    render(<TokenizationTestInterface />);
    
    expect(screen.getByText('Live Testing')).toBeInTheDocument();
    expect(screen.getByText('Comparison')).toBeInTheDocument();
    expect(screen.getByText('Test History')).toBeInTheDocument();
    expect(screen.getByText('Batch Testing')).toBeInTheDocument();
  });

  it('shows sample templates selector', () => {
    render(<TokenizationTestInterface />);
    
    expect(screen.getByText('Quick Templates')).toBeInTheDocument();
    expect(screen.getByText('Load predefined text samples for testing')).toBeInTheDocument();
  });

  it('displays save result button when result is available', async () => {
    const mockResponse = {
      success: true,
      data: {
        originalText: 'วากาเมะ',
        tokens: [
          {
            text: 'วากาเมะ',
            startIndex: 0,
            endIndex: 7,
            isCompound: true,
            confidence: 0.95,
            category: 'thai_compound'
          }
        ],
        wordBoundaries: [0],
        compoundsFound: [
          {
            word: 'วากาเมะ',
            startIndex: 0,
            endIndex: 7,
            confidence: 0.95
          }
        ],
        processingTime: 45.2,
        engine: 'pythainlp-mock',
        confidence: 0.95
      }
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse,
    });

    render(<TokenizationTestInterface />);
    
    const textarea = screen.getByPlaceholderText(/Enter Thai text here to test tokenization/);
    fireEvent.change(textarea, { target: { value: 'วากาเมะ' } });

    await waitFor(() => {
      expect(screen.getByText('Save Result')).toBeInTheDocument();
    });
  });
});