'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { X, Plus } from 'lucide-react';
import { CompoundWord, CompoundWordInput } from '@/types';

const CATEGORIES = [
  { value: 'thai_japanese_compounds', label: 'Thai-Japanese Compounds' },
  { value: 'thai_english_compounds', label: 'Thai-English Compounds' },
];

const compoundWordSchema = z.object({
  word: z.string().min(1, 'Word is required').max(100, 'Word must be less than 100 characters'),
  category: z.string().min(1, 'Category is required'),
  components: z.array(z.string()).optional(),
  confidence: z.number().min(0).max(1).optional(),
  tags: z.array(z.string()).optional(),
  notes: z.string().optional(),
});

type CompoundWordFormData = z.infer<typeof compoundWordSchema>;

interface CompoundWordFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  compound?: CompoundWord | null;
  onSubmit: (data: CompoundWordInput) => Promise<void>;
  isLoading?: boolean;
}

export function CompoundWordFormDialog({
  open,
  onOpenChange,
  compound,
  onSubmit,
  isLoading = false,
}: CompoundWordFormDialogProps) {
  const [newTag, setNewTag] = React.useState('');
  const [newComponent, setNewComponent] = React.useState('');

  const form = useForm<CompoundWordFormData>({
    resolver: zodResolver(compoundWordSchema),
    defaultValues: {
      word: compound?.word || '',
      category: compound?.category || '',
      components: compound?.components || [],
      confidence: compound?.confidence || 0.9,
      tags: compound?.tags || [],
      notes: compound?.notes || '',
    },
  });

  React.useEffect(() => {
    if (compound) {
      form.reset({
        word: compound.word,
        category: compound.category,
        components: compound.components || [],
        confidence: compound.confidence,
        tags: compound.tags || [],
        notes: compound.notes || '',
      });
    } else {
      form.reset({
        word: '',
        category: '',
        components: [],
        confidence: 0.9,
        tags: [],
        notes: '',
      });
    }
  }, [compound, form]);

  const handleSubmit = async (data: CompoundWordFormData) => {
    try {
      await onSubmit(data);
      onOpenChange(false);
      form.reset();
    } catch (error) {
      console.error('Error submitting form:', error);
    }
  };

  const addTag = () => {
    if (newTag.trim()) {
      const currentTags = form.getValues('tags') || [];
      if (!currentTags.includes(newTag.trim())) {
        form.setValue('tags', [...currentTags, newTag.trim()]);
      }
      setNewTag('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    const currentTags = form.getValues('tags') || [];
    form.setValue('tags', currentTags.filter(tag => tag !== tagToRemove));
  };

  const addComponent = () => {
    if (newComponent.trim()) {
      const currentComponents = form.getValues('components') || [];
      if (!currentComponents.includes(newComponent.trim())) {
        form.setValue('components', [...currentComponents, newComponent.trim()]);
      }
      setNewComponent('');
    }
  };

  const removeComponent = (componentToRemove: string) => {
    const currentComponents = form.getValues('components') || [];
    form.setValue('components', currentComponents.filter(comp => comp !== componentToRemove));
  };

  const watchedTags = form.watch('tags') || [];
  const watchedComponents = form.watch('components') || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {compound ? 'Edit Compound Word' : 'Add New Compound Word'}
          </DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="word"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Word *</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Enter compound word"
                        className="font-thai"
                        {...field}
                      />
                    </FormControl>
                    <FormDescription>
                      The Thai compound word to add to the dictionary
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="category"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Category *</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select category" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {CATEGORIES.map((category) => (
                          <SelectItem key={category.value} value={category.value}>
                            {category.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      The category this compound word belongs to
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="confidence"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confidence Score</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      placeholder="0.9"
                      {...field}
                      onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                    />
                  </FormControl>
                  <FormDescription>
                    Confidence score between 0 and 1 (default: 0.9)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Components Section */}
            <div className="space-y-3">
              <FormLabel>Components</FormLabel>
              <div className="flex gap-2">
                <Input
                  placeholder="Add component"
                  value={newComponent}
                  onChange={(e) => setNewComponent(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addComponent())}
                  className="font-thai"
                />
                <Button type="button" onClick={addComponent} size="sm">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              {watchedComponents.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {watchedComponents.map((component) => (
                    <Badge key={component} variant="outline" className="font-thai">
                      {component}
                      <button
                        type="button"
                        onClick={() => removeComponent(component)}
                        className="ml-2 hover:text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
              <p className="text-sm text-muted-foreground">
                Optional: Break down the compound word into its components
              </p>
            </div>

            {/* Tags Section */}
            <div className="space-y-3">
              <FormLabel>Tags</FormLabel>
              <div className="flex gap-2">
                <Input
                  placeholder="Add tag"
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                />
                <Button type="button" onClick={addTag} size="sm">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              {watchedTags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {watchedTags.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                      <button
                        type="button"
                        onClick={() => removeTag(tag)}
                        className="ml-2 hover:text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
              <p className="text-sm text-muted-foreground">
                Add tags to help categorize and search for this compound word
              </p>
            </div>

            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Notes</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Add any additional notes about this compound word..."
                      className="min-h-[100px]"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Optional notes about the compound word's usage or context
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Saving...' : compound ? 'Update' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}