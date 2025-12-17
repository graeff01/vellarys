"use client";

/**
 * DASHBOARD DE QUALIDADE DA IA
 * =============================
 * 
 * Visualização em tempo real da qualidade das respostas da IA.
 * 
 * PERMISSÃO: Admin master only
 * ROTA: /admin/ai-quality
 */

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  Activity,
  AlertCircle,
  Download,
  RefreshCw,
} from "lucide-react";


// =============================================================================
// TIPOS
// =============================================================================

interface AIQualityOverview {
  period: {
    days: number;
    start_date: string;
    end_date: string;
  };
  global_metrics: {
    total_interactions: number;
    total_issues: number;
    forced_handoffs: number;
    issue_rate: number;
    handoff_rate: number;
    avg_confidence: number;
  };
  issues_by_type: {
    hallucinated_price: number;
    repetition: number;
    user_frustration: number;
    other?: number;
  };
  top_tenants_with_issues: Array<{
    tenant_id: number;
    tenant_name: string;
    tenant_slug: string;
    interactions: number;
    issues: number;
    issue_rate: number;
    avg_confidence: number;
  }>;
}

interface RecentIssue {
  id: number;
  timestamp: string;
  tenant: {
    id: number;
    name: string;
  };
  lead: {
    id: number;
    name: string;
    phone: string;
  };
  user_message: string;
  ai_response: string;
  primary_issue: {
    type: string;
    severity: string;
    message: string;
  };
  action_taken: string;
  confidence_score: number;
}


// =============================================================================
// CONSTANTES
// =============================================================================

const COLORS = {
  hallucinated_price: "#EF4444",
  repetition: "#F59E0B",
  user_frustration: "#8B5CF6",
  other: "#6B7280",
};

const ISSUE_LABELS = {
  hallucinated_price: "💰 Preço Inventado",
  repetition: "🔄 Repetição",
  user_frustration: "😤 Frustração",
  other: "❓ Outros",
};

const PERIOD_OPTIONS = [
  { value: "7", label: "Últimos 7 dias" },
  { value: "14", label: "Últimos 14 dias" },
  { value: "30", label: "Últimos 30 dias" },
  { value: "90", label: "Últimos 90 dias" },
];


// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================

