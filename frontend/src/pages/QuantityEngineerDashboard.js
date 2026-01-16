import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { 
  Package, LogOut, RefreshCw, Plus, Search, Download,
  Edit, Trash2, Calendar, AlertTriangle, Clock, CheckCircle,
  Building2, FileSpreadsheet, TrendingUp, ShoppingCart, List
} from "lucide-react";
import ChangePasswordDialog from "../components/ChangePasswordDialog";

const QuantityEngineerDashboard = () => {
  const { user, logout, API_URL, getAuthHeaders } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  
  // Planned quantities
  const [plannedItems, setPlannedItems] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;
  
  // Catalog items for selection
  const [catalogItems, setCatalogItems] = useState([]);
  const [catalogSearch, setCatalogSearch] = useState("");
  const [catalogPage, setCatalogPage] = useState(1);
  const [catalogTotal, setCatalogTotal] = useState(0);
  
  // Filters
  const [searchTerm, setSearchTerm] = useState("");
  const [filterProject, setFilterProject] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  
  // Projects list
  const [projects, setProjects] = useState([]);
  
  // Dialog states
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [selectItemDialogOpen, setSelectItemDialogOpen] = useState(false);
  
  // Selected catalog item for adding
  const [selectedCatalogItem, setSelectedCatalogItem] = useState(null);
  
  // New planned quantity form
  const [newPlan, setNewPlan] = useState({
    catalog_item_id: "",
    project_id: "",
    planned_quantity: "",
    expected_order_date: "",
    priority: 2,
    notes: ""
  });
  
  // Reports
  const [reportData, setReportData] = useState(null);
  
  // Alerts
  const [alerts, setAlerts] = useState(null);
  
  // Password dialog
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);

  // Fetch initial data
  const fetchData = useCallback(async () => {
    try {
      const [statsRes, projectsRes] = await Promise.all([
        axios.get(`${API_URL}/quantity/dashboard/stats`, getAuthHeaders()),
        axios.get(`${API_URL}/projects`, getAuthHeaders())
      ]);
      
      setStats(statsRes.data);
      setProjects(projectsRes.data.projects || []);
      
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("فشل في تحميل البيانات");
    } finally {
      setLoading(false);
    }
  }, [API_URL, getAuthHeaders]);

  // Fetch planned items
  const fetchPlannedItems = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      params.append("page", currentPage);
      params.append("page_size", pageSize);
      if (searchTerm) params.append("search", searchTerm);
      if (filterProject) params.append("project_id", filterProject);
      if (filterStatus) params.append("status", filterStatus);
      
      const res = await axios.get(`${API_URL}/quantity/planned?${params.toString()}`, getAuthHeaders());
      setPlannedItems(res.data.items || []);
      setTotalItems(res.data.total || 0);
      
    } catch (error) {
      console.error("Error fetching planned items:", error);
    }
  }, [API_URL, getAuthHeaders, currentPage, searchTerm, filterProject, filterStatus]);

  // Fetch catalog items for selection
  const fetchCatalogItems = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      params.append("page", catalogPage);
      params.append("page_size", 20);
      if (catalogSearch) params.append("search", catalogSearch);
      
      const res = await axios.get(`${API_URL}/quantity/catalog-items?${params.toString()}`, getAuthHeaders());
      setCatalogItems(res.data.items || []);
      setCatalogTotal(res.data.total || 0);
      
    } catch (error) {
      console.error("Error fetching catalog items:", error);
    }
  }, [API_URL, getAuthHeaders, catalogPage, catalogSearch]);

  // Fetch reports
  const fetchReports = useCallback(async () => {
    try {
      const params = filterProject ? `?project_id=${filterProject}` : "";
      const res = await axios.get(`${API_URL}/quantity/reports/summary${params}`, getAuthHeaders());
      setReportData(res.data);
    } catch (error) {
      console.error("Error fetching reports:", error);
    }
  }, [API_URL, getAuthHeaders, filterProject]);

  // Fetch alerts
  const fetchAlerts = useCallback(async () => {
    try {
      const res = await axios.get(`${API_URL}/quantity/alerts?days_threshold=7`, getAuthHeaders());
      setAlerts(res.data);
    } catch (error) {
      console.error("Error fetching alerts:", error);
    }
  }, [API_URL, getAuthHeaders]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    fetchPlannedItems();
  }, [fetchPlannedItems]);

  useEffect(() => {
    if (selectItemDialogOpen) {
      fetchCatalogItems();
    }
  }, [selectItemDialogOpen, fetchCatalogItems]);

  // Select catalog item
  const handleSelectCatalogItem = (item) => {
    setSelectedCatalogItem(item);
    setNewPlan({
      ...newPlan,
      catalog_item_id: item.id
    });
    setSelectItemDialogOpen(false);
    setAddDialogOpen(true);
  };

  // Create new planned quantity
  const handleCreatePlan = async () => {
    if (!newPlan.catalog_item_id) {
      toast.error("الرجاء اختيار صنف من الكتالوج");
      return;
    }
    if (!newPlan.project_id) {
      toast.error("الرجاء اختيار المشروع");
      return;
    }
    if (!newPlan.planned_quantity || parseFloat(newPlan.planned_quantity) <= 0) {
      toast.error("الرجاء إدخال الكمية المخططة");
      return;
    }
    
    try {
      await axios.post(`${API_URL}/quantity/planned`, {
        ...newPlan,
        planned_quantity: parseFloat(newPlan.planned_quantity)
      }, getAuthHeaders());
      
      toast.success("تم إضافة الكمية المخططة بنجاح");
      setAddDialogOpen(false);
      setSelectedCatalogItem(null);
      setNewPlan({
        catalog_item_id: "",
        project_id: "",
        planned_quantity: "",
        expected_order_date: "",
        priority: 2,
        notes: ""
      });
      fetchPlannedItems();
      fetchData();
      
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في إضافة الكمية");
    }
  };

  // Update planned item
  const handleUpdateItem = async () => {
    if (!editingItem) return;
    
    try {
      await axios.put(`${API_URL}/quantity/planned/${editingItem.id}`, {
        planned_quantity: parseFloat(editingItem.planned_quantity),
        expected_order_date: editingItem.expected_order_date,
        priority: editingItem.priority,
        notes: editingItem.notes
      }, getAuthHeaders());
      
      toast.success("تم تحديث الكمية بنجاح");
      setEditDialogOpen(false);
      setEditingItem(null);
      fetchPlannedItems();
      
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تحديث الكمية");
    }
  };

  // Delete planned item
  const handleDeleteItem = async (itemId) => {
    if (!window.confirm("هل أنت متأكد من حذف هذا العنصر؟")) return;
    
    try {
      await axios.delete(`${API_URL}/quantity/planned/${itemId}`, getAuthHeaders());
      toast.success("تم حذف العنصر بنجاح");
      fetchPlannedItems();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في حذف العنصر");
    }
  };

  // Export to Excel
  const handleExport = async () => {
    try {
      const params = filterProject ? `?project_id=${filterProject}` : "";
      const response = await axios.get(`${API_URL}/quantity/planned/export${params}`, {
        ...getAuthHeaders(),
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `planned_quantities_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success("تم تصدير البيانات");
    } catch (error) {
      toast.error("فشل في التصدير");
    }
  };

  // Status badge
  const getStatusBadge = (status) => {
    const statusMap = {
      planned: { label: "مخطط", className: "bg-blue-100 text-blue-700" },
      partially_ordered: { label: "طلب جزئي", className: "bg-yellow-100 text-yellow-700" },
      fully_ordered: { label: "مكتمل", className: "bg-green-100 text-green-700" },
      overdue: { label: "متأخر", className: "bg-red-100 text-red-700" }
    };
    const s = statusMap[status] || { label: status, className: "bg-slate-100 text-slate-700" };
    return <Badge className={s.className}>{s.label}</Badge>;
  };

  // Priority badge
  const getPriorityBadge = (priority) => {
    const priorityMap = {
      1: { label: "عالية", className: "bg-red-100 text-red-700" },
      2: { label: "متوسطة", className: "bg-yellow-100 text-yellow-700" },
      3: { label: "منخفضة", className: "bg-green-100 text-green-700" }
    };
    const p = priorityMap[priority] || priorityMap[2];
    return <Badge className={p.className}>{p.label}</Badge>;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-50" dir="rtl">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-purple-100">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-lg flex items-center justify-center">
                <Package className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-800">مهندس الكميات</h1>
                <p className="text-sm text-slate-500">{user?.name}</p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => { fetchData(); fetchPlannedItems(); }}>
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setPasswordDialogOpen(true)}>
                تغيير كلمة المرور
              </Button>
              <Button variant="outline" size="sm" onClick={logout}>
                <LogOut className="h-4 w-4 ml-1" />
                خروج
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Card className="border-r-4 border-purple-500" data-testid="total-items-card">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold text-purple-600">{stats.total_planned_items}</p>
                    <p className="text-sm text-slate-500">إجمالي الأصناف</p>
                  </div>
                  <Package className="h-8 w-8 text-purple-500" />
                </div>
              </CardContent>
            </Card>
            
            <Card className="border-r-4 border-blue-500" data-testid="remaining-qty-card">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold text-blue-600">{stats.total_remaining_qty?.toLocaleString()}</p>
                    <p className="text-sm text-slate-500">الكمية المتبقية</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-blue-500" />
                </div>
              </CardContent>
            </Card>
            
            <Card className="border-r-4 border-orange-500" data-testid="due-soon-card">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold text-orange-600">{stats.due_soon_items}</p>
                    <p className="text-sm text-slate-500">قريب الموعد</p>
                  </div>
                  <Clock className="h-8 w-8 text-orange-500" />
                </div>
              </CardContent>
            </Card>
            
            <Card className="border-r-4 border-red-500" data-testid="overdue-card">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-2xl font-bold text-red-600">{stats.overdue_items}</p>
                    <p className="text-sm text-slate-500">متأخر</p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-red-500" />
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        <Tabs defaultValue="quantities" className="space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="quantities" className="gap-2" data-testid="quantities-tab">
              <Package className="h-4 w-4" /> الكميات المخططة
            </TabsTrigger>
            <TabsTrigger value="alerts" className="gap-2" onClick={fetchAlerts} data-testid="alerts-tab">
              <AlertTriangle className="h-4 w-4" /> التنبيهات
            </TabsTrigger>
            <TabsTrigger value="reports" className="gap-2" onClick={fetchReports} data-testid="reports-tab">
              <FileSpreadsheet className="h-4 w-4" /> التقارير
            </TabsTrigger>
          </TabsList>

          {/* Quantities Tab */}
          <TabsContent value="quantities" className="space-y-4">
            {/* Actions Bar */}
            <Card>
              <CardContent className="p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <Button 
                    onClick={() => setSelectItemDialogOpen(true)} 
                    className="bg-purple-600 hover:bg-purple-700"
                    data-testid="add-quantity-btn"
                  >
                    <Plus className="h-4 w-4 ml-1" /> إضافة كمية مخططة
                  </Button>
                  <Button variant="outline" onClick={handleExport} data-testid="export-btn">
                    <Download className="h-4 w-4 ml-1" /> تصدير Excel
                  </Button>
                  
                  <div className="flex-1"></div>
                  
                  {/* Filters */}
                  <div className="flex items-center gap-2">
                    <Input
                      placeholder="بحث..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-40"
                      data-testid="search-input"
                    />
                    <select
                      value={filterProject}
                      onChange={(e) => setFilterProject(e.target.value)}
                      className="h-9 border rounded-lg px-2 text-sm"
                      data-testid="project-filter"
                    >
                      <option value="">كل المشاريع</option>
                      {projects.map(p => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                    <select
                      value={filterStatus}
                      onChange={(e) => setFilterStatus(e.target.value)}
                      className="h-9 border rounded-lg px-2 text-sm"
                      data-testid="status-filter"
                    >
                      <option value="">كل الحالات</option>
                      <option value="planned">مخطط</option>
                      <option value="partially_ordered">طلب جزئي</option>
                      <option value="fully_ordered">مكتمل</option>
                    </select>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Items Table */}
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm" data-testid="planned-items-table">
                    <thead className="bg-slate-50 border-b">
                      <tr>
                        <th className="px-4 py-3 text-right">الصنف</th>
                        <th className="px-4 py-3 text-right">المشروع</th>
                        <th className="px-4 py-3 text-center">الكمية المخططة</th>
                        <th className="px-4 py-3 text-center">الكمية المطلوبة</th>
                        <th className="px-4 py-3 text-center">المتبقي</th>
                        <th className="px-4 py-3 text-center">تاريخ الطلب</th>
                        <th className="px-4 py-3 text-center">الحالة</th>
                        <th className="px-4 py-3 text-center">الأولوية</th>
                        <th className="px-4 py-3 text-center">إجراءات</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {plannedItems.length === 0 ? (
                        <tr>
                          <td colSpan="9" className="px-4 py-8 text-center text-slate-500">
                            <div className="flex flex-col items-center gap-2">
                              <Package className="h-12 w-12 text-slate-300" />
                              <p>لا توجد كميات مخططة</p>
                              <p className="text-xs">اضغط على "إضافة كمية مخططة" لاختيار صنف من الكتالوج</p>
                            </div>
                          </td>
                        </tr>
                      ) : (
                        plannedItems.map((item) => (
                          <tr key={item.id} className="hover:bg-slate-50" data-testid={`planned-item-${item.id}`}>
                            <td className="px-4 py-3">
                              <div className="font-medium">{item.item_name}</div>
                              <div className="text-xs text-slate-500">{item.unit}</div>
                            </td>
                            <td className="px-4 py-3 text-slate-600">{item.project_name}</td>
                            <td className="px-4 py-3 text-center font-bold">{item.planned_quantity?.toLocaleString()}</td>
                            <td className="px-4 py-3 text-center text-green-600">{item.ordered_quantity?.toLocaleString()}</td>
                            <td className="px-4 py-3 text-center text-orange-600 font-bold">{item.remaining_quantity?.toLocaleString()}</td>
                            <td className="px-4 py-3 text-center text-sm">
                              {item.expected_order_date ? new Date(item.expected_order_date).toLocaleDateString('ar-SA') : "-"}
                            </td>
                            <td className="px-4 py-3 text-center">{getStatusBadge(item.status)}</td>
                            <td className="px-4 py-3 text-center">{getPriorityBadge(item.priority)}</td>
                            <td className="px-4 py-3 text-center">
                              <div className="flex items-center justify-center gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => {
                                    setEditingItem({
                                      ...item,
                                      expected_order_date: item.expected_order_date?.split('T')[0] || ""
                                    });
                                    setEditDialogOpen(true);
                                  }}
                                  data-testid={`edit-btn-${item.id}`}
                                >
                                  <Edit className="h-4 w-4 text-blue-600" />
                                </Button>
                                {item.ordered_quantity === 0 && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleDeleteItem(item.id)}
                                    data-testid={`delete-btn-${item.id}`}
                                  >
                                    <Trash2 className="h-4 w-4 text-red-600" />
                                  </Button>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
                
                {/* Pagination */}
                {totalItems > pageSize && (
                  <div className="flex items-center justify-between px-4 py-3 border-t">
                    <span className="text-sm text-slate-500">
                      إجمالي: {totalItems} عنصر
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={currentPage === 1}
                        onClick={() => setCurrentPage(p => p - 1)}
                      >
                        السابق
                      </Button>
                      <span className="px-3 py-1 text-sm">
                        صفحة {currentPage} من {Math.ceil(totalItems / pageSize)}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={currentPage >= Math.ceil(totalItems / pageSize)}
                        onClick={() => setCurrentPage(p => p + 1)}
                      >
                        التالي
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Alerts Tab */}
          <TabsContent value="alerts" className="space-y-4">
            {alerts ? (
              <div className="grid md:grid-cols-2 gap-4">
                {/* Overdue Items */}
                <Card className="border-r-4 border-red-400">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-red-600">
                      <AlertTriangle className="h-5 w-5" /> الأصناف المتأخرة ({alerts.overdue?.count || 0})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {alerts.overdue?.items?.length > 0 ? (
                      <div className="space-y-2 max-h-80 overflow-y-auto">
                        {alerts.overdue.items.map((item, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                            <div>
                              <p className="font-medium">{item.item_name}</p>
                              <p className="text-xs text-slate-500">{item.project_name}</p>
                            </div>
                            <div className="text-left">
                              <p className="text-sm font-bold text-red-600">متأخر {item.days_overdue} يوم</p>
                              <p className="text-xs text-slate-500">المتبقي: {item.remaining_qty} {item.unit}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-slate-500 text-center py-4">لا توجد أصناف متأخرة ✓</p>
                    )}
                  </CardContent>
                </Card>

                {/* Due Soon Items */}
                <Card className="border-r-4 border-orange-400">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-orange-600">
                      <Clock className="h-5 w-5" /> قريب الموعد - 7 أيام ({alerts.due_soon?.count || 0})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {alerts.due_soon?.items?.length > 0 ? (
                      <div className="space-y-2 max-h-80 overflow-y-auto">
                        {alerts.due_soon.items.map((item, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-orange-50 rounded-lg">
                            <div>
                              <p className="font-medium">{item.item_name}</p>
                              <p className="text-xs text-slate-500">{item.project_name}</p>
                            </div>
                            <div className="text-left">
                              <p className="text-sm font-bold text-orange-600">متبقي {item.days_until} يوم</p>
                              <p className="text-xs text-slate-500">الكمية: {item.remaining_qty} {item.unit}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-slate-500 text-center py-4">لا توجد أصناف قريبة من الموعد</p>
                    )}
                  </CardContent>
                </Card>

                {/* High Priority Items */}
                <Card className="border-r-4 border-purple-400 md:col-span-2">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-purple-600">
                      <TrendingUp className="h-5 w-5" /> أصناف ذات أولوية عالية ({alerts.high_priority?.count || 0})
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {alerts.high_priority?.items?.length > 0 ? (
                      <div className="grid md:grid-cols-2 gap-2 max-h-60 overflow-y-auto">
                        {alerts.high_priority.items.map((item, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
                            <div>
                              <p className="font-medium">{item.item_name}</p>
                              <p className="text-xs text-slate-500">{item.project_name}</p>
                            </div>
                            <div className="text-left">
                              <Badge className="bg-red-100 text-red-700">أولوية عالية</Badge>
                              <p className="text-xs text-slate-500 mt-1">المتبقي: {item.remaining_qty} {item.unit}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-slate-500 text-center py-4">لا توجد أصناف ذات أولوية عالية</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p className="text-slate-500 mt-2">جاري تحميل التنبيهات...</p>
              </div>
            )}
          </TabsContent>

          {/* Reports Tab */}
          <TabsContent value="reports" className="space-y-4">
            {reportData ? (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Card className="border-r-4 border-blue-500">
                    <CardContent className="p-4 text-center">
                      <p className="text-2xl font-bold text-blue-600">{reportData.summary?.total_items}</p>
                      <p className="text-sm text-slate-500">إجمالي الأصناف</p>
                    </CardContent>
                  </Card>
                  <Card className="border-r-4 border-green-500">
                    <CardContent className="p-4 text-center">
                      <p className="text-2xl font-bold text-green-600">{reportData.summary?.completion_rate}%</p>
                      <p className="text-sm text-slate-500">نسبة الإنجاز</p>
                    </CardContent>
                  </Card>
                  <Card className="border-r-4 border-orange-500">
                    <CardContent className="p-4 text-center">
                      <p className="text-2xl font-bold text-orange-600">{reportData.summary?.due_soon_count}</p>
                      <p className="text-sm text-slate-500">قريب الموعد</p>
                    </CardContent>
                  </Card>
                  <Card className="border-r-4 border-red-500">
                    <CardContent className="p-4 text-center">
                      <p className="text-2xl font-bold text-red-600">{reportData.summary?.overdue_count}</p>
                      <p className="text-sm text-slate-500">متأخر</p>
                    </CardContent>
                  </Card>
                </div>

                {/* By Project */}
                {reportData.by_project?.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Building2 className="h-5 w-5" /> حسب المشروع
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-slate-50">
                            <tr>
                              <th className="px-4 py-3 text-right">المشروع</th>
                              <th className="px-4 py-3 text-center">عدد الأصناف</th>
                              <th className="px-4 py-3 text-center">الكمية المخططة</th>
                              <th className="px-4 py-3 text-center">الكمية المطلوبة</th>
                              <th className="px-4 py-3 text-center">المتبقي</th>
                              <th className="px-4 py-3 text-center">نسبة الإنجاز</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y">
                            {reportData.by_project.map((p, idx) => (
                              <tr key={idx} className="hover:bg-slate-50">
                                <td className="px-4 py-3 font-medium">{p.project_name}</td>
                                <td className="px-4 py-3 text-center">{p.total_items}</td>
                                <td className="px-4 py-3 text-center">{p.planned_qty?.toLocaleString()}</td>
                                <td className="px-4 py-3 text-center text-green-600">{p.ordered_qty?.toLocaleString()}</td>
                                <td className="px-4 py-3 text-center text-orange-600">{p.remaining_qty?.toLocaleString()}</td>
                                <td className="px-4 py-3 text-center">
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
                <div className="w-10 h-10 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                <p className="text-slate-500 mt-2">جاري تحميل التقارير...</p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* Select Catalog Item Dialog */}
      <Dialog open={selectItemDialogOpen} onOpenChange={setSelectItemDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh]" dir="rtl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ShoppingCart className="h-5 w-5 text-purple-600" /> اختر صنف من الكتالوج
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Search */}
            <div className="flex gap-2">
              <Input
                placeholder="ابحث عن صنف..."
                value={catalogSearch}
                onChange={(e) => {
                  setCatalogSearch(e.target.value);
                  setCatalogPage(1);
                }}
                className="flex-1"
                data-testid="catalog-search-input"
              />
              <Button variant="outline" onClick={fetchCatalogItems}>
                <Search className="h-4 w-4" />
              </Button>
            </div>
            
            {/* Catalog Items List */}
            <div className="border rounded-lg max-h-96 overflow-y-auto">
              {catalogItems.length === 0 ? (
                <div className="p-8 text-center text-slate-500">
                  <List className="h-12 w-12 mx-auto text-slate-300 mb-2" />
                  <p>لا توجد أصناف في الكتالوج</p>
                  <p className="text-xs">يرجى إضافة أصناف من لوحة مدير المشتريات</p>
                </div>
              ) : (
                <div className="divide-y">
                  {catalogItems.map((item) => (
                    <div 
                      key={item.id} 
                      className="p-3 hover:bg-purple-50 cursor-pointer transition-colors"
                      onClick={() => handleSelectCatalogItem(item)}
                      data-testid={`catalog-item-${item.id}`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{item.name}</p>
                          <p className="text-xs text-slate-500">
                            {item.unit} | {item.supplier_name || "بدون مورد"} | {item.price?.toLocaleString()} {item.currency}
                          </p>
                          {item.description && (
                            <p className="text-xs text-slate-400 mt-1">{item.description}</p>
                          )}
                        </div>
                        <Button variant="ghost" size="sm" className="text-purple-600">
                          <Plus className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* Pagination */}
            {catalogTotal > 20 && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-500">
                  {catalogTotal} صنف
                </span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={catalogPage === 1}
                    onClick={() => setCatalogPage(p => p - 1)}
                  >
                    السابق
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={catalogPage >= Math.ceil(catalogTotal / 20)}
                    onClick={() => setCatalogPage(p => p + 1)}
                  >
                    التالي
                  </Button>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Add Planned Quantity Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="max-w-lg" dir="rtl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5 text-purple-600" /> إضافة كمية مخططة
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Selected Item Info */}
            {selectedCatalogItem && (
              <div className="bg-purple-50 p-3 rounded-lg">
                <p className="font-bold text-purple-700">{selectedCatalogItem.name}</p>
                <p className="text-sm text-slate-600">
                  {selectedCatalogItem.unit} | {selectedCatalogItem.supplier_name || "بدون مورد"} | {selectedCatalogItem.price?.toLocaleString()} {selectedCatalogItem.currency}
                </p>
              </div>
            )}
            
            <div>
              <Label>المشروع *</Label>
              <select
                value={newPlan.project_id}
                onChange={(e) => setNewPlan({ ...newPlan, project_id: e.target.value })}
                className="w-full h-9 border rounded-lg px-2"
                data-testid="project-select"
              >
                <option value="">اختر المشروع</option>
                {projects.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>الكمية المخططة *</Label>
                <Input
                  type="number"
                  min="0"
                  value={newPlan.planned_quantity}
                  onChange={(e) => setNewPlan({ ...newPlan, planned_quantity: e.target.value })}
                  data-testid="quantity-input"
                />
              </div>
              <div>
                <Label>تاريخ الطلب المتوقع</Label>
                <Input
                  type="date"
                  value={newPlan.expected_order_date}
                  onChange={(e) => setNewPlan({ ...newPlan, expected_order_date: e.target.value })}
                  data-testid="date-input"
                />
              </div>
            </div>
            
            <div>
              <Label>الأولوية</Label>
              <select
                value={newPlan.priority}
                onChange={(e) => setNewPlan({ ...newPlan, priority: parseInt(e.target.value) })}
                className="w-full h-9 border rounded-lg px-2"
                data-testid="priority-select"
              >
                <option value={1}>عالية</option>
                <option value={2}>متوسطة</option>
                <option value={3}>منخفضة</option>
              </select>
            </div>
            
            <div>
              <Label>ملاحظات</Label>
              <Textarea
                value={newPlan.notes}
                onChange={(e) => setNewPlan({ ...newPlan, notes: e.target.value })}
                rows={2}
                data-testid="notes-input"
              />
            </div>
            
            <div className="flex gap-2 justify-end pt-4">
              <Button variant="outline" onClick={() => {
                setAddDialogOpen(false);
                setSelectedCatalogItem(null);
              }}>إلغاء</Button>
              <Button onClick={handleCreatePlan} className="bg-purple-600 hover:bg-purple-700" data-testid="save-quantity-btn">
                إضافة
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit Item Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-lg" dir="rtl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit className="h-5 w-5 text-blue-600" /> تعديل الكمية
            </DialogTitle>
          </DialogHeader>
          
          {editingItem && (
            <div className="space-y-4">
              <div className="bg-slate-50 p-3 rounded-lg">
                <p className="font-bold">{editingItem.item_name}</p>
                <p className="text-sm text-slate-500">{editingItem.project_name}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>الكمية المخططة</Label>
                  <Input
                    type="number"
                    min="0"
                    value={editingItem.planned_quantity}
                    onChange={(e) => setEditingItem({ ...editingItem, planned_quantity: e.target.value })}
                  />
                </div>
                <div>
                  <Label>تاريخ الطلب المتوقع</Label>
                  <Input
                    type="date"
                    value={editingItem.expected_order_date || ""}
                    onChange={(e) => setEditingItem({ ...editingItem, expected_order_date: e.target.value })}
                  />
                </div>
              </div>
              
              <div>
                <Label>الأولوية</Label>
                <select
                  value={editingItem.priority}
                  onChange={(e) => setEditingItem({ ...editingItem, priority: parseInt(e.target.value) })}
                  className="w-full h-9 border rounded-lg px-2"
                >
                  <option value={1}>عالية</option>
                  <option value={2}>متوسطة</option>
                  <option value={3}>منخفضة</option>
                </select>
              </div>
              
              <div>
                <Label>ملاحظات</Label>
                <Textarea
                  value={editingItem.notes || ""}
                  onChange={(e) => setEditingItem({ ...editingItem, notes: e.target.value })}
                  rows={2}
                />
              </div>
              
              <div className="flex gap-2 justify-end pt-4">
                <Button variant="outline" onClick={() => setEditDialogOpen(false)}>إلغاء</Button>
                <Button onClick={handleUpdateItem} className="bg-blue-600 hover:bg-blue-700">حفظ</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Password Dialog */}
      <ChangePasswordDialog
        isOpen={passwordDialogOpen}
        onClose={() => setPasswordDialogOpen(false)}
      />
    </div>
  );
};

export default QuantityEngineerDashboard;
