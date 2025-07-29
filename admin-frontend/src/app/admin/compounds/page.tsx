'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { DateRangePicker } from '@/components/ui/date-picker';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { Checkbox } from '@/components/ui/checkbox';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  Search,
  Plus,
  MoreHorizontal,
  ArrowUpDown,
  Eye,
  Edit,
  Trash2,
  Download,
  Upload,
  Check,
  X,
} from 'lucide-react';
import { CompoundWord, FilterOptions, PaginatedResponse, CompoundWordInput } from '@/types';
import { format } from 'date-fns';
import { CompoundWordFormDialog } from '@/components/compound-word-form-dialog';
import { DeleteCompoundDialog } from '@/components/delete-compound-dialog';
import { BulkDeleteDialog } from '@/components/bulk-delete-dialog';
import { BulkEditDialog } from '@/components/bulk-edit-dialog';
import { CategoryManagement } from '@/components/category-management';
import { MultiSelect } from '@/components/ui/multi-select';
import { toast } from 'sonner';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

const CATEGORIES = [
  { value: 'all', label: 'All Categories' },
  { value: 'thai_japanese_compounds', label: 'Thai-Japanese Compounds' },
  { value: 'thai_english_compounds', label: 'Thai-English Compounds' },
];

const SORT_OPTIONS = [
  { value: 'word', label: 'Word' },
  { value: 'category', label: 'Category' },
  { value: 'usageCount', label: 'Usage Count' },
  { value: 'createdAt', label: 'Created Date' },
  { value: 'updatedAt', label: 'Updated Date' },
];

// Schema for inline editing
const inlineEditSchema = z.object({
  word: z.string().min(1, 'Word is required').max(100, 'Word must be less than 100 characters'),
  category: z.string().min(1, 'Category is required'),
  confidence: z.number().min(0).max(1),
});

type InlineEditFormData = z.infer<typeof inlineEditSchema>;

async function fetchCompounds(filters: Partial<FilterOptions> & { page: number; limit: number }) {
  const params = new URLSearchParams();
  
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      if (key === 'dateRange' && value && typeof value === 'object') {
        if (value.start) params.append('startDate', value.start.toISOString());
        if (value.end) params.append('endDate', value.end.toISOString());
      } else {
        params.append(key, String(value));
      }
    }
  });

  const response = await fetch(`/api/compounds?${params}`);
  if (!response.ok) {
    throw new Error('Failed to fetch compounds');
  }
  return response.json() as Promise<PaginatedResponse<CompoundWord>>;
}

