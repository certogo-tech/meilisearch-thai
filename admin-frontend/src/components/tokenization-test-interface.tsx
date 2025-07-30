'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Loader2, Clock, Target, Zap, Hash, Activity, BarChart3, RefreshCw, Copy, CheckCircle2, AlertCircle } from 'lucide-react';
import { TokenizationResult, TokenizationMetrics } from '@/types';
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

  // Debounce input to avoid excessive API calls (300ms for better responsiveness)
  const debouncedText = useDebounce(inputText, 300);

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

  return (
    <div className={`space-y-6 ${className}`}>
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
    </div>
  );
}