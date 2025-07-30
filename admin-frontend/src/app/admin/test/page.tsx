'use client';

import { TokenizationTestInterface } from '@/components/tokenization-test-interface';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function TestPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tokenization Testing</h1>
          <p className="text-muted-foreground">
            Test Thai compound word tokenization in real-time
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Live Tokenization Test</CardTitle>
          <CardDescription>
            Enter Thai text below to see how it gets tokenized. Compound words will be highlighted
            and processing metrics will be displayed in real-time.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <TokenizationTestInterface />
        </CardContent>
      </Card>
    </div>
  );
}