export default function CompoundsPage() {
  const [filters, setFilters] = useState<Partial<FilterOptions>>({
    search: '',
    category: 'all',
    minUsageCount: 0,
    dateRange: { start: null, end: null },
    sortBy: 'updatedAt',
    sortOrder: 'desc',
  });
  
  const [page, setPage] = useState(1);
  const [limit] = useState(50);
  const [selectedCompounds, setSelectedCompounds] = useState<string[]>([]);
  const [selectedCompound, setSelectedCompound] = useState<CompoundWord | null>(null);
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [editingCompound, setEditingCompound] = useState<CompoundWord | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deletingCompound, setDeletingCompound] = useState<CompoundWord | null>(null);
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  const [bulkEditDialogOpen, setBulkEditDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [inlineEditingId, setInlineEditingId] = useState<string | null>(null);
  const [inlineEditPopoverOpen, setInlineEditPopoverOpen] = useState(false);

  // Form for inline editing
  const inlineEditForm = useForm<InlineEditFormData>({
    resolver: zodResolver(inlineEditSchema),
    defaultValues: {
      word: '',
      category: '',
      confidence: 0.9,
    },
  });

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['compounds', filters, page, limit],
    queryFn: () => fetchCompounds({ ...filters, page, limit }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const compounds = data?.data || [];
  const pagination = data?.pagination;

  const handleFilterChange = (key: keyof FilterOptions, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1); // Reset to first page when filters change
  };

  const handleSort = (field: string) => {
    const newSortOrder = filters.sortBy === field && filters.sortOrder === 'asc' ? 'desc' : 'asc';
    setFilters(prev => ({
      ...prev,
      sortBy: field as any,
      sortOrder: newSortOrder,
    }));
  };

  const handleSelectCompound = (compoundId: string, checked: boolean) => {
    setSelectedCompounds(prev => 
      checked 
        ? [...prev, compoundId]
        : prev.filter(id => id !== compoundId)
    );
  };

  const handleSelectAll = (checked: boolean) => {
    setSelectedCompounds(checked ? compounds.map(c => c.id) : []);
  };

  const getCategoryLabel = (category: string) => {
    return CATEGORIES.find(cat => cat.value === category)?.label || category;
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'thai_japanese_compounds':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'thai_english_compounds':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  const handleCreateCompound = async (data: CompoundWordInput) => {
    setIsSubmitting(true);
    try {
      const response = await fetch('/api/compounds', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Failed to create compound');
      }

      toast.success('Compound word created successfully');
      refetch();
    } catch (error) {
      toast.error('Failed to create compound word');
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateCompound = async (data: CompoundWordInput) => {
    if (!editingCompound) return;
    
    setIsSubmitting(true);
    try {
      const response = await fetch(`/api/compounds/${editingCompound.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Failed to update compound');
      }

      toast.success('Compound word updated successfully');
      refetch();
      setEditingCompound(null);
    } catch (error) {
      toast.error('Failed to update compound word');
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteCompound = async () => {
    if (!deletingCompound) return;

    setIsSubmitting(true);
    try {
      const response = await fetch(`/api/compounds/${deletingCompound.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete compound');
      }

      toast.success('Compound word deleted successfully');
      refetch();
      setDeletingCompound(null);
    } catch (error) {
      toast.error('Failed to delete compound word');
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleBulkDelete = async () => {
    setIsSubmitting(true);
    try {
      const response = await fetch('/api/compounds/bulk-delete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ids: selectedCompounds }),
      });

      if (!response.ok) {
        throw new Error('Failed to delete compounds');
      }

      toast.success(`${selectedCompounds.length} compound words deleted successfully`);
      setSelectedCompounds([]);
      refetch();
    } catch (error) {
      toast.error('Failed to delete compound words');
      throw error;
    } finally {
      setIsSubmitting(false);
    }
  };

  const openCreateDialog = () => {
    setEditingCompound(null);
    setFormDialogOpen(true);
  };

  const openEditDialog = (compound: CompoundWord) => {
    setEditingCompound(compound);
    setFormDialogOpen(true);
  };

  const openDeleteDialog = (compound: CompoundWord) => {
    setDeletingCompound(compound);
    setDeleteDialogOpen(true);
  };

  const openBulkDeleteDialog = () => {
    setBulkDeleteDialogOpen(true);
  };

  const startInlineEdit = (compound: CompoundWord) => {
    setInlineEditingId(compound.id);
    inlineEditForm.reset({
      word: compound.word,
      category: compound.category,
      confidence: compound.confidence,
    });
    setInlineEditPopoverOpen(true);
  };

  const cancelInlineEdit = () => {
    setInlineEditingId(null);
    setInlineEditPopoverOpen(false);
    inlineEditForm.reset();
  };

  const handleInlineEditSubmit = async (data: InlineEditFormData) => {
    if (!inlineEditingId) return;
    
    setIsSubmitting(true);
    try {
      const response = await fetch(`/api/compounds/${inlineEditingId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Failed to update compound');
      }

      toast.success('Compound word updated successfully');
      refetch();
      cancelInlineEdit();
    } catch (error) {
      toast.error('Failed to update compound word');
      console.error('Error updating compound:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Bulk operation handlers
  const handleBulkEdit = async (data: any) => {
    setIsSubmitting(true);
    try {
      const response = await fetch('/api/compounds/bulk-edit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ids: selectedCompounds,
          updates: data,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to update compounds');
      }

      const result = await response.json();
      toast.success(`Successfully updated ${result.updatedCount} compound words`);
      setSelectedCompounds([]);
      refetch();
    } catch (error) {
      toast.error('Failed to update compound words');
      console.error('Error bulk editing compounds:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const openBulkEditDialog = () => {
    setBulkEditDialogOpen(true);
  };

  const handleExportSelected = (format: 'json' | 'csv' | 'xlsx') => {
    const selectedData = compounds.filter(compound => 
      selectedCompounds.includes(compound.id)
    );
    
    if (format === 'json') {
      const dataStr = JSON.stringify(selectedData, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `compounds_${new Date().toISOString().split('T')[0]}.json`;
      link.click();
      URL.revokeObjectURL(url);
      toast.success(`Exported ${selectedData.length} compounds as JSON`);
    } else {
      toast.info(`Export as ${format.toUpperCase()} feature coming soon`);
    }
  };

  if (error) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-red-600">
              Error loading compounds: {error.message}
              <Button onClick={() => refetch()} className="ml-4">
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dictionary Management</h1>
          <p className="text-muted-foreground">
            Manage Thai compound words and categories for the tokenizer system
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="compounds" className="space-y-6">
        <TabsList>
          <TabsTrigger value="compounds">Compound Words</TabsTrigger>
          <TabsTrigger value="categories">Categories</TabsTrigger>
        </TabsList>

        <TabsContent value="compounds" className="space-y-6">
          {/* Add Compound Button */}
          <div className="flex justify-end">
            <Button size="sm" onClick={openCreateDialog}>
              <Plus className="h-4 w-4 mr-2" />
              Add Compound
            </Button>
          </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search compound words..."
                  value={filters.search || ''}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <MultiSelect
              options={CATEGORIES.filter(cat => cat.value !== 'all')}
              selected={filters.category && filters.category !== 'all' ? [filters.category] : []}
              onChange={(selected) => handleFilterChange('category', selected.length > 0 ? selected[0] : 'all')}
              placeholder="Select categories"
              className="w-[200px]"
            />

            <Input
              type="number"
              placeholder="Min usage"
              value={filters.minUsageCount || ''}
              onChange={(e) => handleFilterChange('minUsageCount', parseInt(e.target.value) || 0)}
              className="w-[120px]"
            />

            <DateRangePicker
              dateRange={filters.dateRange}
              onDateRangeChange={(range) => handleFilterChange('dateRange', range)}
              placeholder="Date range"
              className="w-[200px]"
            />

            <Select
              value={filters.sortBy || 'updatedAt'}
              onValueChange={(value) => handleFilterChange('sortBy', value)}
            >
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleSort(filters.sortBy || 'updatedAt')}
            >
              <ArrowUpDown className="h-4 w-4" />
              {filters.sortOrder === 'asc' ? 'Asc' : 'Desc'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      {selectedCompounds.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {selectedCompounds.length} compound(s) selected
              </span>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={openBulkEditDialog}>
                  <Edit className="h-4 w-4 mr-2" />
                  Bulk Edit
                </Button>
                
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Download className="h-4 w-4 mr-2" />
                      Export
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => handleExportSelected('json')}>
                      Export as JSON
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleExportSelected('csv')}>
                      Export as CSV
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleExportSelected('xlsx')}>
                      Export as Excel
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                
                <Button variant="destructive" size="sm" onClick={openBulkDeleteDialog}>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Selected
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Table */}
      <Card>
        <CardContent className="pt-6">
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[50px]">
                    <Checkbox
                      checked={selectedCompounds.length === compounds.length && compounds.length > 0}
                      onCheckedChange={handleSelectAll}
                    />
                  </TableHead>
                  <TableHead 
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('word')}
                  >
                    <div className="flex items-center">
                      Word
                      <ArrowUpDown className="ml-2 h-4 w-4" />
                    </div>
                  </TableHead>
                  <TableHead 
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('category')}
                  >
                    <div className="flex items-center">
                      Category
                      <ArrowUpDown className="ml-2 h-4 w-4" />
                    </div>
                  </TableHead>
                  <TableHead 
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('usageCount')}
                  >
                    <div className="flex items-center">
                      Usage Count
                      <ArrowUpDown className="ml-2 h-4 w-4" />
                    </div>
                  </TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Tags</TableHead>
                  <TableHead 
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort('updatedAt')}
                  >
                    <div className="flex items-center">
                      Last Updated
                      <ArrowUpDown className="ml-2 h-4 w-4" />
                    </div>
                  </TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8">
                      Loading compounds...
                    </TableCell>
                  </TableRow>
                ) : compounds.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-8">
                      No compounds found
                    </TableCell>
                  </TableRow>
                ) : (
                  compounds.map((compound) => (
                    <TableRow key={compound.id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedCompounds.includes(compound.id)}
                          onCheckedChange={(checked) => 
                            handleSelectCompound(compound.id, checked as boolean)
                          }
                        />
                      </TableCell>
                      <TableCell className="font-medium font-thai">
                        <Popover 
                          open={inlineEditingId === compound.id && inlineEditPopoverOpen} 
                          onOpenChange={(open) => {
                            if (!open) {
                              cancelInlineEdit();
                            }
                          }}
                        >
                          <PopoverTrigger asChild>
                            <Button 
                              variant="ghost" 
                              className="h-auto p-1 font-thai justify-start"
                              onClick={() => startInlineEdit(compound)}
                            >
                              {compound.word}
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-80">
                            <Form {...inlineEditForm}>
                              <form onSubmit={inlineEditForm.handleSubmit(handleInlineEditSubmit)} className="space-y-4">
                                <div className="space-y-2">
                                  <h4 className="font-medium">Quick Edit</h4>
                                  <p className="text-sm text-muted-foreground">
                                    Make quick changes to this compound word.
                                  </p>
                                </div>
                                
                                <FormField
                                  control={inlineEditForm.control}
                                  name="word"
                                  render={({ field }) => (
                                    <FormItem>
                                      <FormLabel>Word</FormLabel>
                                      <FormControl>
                                        <Input
                                          placeholder="Enter compound word"
                                          className="font-thai"
                                          {...field}
                                        />
                                      </FormControl>
                                      <FormMessage />
                                    </FormItem>
                                  )}
                                />

                                <FormField
                                  control={inlineEditForm.control}
                                  name="category"
                                  render={({ field }) => (
                                    <FormItem>
                                      <FormLabel>Category</FormLabel>
                                      <Select onValueChange={field.onChange} value={field.value}>
                                        <FormControl>
                                          <SelectTrigger>
                                            <SelectValue placeholder="Select category" />
                                          </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                          {CATEGORIES.filter(cat => cat.value !== 'all').map((category) => (
                                            <SelectItem key={category.value} value={category.value}>
                                              {category.label}
                                            </SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                      <FormMessage />
                                    </FormItem>
                                  )}
                                />

                                <FormField
                                  control={inlineEditForm.control}
                                  name="confidence"
                                  render={({ field }) => (
                                    <FormItem>
                                      <FormLabel>Confidence</FormLabel>
                                      <FormControl>
                                        <Input
                                          type="number"
                                          min="0"
                                          max="1"
                                          step="0.01"
                                          {...field}
                                          onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                                        />
                                      </FormControl>
                                      <FormMessage />
                                    </FormItem>
                                  )}
                                />

                                <div className="flex justify-end space-x-2">
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="sm"
                                    onClick={cancelInlineEdit}
                                    disabled={isSubmitting}
                                  >
                                    <X className="h-4 w-4 mr-1" />
                                    Cancel
                                  </Button>
                                  <Button
                                    type="submit"
                                    size="sm"
                                    disabled={isSubmitting}
                                  >
                                    <Check className="h-4 w-4 mr-1" />
                                    {isSubmitting ? 'Saving...' : 'Save'}
                                  </Button>
                                </div>
                              </form>
                            </Form>
                          </PopoverContent>
                        </Popover>
                      </TableCell>
                      <TableCell>
                        <Badge className={getCategoryColor(compound.category)}>
                          {getCategoryLabel(compound.category)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {compound.usageCount.toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center">
                          <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${compound.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-sm text-muted-foreground">
                            {(compound.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {compound.tags.slice(0, 2).map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-xs">
                              {tag}
                            </Badge>
                          ))}
                          {compound.tags.length > 2 && (
                            <Badge variant="secondary" className="text-xs">
                              +{compound.tags.length - 2}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {format(compound.updatedAt, 'MMM dd, yyyy')}
                      </TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem
                              onClick={() => setSelectedCompound(compound)}
                            >
                              <Eye className="h-4 w-4 mr-2" />
                              View Details
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => startInlineEdit(compound)}>
                              <Edit className="h-4 w-4 mr-2" />
                              Quick Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => openEditDialog(compound)}>
                              <Edit className="h-4 w-4 mr-2" />
                              Full Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              className="text-red-600"
                              onClick={() => openDeleteDialog(compound)}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {pagination && (
            <div className="flex items-center justify-between mt-4">
              <div className="text-sm text-muted-foreground">
                Showing {((page - 1) * limit) + 1} to {Math.min(page * limit, pagination.total)} of{' '}
                {pagination.total} compounds
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <span className="text-sm">
                  Page {page} of {pagination.totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(p => p + 1)}
                  disabled={!pagination.hasMore}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Detail Sheet */}
      <Sheet open={!!selectedCompound} onOpenChange={() => setSelectedCompound(null)}>
        <SheetContent className="w-[400px] sm:w-[540px]">
          <SheetHeader>
            <SheetTitle>Compound Word Details</SheetTitle>
          </SheetHeader>
          {selectedCompound && (
            <div className="mt-6 space-y-6">
              <div>
                <h3 className="text-lg font-semibold font-thai mb-2">
                  {selectedCompound.word}
                </h3>
                <Badge className={getCategoryColor(selectedCompound.category)}>
                  {getCategoryLabel(selectedCompound.category)}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Usage Count
                  </label>
                  <p className="text-2xl font-bold">
                    {selectedCompound.usageCount.toLocaleString()}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Confidence
                  </label>
                  <p className="text-2xl font-bold">
                    {(selectedCompound.confidence * 100).toFixed(1)}%
                  </p>
                </div>
              </div>

              {selectedCompound.components && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Components
                  </label>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {selectedCompound.components.map((component, index) => (
                      <Badge key={index} variant="outline" className="font-thai">
                        {component}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  Tags
                </label>
                <div className="flex flex-wrap gap-2 mt-1">
                  {selectedCompound.tags.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Created
                  </label>
                  <p className="text-sm">
                    {format(selectedCompound.createdAt, 'PPP')} by {selectedCompound.createdBy}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Last Updated
                  </label>
                  <p className="text-sm">
                    {format(selectedCompound.updatedAt, 'PPP')}
                  </p>
                </div>
                {selectedCompound.lastUsed && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground">
                      Last Used
                    </label>
                    <p className="text-sm">
                      {format(selectedCompound.lastUsed, 'PPP')}
                    </p>
                  </div>
                )}
              </div>

              {selectedCompound.notes && (
                <div>
                  <label className="text-sm font-medium text-muted-foreground">
                    Notes
                  </label>
                  <p className="text-sm mt-1 p-3 bg-muted rounded-md">
                    {selectedCompound.notes}
                  </p>
                </div>
              )}

              <div className="flex gap-2 pt-4">
                <Button className="flex-1">
                  <Edit className="h-4 w-4 mr-2" />
                  Edit Compound
                </Button>
                <Button variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
        </TabsContent>

        <TabsContent value="categories">
          <CategoryManagement 
            compounds={compounds} 
            onCategoryUpdate={(categories) => {
              console.log('Categories updated:', categories);
            }}
          />
        </TabsContent>
      </Tabs>

      {/* Form Dialog */}
      <CompoundWordFormDialog
        open={formDialogOpen}
        onOpenChange={setFormDialogOpen}
        compound={editingCompound}
        onSubmit={editingCompound ? handleUpdateCompound : handleCreateCompound}
        isLoading={isSubmitting}
      />

      {/* Delete Dialog */}
      <DeleteCompoundDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        compound={deletingCompound}
        onConfirm={handleDeleteCompound}
        isLoading={isSubmitting}
      />

      {/* Bulk Delete Dialog */}
      <BulkDeleteDialog
        open={bulkDeleteDialogOpen}
        onOpenChange={setBulkDeleteDialogOpen}
        selectedCount={selectedCompounds.length}
        onConfirm={handleBulkDelete}
        isLoading={isSubmitting}
      />

      {/* Bulk Edit Dialog */}
      <BulkEditDialog
        open={bulkEditDialogOpen}
        onOpenChange={setBulkEditDialogOpen}
        selectedCompounds={compounds.filter(c => selectedCompounds.includes(c.id))}
        onSubmit={handleBulkEdit}
        isLoading={isSubmitting}
      />
    </div>
  );
}