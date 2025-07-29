'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ProtectedRoute } from '@/components/protected-route';
import { DashboardLayout } from '@/components/dashboard-layout';
import { SystemAlerts, useSystemAlerts } from '@/components/system-alerts';
import { Permission } from '@/types';

export default function DashboardPage() {
  const { alerts, removeAlert } = useSystemAlerts();
  return (
    <ProtectedRoute requiredPermissions={[Permission.VIEW_COMPOUNDS]}>
      <DashboardLayout>
        <div className="mb-8">
          <h1 className="text-4xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome to the Thai Tokenizer Admin Interface
          </p>
        </div>

        {/* System Alerts */}
        <div className="mb-8">
          <SystemAlerts alerts={alerts} onDismiss={removeAlert} />
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Total Compound Words
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">32</div>
              <p className="text-xs text-muted-foreground">
                +3 from last week
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">API Requests</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">15,420</div>
              <p className="text-xs text-muted-foreground">
                +12% from last month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Avg Response Time
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">4.2ms</div>
              <p className="text-xs text-muted-foreground">Excellent</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">99.8%</div>
              <p className="text-xs text-muted-foreground">System healthy</p>
            </CardContent>
          </Card>
        </div>

        <div className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="flex gap-4">
              <Button>Add Compound Word</Button>
              <Button variant="outline">Run Test</Button>
              <Button variant="outline">View Analytics</Button>
            </CardContent>
          </Card>
        </div>

        <div className="mt-8">
          <Card>
            <CardHeader>
              <CardTitle>Thai Text Test</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="thai-text text-lg">
                ทดสอบการแสดงผลข้อความภาษาไทย: วากาเมะ, ซาชิมิ, เทมปุระ
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                Testing Thai font rendering with compound words
              </p>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    </ProtectedRoute>
  );
}