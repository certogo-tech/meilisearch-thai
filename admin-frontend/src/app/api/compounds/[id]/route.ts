import { NextRequest, NextResponse } from 'next/server';
import { CompoundWord } from '@/types';

// Mock function to find compound by ID
function findCompoundById(id: string): CompoundWord | null {
  // In production, this would query the database
  // For now, return a mock compound for demonstration
  return {
    id,
    word: 'วากาเมะ',
    category: 'thai_japanese_compounds',
    components: ['วา', 'กา', 'เมะ'],
    confidence: 0.95,
    usageCount: 1247,
    lastUsed: new Date(),
    createdAt: new Date(),
    updatedAt: new Date(),
    createdBy: 'admin',
    tags: ['japanese', 'food'],
    notes: 'Mock compound for testing',
  };
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const compound = findCompoundById(id);
    
    if (!compound) {
      return NextResponse.json(
        { error: 'Compound not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(compound);
  } catch (error) {
    console.error('Error fetching compound:', error);
    return NextResponse.json(
      { error: 'Failed to fetch compound' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    
    // Validate required fields
    if (!body.word || !body.category) {
      return NextResponse.json(
        { error: 'Word and category are required' },
        { status: 400 }
      );
    }

    // Find existing compound
    const existingCompound = findCompoundById(id);
    if (!existingCompound) {
      return NextResponse.json(
        { error: 'Compound not found' },
        { status: 404 }
      );
    }

    // Update compound
    const updatedCompound: CompoundWord = {
      ...existingCompound,
      word: body.word,
      category: body.category,
      components: body.components,
      confidence: body.confidence || existingCompound.confidence,
      tags: body.tags || existingCompound.tags,
      notes: body.notes,
      updatedAt: new Date(),
    };

    // In production, save to database
    console.log('Updated compound:', updatedCompound);

    return NextResponse.json(updatedCompound);
  } catch (error) {
    console.error('Error updating compound:', error);
    return NextResponse.json(
      { error: 'Failed to update compound' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    // Find existing compound
    const existingCompound = findCompoundById(id);
    if (!existingCompound) {
      return NextResponse.json(
        { error: 'Compound not found' },
        { status: 404 }
      );
    }

    // In production, delete from database
    console.log('Deleted compound:', id);

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error deleting compound:', error);
    return NextResponse.json(
      { error: 'Failed to delete compound' },
      { status: 500 }
    );
  }
}