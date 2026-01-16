import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Label } from "../components/ui/label";
import { 
  AlertTriangle, Clock, TrendingUp, Building2, 
  FileSpreadsheet, Download, RefreshCw
} from "lucide-react";
import { toast } from "sonner";

/**
 * مكون التنبيهات والتقارير لمدير المشتريات
 * يعرض التنبيهات والتقارير بدون إمكانية إضافة كميات مخططة
 */
const QuantityAlertsReportsManager = () => {
  const { API_URL, getAuthHeaders } = useAuth();
  const [alerts, setAlerts] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [projects, setProjects] = useState([]);
  const [reportProject, setReportProject] = useState("");
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("alerts");

  // Fetch all data
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [alertsRes, projectsRes] = await Promise.all([
        axios.get(`${API_URL}/quantity/alerts?days_threshold=7`, getAuthHeaders()),
        axios.get(`${API_URL}/projects`, getAuthHeaders())
      ]);
      
      setAlerts(alertsRes.data);
      const projectsList = Array.isArray(projectsRes.data) ? projectsRes.data : (projectsRes.data.projects || []);
      setProjects(projectsList);
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  }, [API_URL, getAuthHeaders]);

  // Fetch reports
  const fetchReports = useCallback(async () => {
    try {
      const params = reportProject ? `?project_id=${reportProject}` : "";
      const res = await axios.get(`${API_URL}/quantity/reports/summary${params}`, getAuthHeaders());
      setReportData(res.data);
    } catch (error) {
      console.error("Error fetching reports:", error);
    }
  }, [API_URL, getAuthHeaders, reportProject]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (activeTab === "reports") {
      fetchReports();
    }
  }, [activeTab, fetchReports]);

  // Export report
  const handleExportReport = async () => {
    try {
      const params = reportProject ? `?project_id=${reportProject}` : "";
      const response = await axios.get(`${API_URL}/quantity/reports/export${params}`, {
        ...getAuthHeaders(),
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `quantity_report_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success("تم تصدير التقرير");
    } catch (error) {
      toast.error("فشل في تصدير التقرير");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Tab Buttons */}
      <div className="flex gap-2 border-b pb-2">
        <Button
          variant={activeTab === "alerts" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveTab("alerts")}
        >
          <AlertTriangle className="h-4 w-4 ml-1" /> التنبيهات
          {alerts?.overdue?.count > 0 && (
            <Badge className="bg-red-500 text-white mr-1">{alerts.overdue.count}</Badge>
          )}
        </Button>
        <Button
          variant={activeTab === "reports" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveTab("reports")}
        >
          <FileSpreadsheet className="h-4 w-4 ml-1" /> التقارير
        </Button>
        <div className="flex-1"></div>
        <Button variant="ghost" size="sm" onClick={fetchData}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Alerts Tab */}
      {activeTab === "alerts" && alerts && (
        <div className="grid md:grid-cols-2 gap-4">
          {/* Overdue Items */}
          <Card className="border-r-4 border-red-400">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-red-600 text-lg">
                <AlertTriangle className="h-5 w-5" /> الأصناف المتأخرة ({alerts.overdue?.count || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {alerts.overdue?.items?.length > 0 ? (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {alerts.overdue.items.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-red-50 rounded-lg text-sm">
                      <div>
                        <p className="font-medium">{item.item_name}</p>
                        <p className="text-xs text-slate-500">{item.project_name}</p>
                      </div>
                      <div className="text-left">
                        <p className="text-sm font-bold text-red-600">متأخر {item.days_overdue} يوم</p>
                        <p className="text-xs text-slate-500">{item.remaining_qty} {item.unit}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 text-center py-4 text-sm">لا توجد أصناف متأخرة ✓</p>
              )}
            </CardContent>
          </Card>

          {/* Due Soon Items */}
          <Card className="border-r-4 border-orange-400">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-orange-600 text-lg">
                <Clock className="h-5 w-5" /> قريب الموعد ({alerts.due_soon?.count || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {alerts.due_soon?.items?.length > 0 ? (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {alerts.due_soon.items.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-orange-50 rounded-lg text-sm">
                      <div>
                        <p className="font-medium">{item.item_name}</p>
                        <p className="text-xs text-slate-500">{item.project_name}</p>
                      </div>
                      <div className="text-left">
                        <p className="text-sm font-bold text-orange-600">متبقي {item.days_until} يوم</p>
                        <p className="text-xs text-slate-500">{item.remaining_qty} {item.unit}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 text-center py-4 text-sm">لا توجد أصناف قريبة من الموعد</p>
              )}
            </CardContent>
          </Card>

          {/* High Priority Items */}
          <Card className="border-r-4 border-purple-400 md:col-span-2">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-purple-600 text-lg">
                <TrendingUp className="h-5 w-5" /> أولوية عالية ({alerts.high_priority?.count || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {alerts.high_priority?.items?.length > 0 ? (
                <div className="grid md:grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {alerts.high_priority.items.map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 bg-purple-50 rounded-lg text-sm">
                      <div>
                        <p className="font-medium">{item.item_name}</p>
                        <p className="text-xs text-slate-500">{item.project_name}</p>
                      </div>
                      <Badge className="bg-red-100 text-red-700">عالية</Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 text-center py-4 text-sm">لا توجد أصناف ذات أولوية عالية</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Reports Tab */}
      {activeTab === "reports" && (
        <div className="space-y-4">
          {/* Controls */}
          <Card>
            <CardContent className="p-3">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-2">
                  <Label className="text-sm">المشروع:</Label>
                  <select
                    value={reportProject}
                    onChange={(e) => {
                      setReportProject(e.target.value);
                      setTimeout(fetchReports, 100);
                    }}
                    className="h-8 border rounded px-2 text-sm min-w-[150px]"
                  >
                    <option value="">كل المشاريع</option>
                    {projects.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
                <div className="flex-1"></div>
                <Button variant="outline" size="sm" onClick={handleExportReport}>
                  <Download className="h-4 w-4 ml-1" /> تصدير Excel
                </Button>
              </div>
            </CardContent>
          </Card>

          {reportData ? (
            <>
              {/* Summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Card className="border-r-4 border-blue-500">
                  <CardContent className="p-3 text-center">
                    <p className="text-xl font-bold text-blue-600">{reportData.summary?.total_items}</p>
                    <p className="text-xs text-slate-500">إجمالي الأصناف</p>
                  </CardContent>
                </Card>
                <Card className="border-r-4 border-green-500">
                  <CardContent className="p-3 text-center">
                    <p className="text-xl font-bold text-green-600">{reportData.summary?.completion_rate}%</p>
                    <p className="text-xs text-slate-500">نسبة الإنجاز</p>
                  </CardContent>
                </Card>
                <Card className="border-r-4 border-orange-500">
                  <CardContent className="p-3 text-center">
                    <p className="text-xl font-bold text-orange-600">{reportData.summary?.due_soon_count}</p>
                    <p className="text-xs text-slate-500">قريب الموعد</p>
                  </CardContent>
                </Card>
                <Card className="border-r-4 border-red-500">
                  <CardContent className="p-3 text-center">
                    <p className="text-xl font-bold text-red-600">{reportData.summary?.overdue_count}</p>
                    <p className="text-xs text-slate-500">متأخر</p>
                  </CardContent>
                </Card>
              </div>

              {/* By Project */}
              {reportData.by_project?.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <Building2 className="h-5 w-5" /> حسب المشروع
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-3 py-2 text-right">المشروع</th>
                            <th className="px-3 py-2 text-center">أصناف</th>
                            <th className="px-3 py-2 text-center">مخطط</th>
                            <th className="px-3 py-2 text-center">مطلوب</th>
                            <th className="px-3 py-2 text-center">متبقي</th>
                            <th className="px-3 py-2 text-center">إنجاز</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {reportData.by_project.map((p, idx) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="px-3 py-2 font-medium">{p.project_name}</td>
                              <td className="px-3 py-2 text-center">{p.total_items}</td>
                              <td className="px-3 py-2 text-center">{p.planned_qty?.toLocaleString()}</td>
                              <td className="px-3 py-2 text-center text-green-600">{p.ordered_qty?.toLocaleString()}</td>
                              <td className="px-3 py-2 text-center text-orange-600">{p.remaining_qty?.toLocaleString()}</td>
                              <td className="px-3 py-2 text-center">
                                <Badge className={
                                  p.planned_qty > 0 
                                    ? (p.ordered_qty / p.planned_qty * 100) >= 100 
                                      ? "bg-green-100 text-green-700"
                                      : (p.ordered_qty / p.planned_qty * 100) >= 50
                                        ? "bg-yellow-100 text-yellow-700"
                                        : "bg-red-100 text-red-700"
                                    : "bg-slate-100 text-slate-700"
                                }>
                                  {p.planned_qty > 0 ? Math.round(p.ordered_qty / p.planned_qty * 100) : 0}%
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <div className="text-center py-8">
              <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p className="text-slate-500 mt-2">جاري تحميل التقارير...</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default QuantityAlertsReportsManager;
