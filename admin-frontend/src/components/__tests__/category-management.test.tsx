import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CategoryManagement } from '../category-management';
import { CompoundWord } from '@/types';

// Mock recharts components
jest.mock('recharts', () => ({
  BarChart: jest.fn(({ children }) => children),
  Bar: jest.fn(() => null),
  XAxis: jest.fn(() => null),
  YAxis: jest.fn(() => null),
  CartesianGrid: jest.fn(() => null),
  Tooltip: jest.fn(() => null),
  ResponsiveContainer: jest.fn(({ children }) => children),
  PieChart: jest.fn(({ children }) => children),
  Pie: jest.fn(() => null),
  Cell: jest.fn(() => null),
  LineChart: jest.fn(({ children }) => children),
  Line: jest.fn(() => null),
}));

const mockCompounds: CompoundWord[] = [
  {
    id: '1',
    word: 'วากาเมะ',
    category: 'thai_japanese_compounds',
    confidence: 0.95,
    usageCount: 1247,
    createdAt: new Date('2024-01-15'),
    updatedAt: new Date('2024-01-15'),
    createdBy: 'admin',
    tags: ['food', 'japanese'],
  },
];

describe('CategoryManagement', () => {
  it('should render category management interface', () => {
    render(<CategoryManagement compounds={mockCompounds} />);
    
    expect(screen.getByText('Category Management')).toBeInTheDocument();
    expect(screen.getByText('Thai-Japanese Compounds')).toBeInTheDocument();
    expect(screen.getByText('Thai-English Compounds')).toBeInTheDocument();
  });

  it('should show analytics when analytics button is clicked', async () => {
    const user = userEvent.setup();
    render(<CategoryManagement compounds={mockCompounds} />);
    
    const analyticsButton = screen.getByText('Show Analytics');
    await user.click(analyticsButton);
    
    await waitFor(() => {
      expect(screen.getByText('Total Categories')).toBeInTheDocument();
    });
  });

  it('should filter categories by search term', async () => {
    const user = userEvent.setup();
    render(<CategoryManagement compounds={mockCompounds} />);
    
    const searchInput = screen.getByPlaceholderText('Search categories...');
    await user.type(searchInput, 'Japanese');
    
    expect(screen.getByText('Thai-Japanese Compounds')).toBeInTheDocument();
  });
});