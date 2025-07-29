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
import { Checkbox } from '@/components/ui/checkbox';
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
  TrendingUp,
  Activity,
  Users,
  Clock,
} from 'lucide-react';
import { Category, CompoundWord } from '@/types';
import { MultiSelect } from '@/components/ui/multi-select';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';

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
      className={`${isDragging ? 'opacity-50 scale-105 rotate-2 shadow-lg' : ''} transition-all duration-200`}
    >
      <Card className={`${isSelected ? 'ring-2 ring-primary' : ''} ${isDragging ? 'shadow-2xl border-primary' : ''} hover:shadow-md transition-all duration-200`}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Checkbox
                checked={isSelected}
                onCheckedChange={(checked) => onCategorySelect(category.id, !!checked)}
              />
              <button
                className="cursor-grab hover:text-primary hover:bg-muted/50 p-1 rounded transition-colors"
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
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [selectedCategoriesForFilter, setSelectedCategoriesForFilter] = useState<string[]>([]);

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
    .filter(category => {
      const matchesSearch = category.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
        category.description?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesFilter = selectedCategoriesForFilter.length === 0 || 
        selectedCategoriesForFilter.includes(category.id);
      return matchesSearch && matchesFilter;
    })
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

  // Analytics data for charts
  const analyticsData = {
    categoryUsage: categories.map(cat => ({
      name: cat.label,
      compounds: cat.compoundCount,
      usage: cat.totalUsage,
      confidence: cat.averageConfidence * 100,
      activity: cat.recentActivity,
    })),
    totalStats: {
      totalCategories: categories.length,
      totalCompounds: categories.reduce((sum, cat) => sum + cat.compoundCount, 0),
      totalUsage: categories.reduce((sum, cat) => sum + cat.totalUsage, 0),
      averageConfidence: categories.reduce((sum, cat) => sum + cat.averageConfidence, 0) / categories.length,
    },
    trendData: [
      { month: 'Jan', compounds: 28, usage: 45000 },
      { month: 'Feb', compounds: 30, usage: 52000 },
      { month: 'Mar', compounds: 32, usage: 58000 },
      { month: 'Apr', compounds: 32, usage: 61000 },
      { month: 'May', compounds: 32, usage: 65000 },
      { month: 'Jun', compounds: 32, usage: 77823 },
    ],
  };

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

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

            <MultiSelect
              options={categories.map(cat => ({ label: cat.label, value: cat.id }))}
              selected={selectedCategoriesForFilter}
              onChange={setSelectedCategoriesForFilter}
              placeholder="Filter categories..."
              className="w-[250px]"
            />

            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setShowAnalytics(!showAnalytics)}
            >
              <BarChart3 className="h-4 w-4 mr-2" />
              {showAnalytics ? 'Hide Analytics' : 'Show Analytics'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Analytics Dashboard */}
      {showAnalytics && (
        <div className="space-y-6">
          {/* Overview Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Categories</p>
                    <p className="text-2xl font-bold">{analyticsData.totalStats.totalCategories}</p>
                  </div>
                  <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center">
                    <Filter className="h-4 w-4 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Compounds</p>
                    <p className="text-2xl font-bold">{analyticsData.totalStats.totalCompounds}</p>
                  </div>
                  <div className="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
                    <Activity className="h-4 w-4 text-green-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Usage</p>
                    <p className="text-2xl font-bold">{analyticsData.totalStats.totalUsage.toLocaleString()}</p>
                  </div>
                  <div className="h-8 w-8 rounded-full bg-orange-100 flex items-center justify-center">
                    <Users className="h-4 w-4 text-orange-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Avg Confidence</p>
                    <p className="text-2xl font-bold">{(analyticsData.totalStats.averageConfidence * 100).toFixed(1)}%</p>
                  </div>
                  <div className="h-8 w-8 rounded-full bg-purple-100 flex items-center justify-center">
                    <TrendingUp className="h-4 w-4 text-purple-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Category Usage Bar Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Category Usage Distribution</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Compound count and usage by category
                </p>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={analyticsData.categoryUsage}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="name" 
                      tick={{ fontSize: 12 }}
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="compounds" fill="#3b82f6" name="Compounds" />
                    <Bar dataKey="activity" fill="#10b981" name="Recent Activity" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Category Distribution Pie Chart */}
            <Card>
              <CardHeader>
                <CardTitle>Category Distribution</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Proportion of compounds by category
                </p>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={analyticsData.categoryUsage}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="compounds"
                    >
                      {analyticsData.categoryUsage.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Usage Trends Line Chart */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Usage Trends Over Time</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Monthly compound usage and growth trends
                </p>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={analyticsData.trendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="month" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Bar yAxisId="left" dataKey="compounds" fill="#3b82f6" name="Compounds" />
                    <Line 
                      yAxisId="right" 
                      type="monotone" 
                      dataKey="usage" 
                      stroke="#10b981" 
                      strokeWidth={3}
                      name="Usage"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Category Performance Table */}
          <Card>
            <CardHeader>
              <CardTitle>Category Performance Metrics</CardTitle>
              <p className="text-sm text-muted-foreground">
                Detailed performance analysis for each category
              </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">Category</th>
                      <th className="text-right p-2">Compounds</th>
                      <th className="text-right p-2">Usage</th>
                      <th className="text-right p-2">Confidence</th>
                      <th className="text-right p-2">Recent Activity</th>
                      <th className="text-center p-2">Trend</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analyticsData.categoryUsage.map((category, index) => (
                      <tr key={index} className="border-b hover:bg-muted/50">
                        <td className="p-2">
                          <div className="flex items-center gap-2">
                            <div 
                              className="w-3 h-3 rounded-full" 
                              style={{ backgroundColor: COLORS[index % COLORS.length] }}
                            />
                            {category.name}
                          </div>
                        </td>
                        <td className="text-right p-2 font-medium">{category.compounds}</td>
                        <td className="text-right p-2">{category.usage.toLocaleString()}</td>
                        <td className="text-right p-2">
                          <div className="flex items-center justify-end gap-2">
                            <Progress value={category.confidence} className="w-16" />
                            <span className="text-sm">{category.confidence.toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="text-right p-2">
                          <span className="text-green-600 font-medium">+{category.activity}</span>
                        </td>
                        <td className="text-center p-2">
                          <TrendingUp className="h-4 w-4 text-green-600 mx-auto" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

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