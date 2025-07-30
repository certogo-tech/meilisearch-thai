// User and Authentication Types
export interface UserInfo {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  permissions: Permission[];
  lastLogin: Date;
}

export enum UserRole {
  ADMIN = 'admin',
  EDITOR = 'editor',
  VIEWER = 'viewer',
}

export enum Permission {
  VIEW_COMPOUNDS = 'view_compounds',
  EDIT_COMPOUNDS = 'edit_compounds',
  DELETE_COMPOUNDS = 'delete_compounds',
  BULK_OPERATIONS = 'bulk_operations',
  VIEW_ANALYTICS = 'view_analytics',
  SYSTEM_ADMIN = 'system_admin',
}

export interface AuthState {
  user: UserInfo | null;
  token: string | null;
  permissions: Permission[];
  isAuthenticated: boolean;
  isLoading: boolean;
}

// Compound Word Types
export interface CompoundWord {
  id: string;
  word: string;
  category: string;
  components?: string[];
  confidence: number;
  usageCount: number;
  lastUsed?: Date;
  createdAt: Date;
  updatedAt: Date;
  createdBy: string;
  tags: string[];
  notes?: string;
}

export interface CompoundWordInput {
  word: string;
  category: string;
  components?: string[];
  confidence?: number;
  tags?: string[];
  notes?: string;
}

export interface Category {
  id: string;
  name: string;
  label: string;
  description?: string;
  color?: string;
}

// System Health Types
export interface SystemHealthStatus {
  status: 'healthy' | 'warning' | 'error';
  message: string;
  lastCheck: Date;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}