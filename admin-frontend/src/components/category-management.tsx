'use client';

import React, { useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  GripVertical,
  Plus,
  Edit,
  Trash2,
  MoreHorizontal,
  BarChart3,
  Filter,
  Search,
} from 'lucide-react';
import { Category, CompoundWord } from '@/types';

interface CategoryWithStats extends Category {
  compoundCount: number;
  totalUsage: number;
  averageConfidence: number;
  recentActivity: number;
}

interface SortableCategoryItemProps {
  category: CategoryWithStats;
  onEdit: (category: CategoryWithStats) => void;
  onDelete: (category: CategoryWithStats) => void;
  selectedCategories: string[];
  onCategorySelect: (categoryId: string, selected: boolean) => void;
}

function SortableCategoryItem({
  category,
  onEdit,
  onDelete,
  selectedCategories,
  onCategorySelect,
}: SortableCategoryItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: category.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const isSelected = selectedCategories.includes(category.id);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`${isDragging ? 'opacity-50' : ''}`}
    >
      <Card className={`${isSelected ? 'ring-2 ring-primary' : ''} hover:shadow-md transition-shadow`}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                className="cursor-grab hover:text-primary"
                {...attributes}
                {...listeners}
              >
                <GripVertical className="h-4 w-4" />
              </button>
              <div>
                <CardTitle className="text-lg">{category.label}</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">
                  {category.description}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge
                style={{ backgroundColor: category.color }}
                className="text-white"
              >
                {category.name}
              </Badge>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => onEdit(category)}>
                    <Edit className="h-4 w-4 mr-2" />
                    Edit Category
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="text-red-600"
                    onClick={() => onDelete(category)}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete Category
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Compounds</p>
              <p className="text-2xl font-bold">{category.compoundCount}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Total Usage</p>
              <p className="text-2xl font-bold">{category.totalUsage.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Avg Confidence</p>
              <div className="flex items-center gap-2">
                <Progress value={category.averageConfidence * 100} className="flex-1" />
                <span className="text-sm font-medium">
                  {(category.averageConfidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Recent Activity</p>
              <p className="text-2xl font-bold text-green-600">
                +{category.recentActivity}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

interface CategoryManagementProps {
  compounds: CompoundWord[];
  onCategoryUpdate?: (categories: CategoryWithStats[]) => void;
}

export function CategoryManagement({ compounds, onCategoryUpdate }: CategoryManagementProps) {
  const [categories, setCategories] = useState<CategoryWithStats[]>([
    {
      id: 'thai_japanese_compounds',
      name: 'thai_japanese_compounds',
      label: 'Thai-Japanese Compounds',
      description: 'Compound words borrowed from Japanese language',
      color: '#3b82f6',
      compoundCount: 22,
      totalUsage: 45678,
      averageConfidence: 0.94,
      recentActivity: 12,
    },
    {
      id: 'thai_english_compounds',
      name: 'thai_english_compounds',
      label: 'Thai-English Compounds',
      description: 'Compound words borrowed from English language',
      color: '#10b981',
      compoundCount: 10,
      totalUsage: 32145,
      averageConfidence: 0.91,
      recentActivity: 8,
    },
  ]);

  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'compounds' | 'usage' | 'confidence'>('name');
  const [editingCategory, setEditingCategory] = useState<CategoryWithStats | null>(null);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (active.id !== over?.id) {
      setCategories((items) => {
        const oldIndex = items.findIndex((item) => item.id === active.id);
        const newIndex = items.findIndex((item) => item.id === over?.id);

        const newCategories = arrayMove(items, oldIndex, newIndex);
        onCategoryUpdate?.(newCategories);
        return newCategories;
      });
    }
  };

  const handleCategorySelect = (categoryId: string, selected: boolean) => {
    setSelectedCategories(prev =>
      selected
        ? [...prev, categoryId]
        : prev.filter(id => id !== categoryId)
    );
  };

  const handleEditCategory = (category: CategoryWithStats) => {
    setEditingCategory(category);
  };

  const handleDeleteCategory = (category: CategoryWithStats) => {
    setCategories(prev => prev.filter(cat => cat.id !== category.id));
  };

  const filteredCategories = categories
    .filter(category =>
      category.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
      category.description?.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'compounds':
          return b.compoundCount - a.compoundCount;
        case 'usage':
          return b.totalUsage - a.totalUsage;
        case 'confidence':
          return b.averageConfidence - a.averageConfidence;
        default:
          return a.label.localeCompare(b.label);
      }
    });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Category Management</h2>
          <p className="text-muted-foreground">
            Organize and manage compound word categories with drag-and-drop
          </p>
        </div>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Category
        </Button>
      </div>

      {/* Filters and Controls */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search categories..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="name">Name</SelectItem>
                <SelectItem value="compounds">Compound Count</SelectItem>
                <SelectItem value="usage">Total Usage</SelectItem>
                <SelectItem value="confidence">Confidence</SelectItem>
              </SelectContent>
            </Select>

            <Button variant="outline" size="sm">
              <BarChart3 className="h-4 w-4 mr-2" />
              Analytics
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      {selectedCategories.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {selectedCategories.length} category(ies) selected
              </span>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm">
                  <Edit className="h-4 w-4 mr-2" />
                  Bulk Edit
                </Button>
                <Button variant="destructive" size="sm">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Selected
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sortable Category List */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={filteredCategories.map(cat => cat.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-4">
            {filteredCategories.map((category) => (
              <SortableCategoryItem
                key={category.id}
                category={category}
                onEdit={handleEditCategory}
                onDelete={handleDeleteCategory}
                selectedCategories={selectedCategories}
                onCategorySelect={handleCategorySelect}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {filteredCategories.length === 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-8">
              <p className="text-muted-foreground">No categories found</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create/Edit Category Dialog */}
      <Dialog 
        open={isCreateDialogOpen || !!editingCategory} 
        onOpenChange={(open) => {
          if (!open) {
            setIsCreateDialogOpen(false);
            setEditingCategory(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingCategory ? 'Edit Category' : 'Create New Category'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Category Name</label>
              <Input placeholder="Enter category name" />
            </div>
            <div>
              <label className="text-sm font-medium">Display Label</label>
              <Input placeholder="Enter display label" />
            </div>
            <div>
              <label className="text-sm font-medium">Description</label>
              <Input placeholder="Enter description" />
            </div>
            <div>
              <label className="text-sm font-medium">Color</label>
              <Input type="color" defaultValue="#3b82f6" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setIsCreateDialogOpen(false);
              setEditingCategory(null);
            }}>
              Cancel
            </Button>
            <Button>
              {editingCategory ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}