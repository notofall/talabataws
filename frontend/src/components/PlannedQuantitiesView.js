import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { 
  Package, AlertTriangle, Clock, TrendingUp, Building2, 
  ChevronDown, ChevronUp, RefreshCw 
} from "lucide-react";

/**
 * مكون عرض الكميات المخططة
 * يُستخدم في لوحات المشرف والمهندس والمدير العام
 */
const PlannedQuantitiesView = ({ projectId = null, showProjectFilter = true }) => {
  const { API_URL, getAuthHeaders } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(true);
  const [filterProject, setFilterProject] = useState(projectId || "");
  const [projects, setProjects] = useState([]);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params = filterProject ? `?project_id=${filterProject}` : "";
      const [quantitiesRes, projectsRes] = await Promise.all([
        axios.get(`${API_URL}/quantity/by-role${params}`, getAuthHeaders()),
        showProjectFilter ? axios.get(`${API_URL}/projects`, getAuthHeaders()) : Promise.resolve({ data: [] })
      ]);
      
      setData(quantitiesRes.data);
      if (showProjectFilter) {
        const projectsList = Array.isArray(projectsRes.data) ? projectsRes.data : (projectsRes.data.projects || []);
        setProjects(projectsList);
      }
    } catch (error) {
      console.error("Error fetching quantities:", error);
    } finally {
      setLoading(false);
    }
  }, [API_URL, getAuthHeaders, filterProject, showProjectFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Status badge
  const getStatusBadge = (status) => {
    const statusMap = {
      planned: { label: "مخطط", className: "bg-blue-100 text-blue-700" },
      partially_ordered: { label: "طلب جزئي", className: "bg-yellow-100 text-yellow-700" },
      fully_ordered: { label: "مكتمل", className: "bg-green-100 text-green-700" }
    };
    const s = statusMap[status] || { label: status, className: "bg-slate-100 text-slate-700" };
    return <Badge className={s.className}>{s.label}</Badge>;
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center py-8">
            <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  return (
    <Card className="border-r-4 border-purple-400">
      <CardHeader className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-purple-700">
            <Package className="h-5 w-5" /> الكميات المخططة
            {data.summary?.overdue_count > 0 && (
              <Badge className="bg-red-100 text-red-700 mr-2">
                {data.summary.overdue_count} متأخر
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); fetchData(); }}>
              <RefreshCw className="h-4 w-4" />
            </Button>
            {expanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
          </div>
        </div>
      </CardHeader>
      
      {expanded && (
        <CardContent className="space-y-4">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-purple-50 p-3 rounded-lg text-center">
              <p className="text-xl font-bold text-purple-600">{data.summary?.total_items || 0}</p>
              <p className="text-xs text-slate-500">إجمالي الأصناف</p>
            </div>
            <div className="bg-blue-50 p-3 rounded-lg text-center">
              <p className="text-xl font-bold text-blue-600">{data.summary?.total_remaining?.toLocaleString() || 0}</p>
              <p className="text-xs text-slate-500">الكمية المتبقية</p>
            </div>
            <div className="bg-orange-50 p-3 rounded-lg text-center">
              <p className="text-xl font-bold text-orange-600">
                {data.items?.filter(i => i.days_until !== null && i.days_until <= 7 && i.days_until >= 0).length || 0}
              </p>
              <p className="text-xs text-slate-500">قريب الموعد</p>
            </div>
            <div className="bg-red-50 p-3 rounded-lg text-center">
              <p className="text-xl font-bold text-red-600">{data.summary?.overdue_count || 0}</p>
              <p className="text-xs text-slate-500">متأخر</p>
            </div>
          </div>

          {/* Project Filter */}
          {showProjectFilter && projects.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-500">فلترة حسب المشروع:</span>
              <select
                value={filterProject}
                onChange={(e) => setFilterProject(e.target.value)}
                className="h-8 border rounded px-2 text-sm flex-1 max-w-xs"
              >
                <option value="">كل المشاريع</option>
                {projects.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Items List */}
          {data.items?.length > 0 ? (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 border-b">
                  <tr>
                    <th className="px-3 py-2 text-right">الصنف</th>
                    <th className="px-3 py-2 text-right">المشروع</th>
                    <th className="px-3 py-2 text-center">مخطط</th>
                    <th className="px-3 py-2 text-center">متبقي</th>
                    <th className="px-3 py-2 text-center">تاريخ الطلب</th>
                    <th className="px-3 py-2 text-center">الحالة</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.items.slice(0, 20).map((item, idx) => (
                    <tr 
                      key={idx} 
                      className={`hover:bg-slate-50 ${item.is_overdue ? 'bg-red-50' : ''}`}
                    >
                      <td className="px-3 py-2">
                        <div className="font-medium">{item.item_name}</div>
                        <div className="text-xs text-slate-500">{item.unit} | {item.category_name || "-"}</div>
                      </td>
                      <td className="px-3 py-2 text-slate-600 text-sm">{item.project_name}</td>
                      <td className="px-3 py-2 text-center">{item.planned_quantity?.toLocaleString()}</td>
                      <td className="px-3 py-2 text-center font-bold text-orange-600">
                        {item.remaining_quantity?.toLocaleString()}
                      </td>
                      <td className="px-3 py-2 text-center text-sm">
                        {item.expected_order_date ? (
                          <span className={item.is_overdue ? 'text-red-600 font-bold' : ''}>
                            {new Date(item.expected_order_date).toLocaleDateString('ar-SA')}
                            {item.is_overdue && <span className="block text-xs">متأخر</span>}
                            {item.days_until !== null && item.days_until >= 0 && item.days_until <= 7 && (
                              <span className="block text-xs text-orange-600">متبقي {item.days_until} يوم</span>
                            )}
                          </span>
                        ) : "-"}
                      </td>
                      <td className="px-3 py-2 text-center">{getStatusBadge(item.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {data.items.length > 20 && (
                <div className="bg-slate-50 px-3 py-2 text-center text-sm text-slate-500">
                  يتم عرض 20 صنف من أصل {data.items.length}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-6 text-slate-500">
              <Package className="h-10 w-10 mx-auto text-slate-300 mb-2" />
              <p>لا توجد كميات مخططة</p>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
};

export default PlannedQuantitiesView;
