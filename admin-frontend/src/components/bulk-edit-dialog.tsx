'use client';

import React, { useState } from 'react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { X, Plus } from 'lucide-react';
import { CompoundWord } from '@/types';

const CATEGORIES = [
  { value: 'thai_japanese_compounds', label: 'Thai-Japanese Compounds' },
  { value: 'thai_english_compounds', label: 'Thai-English Compounds' },
];

const bulkEditSchema = z.object({
  category: z.string().optional(),
  confidence: z.number().min(0).max(1).optional(),
  addTags: z.array(z.string()).optional(),
  removeTags: z.array(z.string()).optional(),
});

type BulkEditFormData = z.infer<typeof bulkEditSchema>;

interface BulkEditDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedCompounds: CompoundWord[];
  onSubmit: (data: BulkEditFormData) => Promise<void>;
  isLoading?: boolean;
}

export function BulkEditDialog({
  open,
  onOpenChange,
  selectedCompounds,
  onSubmit,
  isLoading = false,
}: BulkEditDialogProps) {
  const [newTag, setNewTag] = useState('');
  const [removeTag, setRemoveTag] = useState('');

  const form = useForm<BulkEditFormData>({
    resolver: zodResolver(bulkEditSchema),
    defaultValues: {
      category: '',
      confidence: undefined,
      addTags: [],
      removeTags: [],
    },
  });

  const handleSubmit = async (data: BulkEditFormData) => {
    try {
      // Filter out empty values
      const cleanData = Object.fromEntries(
        Object.entries(data).filter(([_, value]) => {
          if (Array.isArray(value)) return value.length > 0;
          return value !== undefined && value !== '';
        })
      );

      await onSubmit(cleanData as BulkEditFormData);
      onOpenChange(false);
      form.reset();
    } catch (error) {
      console.error('Error submitting bulk edit:', error);
    }
  };

  const addTagToList = (field: 'addTags' | 'removeTags', tag: string) => {
    if (tag.trim()) {
      const currentTags = form.getValues(field) || [];
      if (!currentTags.includes(tag.trim())) {
        form.setValue(field, [...currentTags, tag.trim()]);
      }
      if (field === 'addTags') setNewTag('');
      if (field === 'removeTags') setRemoveTag('');
    }
  };

  const removeTagFromList = (field: 'addTags' | 'removeTags', tagToRemove: string) => {
    const currentTags = form.getValues(field) || [];
    form.setValue(field, currentTags.filter(tag => tag !== tagToRemove));
  };

  const watchedAddTags = form.watch('addTags') || [];
  const watchedRemoveTags = form.watch('removeTags') || [];

  // Get unique categories and tags from selected compounds
  const selectedCategories = [...new Set(selectedCompounds.map(c => c.category))];
  const allTags = [...new Set(selectedCompounds.flatMap(c => c.tags))];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            Bulk Edit {selectedCompounds.length} Compound Words
          </DialogTitle>
        </DialogHeader>

        <div className="mb-4 p-4 bg-muted rounded-lg">
          <h4 className="font-medium mb-2">Selected Compounds:</h4>
          <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
            {selectedCompounds.slice(0, 10).map((compound) => (
              <Badge key={compound.id} variant="outline" className="font-thai">
                {compound.word}
              </Badge>
            ))}
            {selectedCompounds.length > 10 && (
              <Badge variant="outline">
                +{selectedCompounds.length - 10} more
              </Badge>
            )}
          </div>
        </div>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="category"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Change Category</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select new category (optional)" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="">No change</SelectItem>
                      {CATEGORIES.map((category) => (
                        <SelectItem key={category.value} value={category.value}>
                          {category.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    Current categories: {selectedCategories.join(', ')}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="confidence"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Update Confidence Score</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      placeholder="Leave empty for no change"
                      {...field}
                      onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : undefined)}
                      value={field.value || ''}
                    />
                  </FormControl>
                  <FormDescription>
                    Set a new confidence score between 0 and 1 for all selected compounds
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Add Tags Section */}
            <div className="space-y-3">
              <FormLabel>Add Tags</FormLabel>
              <div className="flex gap-2">
                <Input
                  placeholder="Add tag to all selected compounds"
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTagToList('addTags', newTag))}
                />
                <Button 
                  type="button" 
                  onClick={() => addTagToList('addTags', newTag)} 
                  size="sm"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              {watchedAddTags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {watchedAddTags.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                      <button
                        type="button"
                        onClick={() => removeTagFromList('addTags', tag)}
                        className="ml-2 hover:text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
              <p className="text-sm text-muted-foreground">
                These tags will be added to all selected compounds
              </p>
            </div>

            {/* Remove Tags Section */}
            <div className="space-y-3">
              <FormLabel>Remove Tags</FormLabel>
              <div className="flex gap-2">
                <Select onValueChange={(value) => addTagToList('removeTags', value)}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select tag to remove" />
                  </SelectTrigger>
                  <SelectContent>
                    {allTags.map((tag) => (
                      <SelectItem key={tag} value={tag}>
                        {tag}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {watchedRemoveTags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {watchedRemoveTags.map((tag) => (
                    <Badge key={tag} variant="destructive">
                      {tag}
                      <button
                        type="button"
                        onClick={() => removeTagFromList('removeTags', tag)}
                        className="ml-2 hover:text-destructive-foreground"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
              <p className="text-sm text-muted-foreground">
                These tags will be removed from all selected compounds that have them
              </p>
            </div>

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
                {isLoading ? 'Applying Changes...' : 'Apply Changes'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}