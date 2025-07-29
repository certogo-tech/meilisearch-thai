'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ProtectedRoute } from '@/components/protected-route';
import { DashboardLayout } from '@/components/dashboard-layout';
import { useAuth } from '@/hooks/use-auth';
import { AuditLog, AuditAction, Permission } from '@/types';
import { 
  Search, 
  Shield, 
  User, 
  Key, 
  Settings, 
  FileText, 
  Download,
  Calendar,
  Clock
} from 'lucide-react';

const actionIcons = {
  [AuditAction.LOGIN]: User,
  [AuditAction.LOGOUT]: User,
  [AuditAction.PASSWORD_CHANGE]: Key,
  [AuditAction.PROFILE_UPDATE]: User,
  [AuditAction.ROLE_ASSIGNMENT]: Shield,
  [AuditAction.COMPOUND_CREATE]: FileText,
  [AuditAction.COMPOUND_UPDATE]: FileText,
  [AuditAction.COMPOUND_DELETE]: FileText,
  [AuditAction.BULK_IMPORT]: Download,
  [AuditAction.BULK_EXPORT]: Download,
  [AuditAction.SYSTEM_CONFIG]: Settings,
};

const actionColors = {
  [AuditAction.LOGIN]: 'bg-green-100 text-green-800 border-green-200',
  [AuditAction.LOGOUT]: 'bg-gray-100 text-gray-800 border-gray-200',
  [AuditAction.PASSWORD_CHANGE]: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  [AuditAction.PROFILE_UPDATE]: 'bg-blue-100 text-blue-800 border-blue-200',
  [AuditAction.ROLE_ASSIGNMENT]: 'bg-red-100 text-red-800 border-red-200',
  [AuditAction.COMPOUND_CREATE]: 'bg-green-100 text-green-800 border-green-200',
  [AuditAction.COMPOUND_UPDATE]: 'bg-blue-100 text-blue-800 border-blue-200',
  [AuditAction.COMPOUND_DELETE]: 'bg-red-100 text-red-800 border-red-200',
  [AuditAction.BULK_IMPORT]: 'bg-purple-100 text-purple-800 border-purple-200',
  [AuditAction.BULK_EXPORT]: 'bg-purple-100 text-purple-800 border-purple-200',
  [AuditAction.SYSTEM_CONFIG]: 'bg-orange-100 text-orange-800 border-orange-200',
};

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAction, setSelectedAction] = useState<string>('all');
  const [selectedUser, setSelectedUser] = useState<string>('all');
  const { user } = useAuth();

  useEffect(() => {
    fetchAuditLogs();
  }, [selectedAction, selectedUser]);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      if (selectedAction !== 'all') {
        params.append('action', selectedAction);
      }
      
      if (selectedUser !== 'all') {
        params.append('userId', selectedUser);
      }
      
      if (searchTerm) {
        params.append('search', searchTerm);
      }

      const response = await fetch(`/api/audit/logs?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs);
      } else {
        console.error('Failed to fetch audit logs');
      }
    } catch (error) {
      console.error('Error fetching audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    fetchAuditLogs();
  };

  const formatTimestamp = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(new Date(date));
  };

  const formatDetails = (details: Record<string, any>) => {
    return Object.entries(details)
      .filter(([key, value]) => value !== undefined && value !== null)
      .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
      .join(', ');
  };

  const uniqueUsers = Array.from(new Set(logs.map(log => log.username)));

  return (
    <ProtectedRoute requiredPermissions={[Permission.SYSTEM_ADMIN]}>
      <DashboardLayout>
        <div>
        <div className="mb-8">
          <h1 className="text-4xl font-bold tracking-tight">Audit Logs</h1>
          <p className="text-muted-foreground">
            View system activity and security events
          </p>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Search</label>
                <div className="flex space-x-2">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                    <Input
                      placeholder="Search logs..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10"
                      onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                    />
                  </div>
                  <Button onClick={handleSearch} size="sm">
                    Search
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Action</label>
                <Select value={selectedAction} onValueChange={setSelectedAction}>
                  <SelectTrigger>
                    <SelectValue placeholder="All actions" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All actions</SelectItem>
                    {Object.values(AuditAction).map((action) => (
                      <SelectItem key={action} value={action}>
                        {action.replace(/_/g, ' ').toUpperCase()}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">User</label>
                <Select value={selectedUser} onValueChange={setSelectedUser}>
                  <SelectTrigger>
                    <SelectValue placeholder="All users" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All users</SelectItem>
                    {uniqueUsers.map((username) => (
                      <SelectItem key={username} value={username}>
                        {username}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Results</label>
                <div className="flex items-center space-x-2 text-sm text-muted-foreground pt-2">
                  <FileText className="h-4 w-4" />
                  <span>{logs.length} entries</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {loading ? (
            <Card>
              <CardContent className="p-12 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                <p className="text-muted-foreground">Loading audit logs...</p>
              </CardContent>
            </Card>
          ) : logs.length === 0 ? (
            <Card>
              <CardContent className="p-12 text-center">
                <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No audit logs found</h3>
                <p className="text-muted-foreground">
                  Try adjusting your search criteria
                </p>
              </CardContent>
            </Card>
          ) : (
            logs.map((log) => {
              const ActionIcon = actionIcons[log.action];
              
              return (
                <Card key={log.id}>
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start space-x-4">
                        <div className="w-10 h-10 bg-muted rounded-full flex items-center justify-center">
                          <ActionIcon className="h-5 w-5" />
                        </div>
                        
                        <div className="space-y-2">
                          <div className="flex items-center space-x-2">
                            <Badge className={actionColors[log.action]}>
                              {log.action.replace(/_/g, ' ').toUpperCase()}
                            </Badge>
                            <span className="text-sm font-medium">{log.username}</span>
                            <span className="text-sm text-muted-foreground">
                              on {log.resource}
                            </span>
                            {log.resourceId && (
                              <span className="text-sm text-muted-foreground">
                                #{log.resourceId}
                              </span>
                            )}
                          </div>
                          
                          <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                            <div className="flex items-center space-x-1">
                              <Clock className="h-3 w-3" />
                              <span>{formatTimestamp(log.timestamp)}</span>
                            </div>
                            <span>IP: {log.ipAddress}</span>
                          </div>
                          
                          {Object.keys(log.details).length > 0 && (
                            <div className="text-sm text-muted-foreground bg-muted/50 rounded p-2 max-w-2xl">
                              <strong>Details:</strong> {formatDetails(log.details)}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  );
}