export default function AIQualityDashboard() {
  const [overview, setOverview] = useState<AIQualityOverview | null>(null);
  const [recentIssues, setRecentIssues] = useState<RecentIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("7");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, [period]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const overviewRes = await fetch(`/api/admin/ai-quality/overview?days=${period}`, {
        credentials: "include",
      });

      if (!overviewRes.ok) throw new Error("Erro ao buscar overview");
      const overviewData = await overviewRes.json();
      setOverview(overviewData);

      const issuesRes = await fetch(`/api/admin/ai-quality/issues/recent?limit=20`, {
        credentials: "include",
      });

      if (!issuesRes.ok) throw new Error("Erro ao buscar issues");
      const issuesData = await issuesRes.json();
      setRecentIssues(issuesData.issues || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const exportData = async () => {
    try {
      const res = await fetch(`/api/admin/ai-quality/export?days=${period}&format=json`, {
        credentials: "include",
      });
      const data = await res.json();
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ai-quality-export-${new Date().toISOString().split("T")[0]}.json`;
      a.click();
    } catch (err: any) {
      alert("Erro ao exportar: " + err.message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!overview) return null;

  const metrics = overview.global_metrics;

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">🧠 Qualidade da IA</h1>
          <p className="text-gray-600 mt-1">
            Monitoramento em tempo real da qualidade das respostas
          </p>
        </div>

        <div className="flex gap-2">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PERIOD_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button variant="outline" onClick={fetchData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Atualizar
          </Button>

          <Button variant="outline" onClick={exportData}>
            <Download className="h-4 w-4 mr-2" />
            Exportar
          </Button>
        </div>
      </div>

      {/* Cards de Métricas Principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Total de Interações
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="text-3xl font-bold">{metrics.total_interactions.toLocaleString()}</span>
              <Activity className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Issues Detectados
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <span className="text-3xl font-bold">{metrics.total_issues}</span>
                <Badge
                  variant={metrics.issue_rate < 5 ? "default" : "destructive"}
                  className="ml-2"
                >
                  {metrics.issue_rate.toFixed(1)}%
                </Badge>
              </div>
              <AlertTriangle className="h-8 w-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Handoffs Forçados
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <span className="text-3xl font-bold">{metrics.forced_handoffs}</span>
                <Badge
                  variant={metrics.handoff_rate < 3 ? "default" : "destructive"}
                  className="ml-2"
                >
                  {metrics.handoff_rate.toFixed(1)}%
                </Badge>
              </div>
              {metrics.handoff_rate < 3 ? (
                <TrendingDown className="h-8 w-8 text-green-600" />
              ) : (
                <TrendingUp className="h-8 w-8 text-red-600" />
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">
              Confiança Média
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <span className="text-3xl font-bold">{metrics.avg_confidence.toFixed(0)}/100</span>
              <CheckCircle2
                className={`h-8 w-8 ${
                  metrics.avg_confidence >= 80 ? "text-green-600" : "text-yellow-600"
                }`}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Visão Geral</TabsTrigger>
          <TabsTrigger value="issues">Issues Recentes</TabsTrigger>
          <TabsTrigger value="tenants">Por Tenant</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Issues por Tipo</CardTitle>
                <CardDescription>
                  Distribuição dos problemas detectados
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={Object.entries(overview.issues_by_type).map(([key, value]) => ({
                        name: ISSUE_LABELS[key as keyof typeof ISSUE_LABELS] || key,
                        value,
                      }))}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }: any) =>
                        `${name} ${(percent * 100).toFixed(0)}%`
                      }
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {Object.keys(overview.issues_by_type).map((key) => (
                        <Cell
                          key={key}
                          fill={COLORS[key as keyof typeof COLORS] || COLORS.other}
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Detalhamento</CardTitle>
                <CardDescription>
                  Quantidade de cada tipo de issue
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(overview.issues_by_type).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{
                            backgroundColor:
                              COLORS[key as keyof typeof COLORS] || COLORS.other,
                          }}
                        />
                        <span className="font-medium">
                          {ISSUE_LABELS[key as keyof typeof ISSUE_LABELS] || key}
                        </span>
                      </div>
                      <Badge variant="outline">{value}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="issues" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Issues Recentes</CardTitle>
              <CardDescription>
                Últimos 20 problemas detectados pelo validador
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentIssues.map((issue) => (
                  <IssueCard key={issue.id} issue={issue} />
                ))}

                {recentIssues.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    <CheckCircle2 className="h-12 w-12 mx-auto mb-2 text-green-600" />
                    <p>Nenhum issue detectado! 🎉</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="tenants" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Top Tenants com Issues</CardTitle>
              <CardDescription>
                Tenants com mais problemas detectados
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {overview.top_tenants_with_issues.map((tenant) => (
                  <TenantCard key={tenant.tenant_id} tenant={tenant} />
                ))}

                {overview.top_tenants_with_issues.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    Nenhum tenant com issues
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}


// =============================================================================
// COMPONENTES AUXILIARES
// =============================================================================

function IssueCard({ issue }: { issue: RecentIssue }) {
  const severityColor = issue.primary_issue?.severity === "critical" ? "destructive" : "default";

  return (
    <div className="border rounded-lg p-4 space-y-2">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant={severityColor}>{issue.primary_issue?.type || "unknown"}</Badge>
            <span className="text-sm text-gray-600">
              {new Date(issue.timestamp).toLocaleString("pt-BR")}
            </span>
          </div>
          <p className="font-medium mt-1">{issue.tenant.name}</p>
          <p className="text-sm text-gray-600">
            Lead: {issue.lead.name || issue.lead.phone}
          </p>
        </div>
        <Badge variant="outline">Confiança: {issue.confidence_score}</Badge>
      </div>

      <div className="bg-gray-50 rounded p-2 text-sm">
        <p className="font-medium mb-1">Usuário:</p>
        <p className="text-gray-700">{issue.user_message}</p>
      </div>

      <div className="bg-red-50 rounded p-2 text-sm">
        <p className="font-medium mb-1 text-red-700">IA tentou:</p>
        <p className="text-gray-700">{issue.ai_response}</p>
      </div>

      <div className="flex items-center justify-between text-sm">
        <span className="text-gray-600">{issue.primary_issue?.message || "Sem mensagem"}</span>
        <Badge variant={issue.action_taken === "handoff" ? "destructive" : "default"}>
          {issue.action_taken === "handoff" ? "Bloqueado" : "Permitido"}
        </Badge>
      </div>
    </div>
  );
}

function TenantCard({ tenant }: { tenant: any }) {
  return (
    <div className="flex items-center justify-between border rounded-lg p-4">
      <div>
        <p className="font-medium">{tenant.tenant_name}</p>
        <p className="text-sm text-gray-600">{tenant.interactions} interações</p>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm font-medium">{tenant.issues} issues</p>
          <Badge
            variant={tenant.issue_rate < 5 ? "default" : "destructive"}
            className="mt-1"
          >
            {tenant.issue_rate.toFixed(1)}%
          </Badge>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-600">Confiança</p>
          <p className="font-medium">{tenant.avg_confidence.toFixed(0)}/100</p>
        </div>
      </div>
    </div>
  );
}