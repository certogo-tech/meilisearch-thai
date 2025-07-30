import { NextRequest, NextResponse } from 'next/server';
import { TokenizationResult, TokenInfo, CompoundMatch } from '@/types';

// Mock tokenization function - in production this would call the actual Thai tokenizer API
async function mockTokenize(text: string): Promise<TokenizationResult> {
  // Simulate processing time
  await new Promise(resolve => setTimeout(resolve, Math.random() * 100 + 50));
  
  // Simple mock tokenization for Thai text
  const words = text.split(/\s+/).filter(word => word.length > 0);
  const tokens: TokenInfo[] = [];
  const compoundsFound: CompoundMatch[] = [];
  let currentIndex = 0;
  
  for (const word of words) {
    const startIndex = text.indexOf(word, currentIndex);
    const endIndex = startIndex + word.length;
    
    // Mock compound detection - detect Thai compound words
    const isCompound = word.length > 3 && /[\u0E00-\u0E7F]/.test(word);
    const confidence = isCompound ? Math.random() * 0.3 + 0.7 : Math.random() * 0.5 + 0.5;
    
    tokens.push({
      text: word,
      startIndex,
      endIndex,
      isCompound,
      confidence,
      category: isCompound ? 'thai_compound' : 'regular'
    });
    
    if (isCompound) {
      compoundsFound.push({
        word,
        startIndex,
        endIndex,
        confidence,
        components: word.length > 5 ? [word.slice(0, Math.floor(word.length/2)), word.slice(Math.floor(word.length/2))] : undefined
      });
    }
    
    currentIndex = endIndex;
  }
  
  return {
    originalText: text,
    tokens,
    wordBoundaries: tokens.map(t => t.startIndex),
    compoundsFound,
    processingTime: Math.random() * 50 + 10,
    engine: 'pythainlp-mock',
    confidence: tokens.reduce((acc, t) => acc + t.confidence, 0) / tokens.length
  };
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { text, options = {} } = body;
    
    if (!text || typeof text !== 'string') {
      return NextResponse.json(
        { error: 'Text is required and must be a string' },
        { status: 400 }
      );
    }
    
    if (text.length > 10000) {
      return NextResponse.json(
        { error: 'Text too long. Maximum 10,000 characters allowed.' },
        { status: 400 }
      );
    }
    
    const result = await mockTokenize(text);
    
    return NextResponse.json({
      success: true,
      data: result
    });
    
  } catch (error) {
    console.error('Tokenization error:', error);
    return NextResponse.json(
      { error: 'Internal server error during tokenization' },
      { status: 500 }
    );
  }
}

// GET endpoint to provide sample texts for testing
export async function GET() {
  const sampleTexts = [
    {
      id: 'thai_compounds',
      title: 'Thai Compound Words',
      text: 'สาหร่ายวากาเมะเป็นสาหร่ายทะเลจากญี่ปุ่นที่มีรสชาติหวานเล็กน้อย เหมาะสำหรับทำสลัดหรือซุป',
      description: 'Contains Thai-Japanese compound words like วากาเมะ (wakame seaweed)'
    },
    {
      id: 'technology',
      title: 'Technology Terms',
      text: 'ปัญญาประดิษฐ์หรือ AI เป็นเทคโนโลยีที่กำลังเปลี่ยนแปลงโลก การเรียนรู้ของเครื่อง (Machine Learning) และการเรียนรู้เชิงลึก (Deep Learning)',
      description: 'Technical terms with mixed Thai-English content'
    },
    {
      id: 'food_culture',
      title: 'Thai Food Culture',
      text: 'อาหารไทยมีความหลากหลายและรสชาติที่เป็นเอกลักษณ์ ต้มยำกุ้ง แกงเขียวหวาน ผัดไทย และส้มตำ เป็นอาหารที่มีชื่อเสียงระดับโลก',
      description: 'Traditional Thai food names and cultural terms'
    },
    {
      id: 'mixed_content',
      title: 'Mixed Thai-English',
      text: 'Startup ecosystem ในประเทศไทยกำลังเติบโตอย่างรวดเร็ว บริษัท Fintech เช่น TrueMoney, Omise และ 2C2P กำลังปฏิวัติระบบการเงิน',
      description: 'Business text with mixed Thai and English terms'
    }
  ];

  return NextResponse.json({
    success: true,
    data: sampleTexts
  });
}