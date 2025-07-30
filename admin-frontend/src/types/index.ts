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

export interface LoginCredentials {
  username: string;
  password: string;
  rememberMe?: boolean;
}

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  user: UserInfo;
  expiresIn: number;
}

export interface TokenPayload {
  sub: string;
  username: string;
  email: string;
  role: UserRole;
  permissions: Permission[];
  exp: number;
  iat: number;
}

export interface RefreshTokenRequest {
  refreshToken: string;
}

export interface PasswordChangeRequest {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export interface UserProfileUpdateRequest {
  email?: string;
  username?: string;
}

export interface PasswordValidationResult {
  isValid: boolean;
  errors: string[];
  strength: 'weak' | 'medium' | 'strong';
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

// Filtering and Pagination Types
export interface FilterOptions {
  search: string;
  category: string;
  minUsageCount: number;
  dateRange: DateRange;
  sortBy: SortField;
  sortOrder: 'asc' | 'desc';
}

export interface DateRange {
  start: Date | null;
  end: Date | null;
}

export type SortField =
  | 'word'
  | 'category'
  | 'usageCount'
  | 'createdAt'
  | 'updatedAt';

export interface PaginationState {
  page: number;
  limit: number;
  total: number;
  hasMore: boolean;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasMore: boolean;
  };
}

// System Health Types
export interface SystemHealthStatus {
  status: 'healthy' | 'warning' | 'error';
  message: string;
  lastCheck: Date;
}

// Notification Types
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
}

// Audit Log Types
export interface AuditLog {
  id: string;
  userId: string;
  username: string;
  action: AuditAction;
  resource: string;
  resourceId?: string;
  details: Record<string, any>;
  ipAddress: string;
  userAgent: string;
  timestamp: Date;
}

export enum AuditAction {
  LOGIN = 'login',
  LOGOUT = 'logout',
  PASSWORD_CHANGE = 'password_change',
  PROFILE_UPDATE = 'profile_update',
  ROLE_ASSIGNMENT = 'role_assignment',
  COMPOUND_CREATE = 'compound_create',
  COMPOUND_UPDATE = 'compound_update',
  COMPOUND_DELETE = 'compound_delete',
  BULK_IMPORT = 'bulk_import',
  BULK_EXPORT = 'bulk_export',
  SYSTEM_CONFIG = 'system_config',
}

export interface AuditLogFilters {
  userId?: string;
  action?: AuditAction;
  resource?: string;
  startDate?: Date;
  endDate?: Date;
  search?: string;
}

// Tokenization Testing Types
export interface TokenInfo {
  text: string;
  startIndex: number;
  endIndex: number;
  isCompound: boolean;
  confidence: number;
  category?: string;
}

export interface CompoundMatch {
  word: string;
  startIndex: number;
  endIndex: number;
  confidence: number;
  components?: string[];
}

export interface TokenizationResult {
  originalText: string;
  tokens: TokenInfo[];
  wordBoundaries: number[];
  compoundsFound: CompoundMatch[];
  processingTime: number;
  engine: string;
  confidence: number;
  alternatives?: TokenizationResult[];
}

export interface TokenizationOptions {
  includeAlternatives?: boolean;
  engine?: string;
  preserveWhitespace?: boolean;
}

export interface TestResult {
  id: string;
  text: string;
  result: TokenizationResult;
  timestamp: Date;
  saved: boolean;
}

export interface TokenizationMetrics {
  totalTokens: number;
  compoundTokens: number;
  processingTime: number;
  confidence: number;
  accuracy?: number;
  textLength?: number;
  tokensPerSecond?: number;
  charactersPerSecond?: number;
}