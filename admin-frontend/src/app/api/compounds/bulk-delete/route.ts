import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Validate required fields
    if (!body.ids || !Array.isArray(body.ids) || body.ids.length === 0) {
      return NextResponse.json(
        { error: 'IDs array is required and must not be empty' },
        { status: 400 }
      );
    }

    // In production, delete compounds from database
    console.log('Bulk deleting compounds:', body.ids);

    return NextResponse.json({ 
      success: true, 
      deletedCount: body.ids.length 
    });
  } catch (error) {
    console.error('Error bulk deleting compounds:', error);
    return NextResponse.json(
      { error: 'Failed to delete compounds' },
      { status: 500 }
    );
  }
}