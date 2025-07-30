'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Loader2, Clock, Target, Zap, Hash, Activity, BarChart3, RefreshCw, Copy, CheckCircle2, AlertCircle, History, Save, Download, Play, Pause, RotateCcw, FileText, Layers } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { TokenizationResult, TokenizationMetrics, TestResult } from '@/types';
import { useDebounce } from '@/hooks/use-debounce';

interface TokenizationTestInterfaceProps {
  className?: string;
}

export function TokenizationTestInterface({ className }: TokenizationTestInterfaceProps) {
  const [inputText, setInputText] = useState('');
  const [result, setResult] = useState<TokenizationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<TokenizationMetrics | null>(null);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // Comparison and history state
  const [testHistory, setTestHistory] = useState<TestResult[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [comparisonMode, setComparisonMode] = useState<'single' | 'comparison'>('single');
  const [beforeResult, setBeforeResult] = useState<TokenizationResult | null>(null);
  const [afterResult, setAfterResult] = useState<TokenizationResult | null>(null);
  const [batchTests, setBatchTests] = useState<string[]>([]);
  const [batchProgress, setBatchProgress] = useState(0);
  const [isBatchRunning, setIsBatchRunning] = useState(false);

  // Debounce input to avoid excessive API calls (300ms for better responsiveness)
  const debouncedText = useDebounce(inputText, 300);

  // Sample templates for testing
  const sampleTemplates = [
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

  const tokenizeText = useCallback(async (text: string) => {
    if (!text.trim()) {
      setResult(null);
      setMetrics(null);
      setProcessingProgress(0);
      return;
    }

    setIsLoading(true);
    setError(null);
    setProcessingProgress(0);

    // Simulate progressive loading for better UX
    const progressInterval = setInterval(() => {
      setProcessingProgress(prev => Math.min(prev + Math.random() * 20, 90));
    }, 50);

    try {
      const startTime = performance.now();
      
      const response = await fetch('/api/tokenize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          text,
          options: {
            includeAlternatives: false,
            preserveWhitespace: true
          }
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Tokenization failed');
      }

      const data = await response.json();
      const tokenizationResult = data.data as TokenizationResult;
      const actualProcessingTime = performance.now() - startTime;
      
      // Complete the progress
      setProcessingProgress(100);
      
      setResult(tokenizationResult);
      
      // Calculate enhanced metrics with actual client-side timing
      const totalTokens = tokenizationResult.tokens.length;
      const compoundTokens = tokenizationResult.tokens.filter(t => t.isCompound).length;
      const averageConfidence = totalTokens > 0 
        ? tokenizationResult.tokens.reduce((acc, t) => acc + t.confidence, 0) / totalTokens 
        : 0;
      const textLength = text.length;
      const tokensPerSecond = totalTokens / (actualProcessingTime / 1000);
      const charactersPerSecond = textLength / (actualProcessingTime / 1000);
      
      setMetrics({
        totalTokens,
        compoundTokens,
        processingTime: actualProcessingTime,
        confidence: averageConfidence,
        accuracy: tokenizationResult.confidence,
        textLength,
        tokensPerSecond,
        charactersPerSecond,
      });
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred during tokenization');
      setResult(null);
      setMetrics(null);
      setProcessingProgress(0);
    } finally {
      clearInterval(progressInterval);
      setIsLoading(false);
      // Reset progress after a short delay
      setTimeout(() => setProcessingProgress(0), 1000);
    }
  }, []);

  // Trigger tokenization when debounced text changes
  useEffect(() => {
    tokenizeText(debouncedText);
  }, [debouncedText, tokenizeText]);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
  };

  const clearInput = () => {
    setInputText('');
    setResult(null);
    setMetrics(null);
    setError(null);
    setProcessingProgress(0);
    setCopied(false);
    textareaRef.current?.focus();
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const retryTokenization = () => {
    if (inputText.trim()) {
      tokenizeText(inputText);
    }
  };

  const saveTestResult = () => {
    if (result && inputText.trim()) {
      const testResult: TestResult = {
        id: Date.now().toString(),
        text: inputText,
        result,
        timestamp: new Date(),
        saved: true
      };
      setTestHistory(prev => [testResult, ...prev.slice(0, 9)]); // Keep last 10 results
    }
  };

  const loadTemplate = (templateId: string) => {
    const template = sampleTemplates.find(t => t.id === templateId);
    if (template) {
      setInputText(template.text);
      setSelectedTemplate(templateId);
    }
  };

  const runBatchTest = async () => {
    if (batchTests.length === 0) return;
    
    setIsBatchRunning(true);
    setBatchProgress(0);
    
    const results: TestResult[] = [];
    
    for (let i = 0; i < batchTests.length; i++) {
      const text = batchTests[i];
      if (text.trim()) {
        try {
          const response = await fetch('/api/tokenize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
          });
          
          if (response.ok) {
            const data = await response.json();
            results.push({
              id: `batch-${Date.now()}-${i}`,
              text,
              result: data.data,
              timestamp: new Date(),
              saved: false
            });
          }
        } catch (err) {
          console.error('Batch test error:', err);
        }
      }
      
      setBatchProgress(((i + 1) / batchTests.length) * 100);
      await new Promise(resolve => setTimeout(resolve, 100)); // Small delay for UX
    }
    
    setTestHistory(prev => [...results, ...prev].slice(0, 20));
    setIsBatchRunning(false);
    setBatchProgress(0);
  };

  const exportResults = () => {
    const exportData = {
      timestamp: new Date().toISOString(),
      testHistory: testHistory.map(test => ({
        text: test.text,
        totalTokens: test.result.tokens.length,
        compoundTokens: test.result.tokens.filter(t => t.isCompound).length,
        processingTime: test.result.processingTime,
        confidence: test.result.confidence,
        timestamp: test.timestamp
      }))
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tokenization-test-results-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const clearHistory = () => {
    setTestHistory([]);
  };

  const renderComparisonView = () => {
    if (!beforeResult || !afterResult) return null;

    const getDiffHighlight = (beforeTokens: any[], afterTokens: any[]) => {
      // Simple diff highlighting - in production, use a proper diff library
      const beforeText = beforeTokens.map(t => t.text).join('');
      const afterText = afterTokens.map(t => t.text).join('');
      return beforeText !== afterText;
    };

    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-l-4 border-l-red-500">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Layers className="h-4 w-4 text-red-500" />
              Before Changes
            </CardTitle>
            <CardDescription>
              Original tokenization results
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2 p-4 bg-red-50 rounded-lg min-h-[100px] border-2 border-dashed border-red-200">
              {beforeResult.tokens.map((token, index) => (
                <Badge
                  key={index}
                  variant="outline"
                  className="text-sm px-3 py-1.5 font-thai bg-red-100 text-red-800 border-red-200"
                >
                  {token.text}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-green-500">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Layers className="h-4 w-4 text-green-500" />
              After Changes
            </CardTitle>
            <CardDescription>
              Updated tokenization results
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2 p-4 bg-green-50 rounded-lg min-h-[100px] border-2 border-dashed border-green-200">
              {afterResult.tokens.map((token, index) => (
                <Badge
                  key={index}
                  variant="outline"
                  className="text-sm px-3 py-1.5 font-thai bg-green-100 text-green-800 border-green-200"
                >
                  {token.text}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  const renderTokenizedText = () => {
    if (!result) return null;

    return (
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2 p-4 bg-muted/50 rounded-lg min-h-[100px] border-2 border-dashed border-muted-foreground/20">
          {result.tokens.map((token, index) => {
            // Enhanced color coding based on confidence and type
            const getTokenStyle = () => {
              if (token.isCompound) {
                if (token.confidence >= 0.8) {
                  return 'bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-900 dark:text-emerald-200';
                } else if (token.confidence >= 0.6) {
                  return 'bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900 dark:text-blue-200';
                } else {
                  return 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900 dark:text-amber-200';
                }
              } else {
                return 'bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-300';
              }
            };

            return (
              <Badge
                key={index}
                variant="outline"
                className={`
                  text-sm px-3 py-1.5 font-thai cursor-help transition-all hover:scale-105 hover:shadow-sm
                  ${getTokenStyle()}
                `}
                title={`
                  Token: ${token.text}
                  Confidence: ${(token.confidence * 100).toFixed(1)}%
                  Category: ${token.category || 'N/A'}
                  Type: ${token.isCompound ? 'Compound Word' : 'Regular Token'}
                  Position: ${token.startIndex}-${token.endIndex}
                `}
              >
                {token.text}
                {token.isCompound && (
                  <span className="ml-1.5 text-xs opacity-75 font-mono">
                    {(token.confidence * 100).toFixed(0)}%
                  </span>
                )}
              </Badge>
            );
          })}
        </div>

        {result.compoundsFound.length > 0 && (
          <Card className="border-l-4 border-l-blue-500">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Target className="h-4 w-4 text-blue-500" />
                  Compound Words Detected
                </CardTitle>
                <Badge variant="secondary" className="text-xs">
                  {result.compoundsFound.length} found
                </Badge>
              </div>
              <CardDescription className="text-xs">
                Thai compound words identified by the tokenizer with confidence scores
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {result.compoundsFound.map((compound, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border hover:bg-muted/50 transition-colors">
                  <div className="flex items-center gap-3">
                    <Badge 
                      variant="outline" 
                      className="font-thai text-base px-3 py-1 bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                    >
                      {compound.word}
                    </Badge>
                    {compound.components && (
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="text-muted-foreground/70">→</span>
                        <div className="flex gap-1">
                          {compound.components.map((comp, i) => (
                            <Badge key={i} variant="secondary" className="text-xs font-thai px-2 py-0.5">
                              {comp}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge 
                      variant="outline" 
                      className={`text-xs font-mono ${
                        compound.confidence >= 0.8 
                          ? 'text-green-700 border-green-200 bg-green-50 dark:text-green-300 dark:border-green-800 dark:bg-green-950' 
                          : compound.confidence >= 0.6 
                          ? 'text-blue-700 border-blue-200 bg-blue-50 dark:text-blue-300 dark:border-blue-800 dark:bg-blue-950'
                          : 'text-amber-700 border-amber-200 bg-amber-50 dark:text-amber-300 dark:border-amber-800 dark:bg-amber-950'
                      }`}
                    >
                      {(compound.confidence * 100).toFixed(1)}%
                    </Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    );
  };

  const renderMetrics = () => {
    if (!metrics) return null;

    const compoundRatio = metrics.totalTokens > 0 ? (metrics.compoundTokens / metrics.totalTokens) * 100 : 0;
    const processingSpeed = metrics.tokensPerSecond || 0;
    const charactersPerSecond = metrics.charactersPerSecond || 0;
    const efficiency = metrics.textLength > 0 ? (metrics.totalTokens / metrics.textLength) * 100 : 0;

    return (
      <div className="space-y-6">
        {/* Processing Progress Bar */}
        {isLoading && processingProgress > 0 && (
          <Card className="border-primary/20 bg-primary/5">
            <CardContent className="p-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-primary">Processing Thai text...</span>
                  <span className="text-muted-foreground">{processingProgress.toFixed(0)}%</span>
                </div>
                <Progress 
                  value={processingProgress} 
                  className="h-2 bg-muted" 
                />
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Activity className="h-3 w-3 animate-pulse" />
                  <span>Analyzing compound words and tokenization patterns</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Main Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Hash className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-2xl font-bold">{metrics.totalTokens}</p>
                <p className="text-xs text-muted-foreground">Total Tokens</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-blue-500" />
              <div>
                <p className="text-2xl font-bold text-blue-600">{metrics.compoundTokens}</p>
                <p className="text-xs text-muted-foreground">Compounds</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-green-500" />
              <div>
                <p className="text-2xl font-bold text-green-600">
                  {metrics.processingTime.toFixed(1)}ms
                </p>
                <p className="text-xs text-muted-foreground">Processing Time</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-orange-500" />
              <div>
                <p className="text-2xl font-bold text-orange-600">
                  {(metrics.confidence * 100).toFixed(1)}%
                </p>
                <p className="text-xs text-muted-foreground">Confidence</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-purple-500" />
              <div>
                <p className="text-2xl font-bold text-purple-600">
                  {processingSpeed.toFixed(0)}
                </p>
                <p className="text-xs text-muted-foreground">Tokens/sec</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-indigo-500" />
              <div>
                <p className="text-2xl font-bold text-indigo-600">
                  {metrics.textLength || 0}
                </p>
                <p className="text-xs text-muted-foreground">Characters</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Additional Performance Metrics */}
        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-cyan-500" />
              <div>
                <p className="text-2xl font-bold text-cyan-600">
                  {charactersPerSecond.toFixed(0)}
                </p>
                <p className="text-xs text-muted-foreground">Chars/sec</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-rose-500" />
              <div>
                <p className="text-2xl font-bold text-rose-600">
                  {efficiency.toFixed(1)}%
                </p>
                <p className="text-xs text-muted-foreground">Efficiency</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Compound Detection Progress */}
        <Card className="col-span-2 md:col-span-3 lg:col-span-8 hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="space-y-3">
              <div className="flex justify-between text-sm font-medium">
                <span>Compound Word Detection Rate</span>
                <span className="text-blue-600">{compoundRatio.toFixed(1)}%</span>
              </div>
              <Progress 
                value={compoundRatio} 
                className="h-3 bg-muted" 
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{metrics.compoundTokens} compound words detected</span>
                <span>{metrics.totalTokens - metrics.compoundTokens} regular tokens</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Performance Indicator */}
        <Card className="col-span-2 md:col-span-3 lg:col-span-8 hover:shadow-md transition-shadow">
          <CardContent className="p-4">
            <div className="space-y-3">
              <div className="flex justify-between text-sm font-medium">
                <span>Processing Performance</span>
                <span className={`${
                  metrics.processingTime < 50 ? 'text-green-600' : 
                  metrics.processingTime < 100 ? 'text-yellow-600' : 'text-red-600'
                }`}>
                  {metrics.processingTime < 50 ? 'Excellent' : 
                   metrics.processingTime < 100 ? 'Good' : 'Slow'}
                </span>
              </div>
              <Progress 
                value={Math.min((200 - metrics.processingTime) / 2, 100)} 
                className="h-3 bg-muted" 
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Target: &lt;50ms for optimal performance</span>
                <span>Actual: {metrics.processingTime.toFixed(1)}ms</span>
              </div>
            </div>
          </CardContent>
        </Card>
        </div>
      </div>
    );
  };

  const renderTestHistory = () => {
    if (testHistory.length === 0) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          <History className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg font-medium">No test history yet</p>
          <p className="text-sm">Run some tests to see results here</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Test History</h3>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={exportResults}
              className="text-blue-600 border-blue-200 hover:bg-blue-50"
            >
              <Download className="h-3 w-3 mr-1" />
              Export
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={clearHistory}
              className="text-red-600 border-red-200 hover:bg-red-50"
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Clear
            </Button>
          </div>
        </div>

        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Text Sample</TableHead>
                <TableHead className="text-center">Tokens</TableHead>
                <TableHead className="text-center">Compounds</TableHead>
                <TableHead className="text-center">Time (ms)</TableHead>
                <TableHead className="text-center">Confidence</TableHead>
                <TableHead className="text-center">Timestamp</TableHead>
                <TableHead className="text-center">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {testHistory.map((test) => (
                <TableRow key={test.id} className="hover:bg-muted/50">
                  <TableCell className="max-w-xs">
                    <div className="truncate font-thai" title={test.text}>
                      {test.text}
                    </div>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant="secondary">
                      {test.result.tokens.length}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline" className="text-blue-600 border-blue-200">
                      {test.result.tokens.filter(t => t.isCompound).length}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge 
                      variant="outline" 
                      className={`${
                        test.result.processingTime < 50 
                          ? 'text-green-600 border-green-200' 
                          : test.result.processingTime < 100 
                          ? 'text-yellow-600 border-yellow-200'
                          : 'text-red-600 border-red-200'
                      }`}
                    >
                      {test.result.processingTime.toFixed(1)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge 
                      variant="outline"
                      className={`${
                        test.result.confidence >= 0.8 
                          ? 'text-green-600 border-green-200' 
                          : test.result.confidence >= 0.6 
                          ? 'text-blue-600 border-blue-200'
                          : 'text-amber-600 border-amber-200'
                      }`}
                    >
                      {(test.result.confidence * 100).toFixed(1)}%
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center text-xs text-muted-foreground">
                    {test.timestamp.toLocaleTimeString()}
                  </TableCell>
                  <TableCell className="text-center">
                    <div className="flex items-center justify-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setInputText(test.text);
                          textareaRef.current?.focus();
                        }}
                        className="h-8 w-8 p-0"
                        title="Load text"
                      >
                        <FileText className="h-3 w-3" />
                      </Button>
                      {test.saved && (
                        <Badge variant="outline" className="text-xs text-green-600 border-green-200">
                          <Save className="h-2 w-2 mr-1" />
                          Saved
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>
    );
  };

  const renderBatchTesting = () => {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Batch Testing</h3>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setBatchTests(sampleTemplates.map(t => t.text))}
              disabled={isBatchRunning}
            >
              <FileText className="h-3 w-3 mr-1" />
              Load Samples
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={runBatchTest}
              disabled={batchTests.length === 0 || isBatchRunning}
            >
              {isBatchRunning ? (
                <>
                  <Pause className="h-3 w-3 mr-1" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-3 w-3 mr-1" />
                  Run Batch
                </>
              )}
            </Button>
          </div>
        </div>

        {isBatchRunning && (
          <Card className="border-primary/20 bg-primary/5">
            <CardContent className="p-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-primary">Processing batch tests...</span>
                  <span className="text-muted-foreground">{batchProgress.toFixed(0)}%</span>
                </div>
                <Progress value={batchProgress} className="h-2 bg-muted" />
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Activity className="h-3 w-3 animate-pulse" />
                  <span>Testing {batchTests.length} text samples</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Batch Test Queue</CardTitle>
            <CardDescription>
              Add multiple text samples to test in sequence
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              placeholder="Enter multiple text samples, one per line..."
              value={batchTests.join('\n')}
              onChange={(e) => setBatchTests(e.target.value.split('\n').filter(line => line.trim()))}
              className="min-h-[120px] font-thai"
              disabled={isBatchRunning}
            />
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>{batchTests.length} samples queued</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setBatchTests([])}
                disabled={isBatchRunning}
              >
                Clear Queue
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <div className={`space-y-6 ${className}`}>
      <Tabs defaultValue="testing" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="testing">Live Testing</TabsTrigger>
          <TabsTrigger value="comparison">Comparison</TabsTrigger>
          <TabsTrigger value="history">Test History</TabsTrigger>
          <TabsTrigger value="batch">Batch Testing</TabsTrigger>
        </TabsList>

        <TabsContent value="testing" className="space-y-6">
          {/* Sample Templates */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Quick Templates</CardTitle>
              <CardDescription>
                Load predefined text samples for testing
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Select value={selectedTemplate} onValueChange={loadTemplate}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Choose a sample template..." />
                </SelectTrigger>
                <SelectContent>
                  {sampleTemplates.map((template) => (
                    <SelectItem key={template.id} value={template.id}>
                      <div className="flex flex-col items-start">
                        <span className="font-medium">{template.title}</span>
                        <span className="text-xs text-muted-foreground">{template.description}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          {/* Input Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label htmlFor="test-input" className="text-sm font-medium">
                Thai Text Input
                <span className="ml-2 text-xs text-muted-foreground">
                  ({inputText.length} characters)
                </span>
              </label>
              <div className="flex items-center gap-2">
                {isLoading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Processing...
                  </div>
                )}
                {error && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={retryTokenization}
                    className="text-orange-600 border-orange-200 hover:bg-orange-50"
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Retry
                  </Button>
                )}
                {result && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={saveTestResult}
                    className="text-green-600 border-green-200 hover:bg-green-50"
                  >
                    <Save className="h-3 w-3 mr-1" />
                    Save Result
                  </Button>
                )}
                {inputText && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyToClipboard(inputText)}
                    className="text-blue-600 border-blue-200 hover:bg-blue-50"
                  >
                    {copied ? (
                      <>
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3 mr-1" />
                        Copy
                      </>
                    )}
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearInput}
                  disabled={!inputText}
                >
                  Clear
                </Button>
              </div>
            </div>
        
        <div className="relative">
          <Textarea
            ref={textareaRef}
            id="test-input"
            placeholder="Enter Thai text here to test tokenization... (e.g., วากาเมะ, ซาชิมิ, เทมปุระ, ปัญญาประดิษฐ์)"
            value={inputText}
            onChange={handleInputChange}
            className={`
              min-h-[120px] font-thai text-base resize-none transition-all duration-200
              ${isLoading ? 'opacity-75 cursor-wait' : ''}
              focus:ring-2 focus:ring-primary/20 focus:border-primary
              placeholder:text-muted-foreground/60
            `}
            disabled={isLoading}
            maxLength={10000}
            aria-describedby="input-help"
          />
          {isLoading && (
            <div className="absolute inset-0 bg-background/50 backdrop-blur-[1px] rounded-md flex items-center justify-center">
              <div className="flex items-center gap-2 bg-background/90 px-3 py-2 rounded-md shadow-sm border">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span className="text-sm font-medium text-foreground">
                  Analyzing Thai text patterns...
                </span>
              </div>
            </div>
          )}
        </div>
        
            <div id="input-help" className="text-xs text-muted-foreground">
              Real-time tokenization with 300ms debouncing. Maximum 10,000 characters.
            </div>
            
            {error && (
              <Card className="border-destructive/20 bg-destructive/5">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-destructive mt-0.5 flex-shrink-0" />
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-destructive">
                        Tokenization Error
                      </p>
                      <p className="text-sm text-destructive/80">
                        {error}
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={retryTokenization}
                        className="text-destructive border-destructive/20 hover:bg-destructive/10"
                      >
                        <RefreshCw className="h-3 w-3 mr-1" />
                        Try Again
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Metrics Section */}
          {metrics && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Processing Metrics</h3>
              {renderMetrics()}
            </div>
          )}

          {/* Results Section */}
          {result && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold">Tokenization Results</h3>
                <Card className="px-3 py-2">
                  <div className="flex items-center gap-4 text-xs">
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded bg-emerald-100 border border-emerald-200"></div>
                      <span>High confidence (≥80%)</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded bg-blue-100 border border-blue-200"></div>
                      <span>Medium confidence (≥60%)</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded bg-amber-100 border border-amber-200"></div>
                      <span>Low confidence (&lt;60%)</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 rounded bg-gray-100 border border-gray-200"></div>
                      <span>Regular token</span>
                    </div>
                  </div>
                </Card>
              </div>
              {renderTokenizedText()}
            </div>
          )}

          {/* Empty State */}
          {!inputText && !isLoading && (
            <div className="text-center py-12 text-muted-foreground">
              <Target className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg font-medium">Start typing to see tokenization results</p>
              <p className="text-sm">
                Enter Thai text above and watch as it gets tokenized in real-time
              </p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="comparison" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Before/After Comparison</CardTitle>
              <CardDescription>
                Compare tokenization results before and after dictionary changes
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Button
                  variant="outline"
                  onClick={() => setBeforeResult(result)}
                  disabled={!result}
                  className="h-20 flex-col gap-2"
                >
                  <Layers className="h-5 w-5" />
                  <span>Capture "Before" State</span>
                  {beforeResult && (
                    <span className="text-xs text-muted-foreground">
                      {beforeResult.tokens.length} tokens captured
                    </span>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setAfterResult(result)}
                  disabled={!result}
                  className="h-20 flex-col gap-2"
                >
                  <Layers className="h-5 w-5" />
                  <span>Capture "After" State</span>
                  {afterResult && (
                    <span className="text-xs text-muted-foreground">
                      {afterResult.tokens.length} tokens captured
                    </span>
                  )}
                </Button>
              </div>
              
              {beforeResult && afterResult && (
                <div className="pt-4">
                  <Separator className="mb-6" />
                  {renderComparisonView()}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="space-y-6">
          {renderTestHistory()}
        </TabsContent>

        <TabsContent value="batch" className="space-y-6">
          {renderBatchTesting()}
        </TabsContent>
      </Tabs>
    </div>
  );
}