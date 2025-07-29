import { NextRequest, NextResponse } from 'next/server';
import { CompoundWord, PaginatedResponse, FilterOptions } from '@/types';
import fs from 'fs/promises';
import path from 'path';

// Mock data for development - in production this would connect to the actual API
const COMPOUNDS_FILE = path.join(process.cwd(), '../../data/dictionaries/thai_compounds.json');
const CONFIG_FILE = path.join(process.cwd(), '../../config/compound_words.json');

// Generate mock compound words with proper structure
function generateMockCompounds(): CompoundWord[] {
  const categories = [
    { id: 'thai_japanese_compounds', name: 'Thai-Japanese Compounds' },
    { id: 'thai_english_compounds', name: 'Thai-English Compounds' },
  ];

  const mockWords = [
    { word: 'วากาเมะ', category: 'thai_japanese_compounds', usageCount: 1247, confidence: 0.95 },
    { word: 'สาหร่ายวากาเมะ', category: 'thai_japanese_compounds', usageCount: 892, confidence: 0.92 },
    { word: 'ซาชิมิ', category: 'thai_japanese_compounds', usageCount: 2156, confidence: 0.98 },
    { word: 'เทมปุระ', category: 'thai_japanese_compounds', usageCount: 1834, confidence: 0.96 },
    { word: 'ซูชิ', category: 'thai_japanese_compounds', usageCount: 3421, confidence: 0.99 },
    { word: 'ราเมน', category: 'thai_japanese_compounds', usageCount: 2789, confidence: 0.97 },
    { word: 'อุด้ง', category: 'thai_japanese_compounds', usageCount: 1456, confidence: 0.94 },
    { word: 'โซบะ', category: 'thai_japanese_compounds', usageCount: 1123, confidence: 0.93 },
    { word: 'มิโซะ', category: 'thai_japanese_compounds', usageCount: 987, confidence: 0.91 },
    { word: 'โชยุ', category: 'thai_japanese_compounds', usageCount: 756, confidence: 0.89 },
    { word: 'วาซาบิ', category: 'thai_japanese_compounds', usageCount: 1678, confidence: 0.95 },
    { word: 'เกนมัย', category: 'thai_japanese_compounds', usageCount: 543, confidence: 0.87 },
    { word: 'คาราเกะ', category: 'thai_japanese_compounds', usageCount: 432, confidence: 0.85 },
    { word: 'คาราโอเกะ', category: 'thai_japanese_compounds', usageCount: 2345, confidence: 0.96 },
    { word: 'คาราเต้', category: 'thai_japanese_compounds', usageCount: 1876, confidence: 0.94 },
    { word: 'ซามูไร', category: 'thai_japanese_compounds', usageCount: 1234, confidence: 0.92 },
    { word: 'นินจา', category: 'thai_japanese_compounds', usageCount: 1567, confidence: 0.93 },
    { word: 'โตโยต้า', category: 'thai_japanese_compounds', usageCount: 4567, confidence: 0.99 },
    { word: 'ฮอนด้า', category: 'thai_japanese_compounds', usageCount: 3890, confidence: 0.98 },
    { word: 'นิสสัน', category: 'thai_japanese_compounds', usageCount: 2134, confidence: 0.95 },
    { word: 'มิตซูบิชิ', category: 'thai_japanese_compounds', usageCount: 1789, confidence: 0.94 },
    { word: 'ซูซูกิ', category: 'thai_japanese_compounds', usageCount: 1456, confidence: 0.93 },
    { word: 'คอมพิวเตอร์', category: 'thai_english_compounds', usageCount: 8765, confidence: 0.99 },
    { word: 'อินเทอร์เน็ต', category: 'thai_english_compounds', usageCount: 7654, confidence: 0.98 },
    { word: 'เว็บไซต์', category: 'thai_english_compounds', usageCount: 6543, confidence: 0.97 },
    { word: 'อีเมล', category: 'thai_english_compounds', usageCount: 5432, confidence: 0.96 },
    { word: 'โซเชียล', category: 'thai_english_compounds', usageCount: 4321, confidence: 0.95 },
    { word: 'มาร์เก็ตติ้ง', category: 'thai_english_compounds', usageCount: 3210, confidence: 0.94 },
    { word: 'แบรนด์ดิ้ง', category: 'thai_english_compounds', usageCount: 2109, confidence: 0.93 },
    { word: 'บิสิเนส', category: 'thai_english_compounds', usageCount: 1987, confidence: 0.92 },
    { word: 'เทคโนโลยี', category: 'thai_english_compounds', usageCount: 6789, confidence: 0.98 },
    { word: 'ดิจิทัล', category: 'thai_english_compounds', usageCount: 5678, confidence: 0.97 },
  ];

  return mockWords.map((word, index) => ({
    id: `compound_${index + 1}`,
    word: word.word,
    category: word.category,
    components: word.word.length > 5 ? [word.word.slice(0, 3), word.word.slice(3)] : undefined,
    confidence: word.confidence,
    usageCount: word.usageCount,
    lastUsed: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000), // Random date within last 30 days
    createdAt: new Date(Date.now() - Math.random() * 365 * 24 * 60 * 60 * 1000), // Random date within last year
    updatedAt: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000), // Random date within last week
    createdBy: 'admin',
    tags: word.category === 'thai_japanese_compounds' ? ['japanese', 'food'] : ['english', 'technology'],
    notes: `Auto-generated compound word for ${word.category}`,
  }));
}

function applyFilters(compounds: CompoundWord[], filters: Partial<FilterOptions>): CompoundWord[] {
  let filtered = [...compounds];

  // Search filter
  if (filters.search) {
    const searchTerm = filters.search.toLowerCase();
    filtered = filtered.filter(compound => 
      compound.word.toLowerCase().includes(searchTerm) ||
      compound.category.toLowerCase().includes(searchTerm) ||
      compound.tags.some(tag => tag.toLowerCase().includes(searchTerm))
    );
  }

  // Category filter
  if (filters.category && filters.category !== 'all') {
    filtered = filtered.filter(compound => compound.category === filters.category);
  }

  // Usage count filter
  if (filters.minUsageCount && filters.minUsageCount > 0) {
    filtered = filtered.filter(compound => compound.usageCount >= filters.minUsageCount!);
  }

  // Date range filter
  if (filters.dateRange?.start) {
    filtered = filtered.filter(compound => compound.createdAt >= filters.dateRange!.start!);
  }
  if (filters.dateRange?.end) {
    filtered = filtered.filter(compound => compound.createdAt <= filters.dateRange!.end!);
  }

  // Sorting
  if (filters.sortBy) {
    filtered.sort((a, b) => {
      let aValue: any = a[filters.sortBy as keyof CompoundWord];
      let bValue: any = b[filters.sortBy as keyof CompoundWord];

      // Handle date sorting
      if (aValue instanceof Date && bValue instanceof Date) {
        aValue = aValue.getTime();
        bValue = bValue.getTime();
      }

      // Handle string sorting
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        aValue = aValue.toLowerCase();
        bValue = bValue.toLowerCase();
      }

      if (filters.sortOrder === 'desc') {
        return bValue > aValue ? 1 : bValue < aValue ? -1 : 0;
      } else {
        return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
      }
    });
  }

  return filtered;
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    
    // Parse query parameters
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '50');
    const search = searchParams.get('search') || '';
    const category = searchParams.get('category') || '';
    const minUsageCount = parseInt(searchParams.get('minUsageCount') || '0');
    const sortBy = searchParams.get('sortBy') || 'updatedAt';
    const sortOrder = searchParams.get('sortOrder') || 'desc';
    
    // Parse date range
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');
    const dateRange = {
      start: startDate ? new Date(startDate) : null,
      end: endDate ? new Date(endDate) : null,
    };

    const filters: Partial<FilterOptions> = {
      search,
      category,
      minUsageCount,
      dateRange,
      sortBy: sortBy as any,
      sortOrder: sortOrder as 'asc' | 'desc',
    };

    // Generate mock data
    const allCompounds = generateMockCompounds();
    
    // Apply filters
    const filteredCompounds = applyFilters(allCompounds, filters);
    
    // Apply pagination
    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + limit;
    const paginatedCompounds = filteredCompounds.slice(startIndex, endIndex);
    
    const response: PaginatedResponse<CompoundWord> = {
      data: paginatedCompounds,
      pagination: {
        page,
        limit,
        total: filteredCompounds.length,
        totalPages: Math.ceil(filteredCompounds.length / limit),
        hasMore: endIndex < filteredCompounds.length,
      },
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error('Error fetching compounds:', error);
    return NextResponse.json(
      { error: 'Failed to fetch compounds' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Validate required fields
    if (!body.word || !body.category) {
      return NextResponse.json(
        { error: 'Word and category are required' },
        { status: 400 }
      );
    }

    // Create new compound word
    const newCompound: CompoundWord = {
      id: `compound_${Date.now()}`,
      word: body.word,
      category: body.category,
      components: body.components,
      confidence: body.confidence || 0.9,
      usageCount: 0,
      lastUsed: undefined,
      createdAt: new Date(),
      updatedAt: new Date(),
      createdBy: 'admin', // In production, get from auth context
      tags: body.tags || [],
      notes: body.notes,
    };

    // In production, save to database
    console.log('Created new compound:', newCompound);

    return NextResponse.json(newCompound, { status: 201 });
  } catch (error) {
    console.error('Error creating compound:', error);
    return NextResponse.json(
      { error: 'Failed to create compound' },
      { status: 500 }
    );
  }
}