import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Package, Plus, LogOut, FileText, Clock, CheckCircle, XCircle, RefreshCw, Download, Eye, Edit, Trash2, X, Truck, PackageCheck, Building, KeyRound, Loader2 } from "lucide-react";
import { exportRequestToPDF, exportRequestsTableToPDF } from "../utils/pdfExport";
import ChangePasswordDialog from "../components/ChangePasswordDialog";

const UNITS = ["قطعة", "طن", "كيلو", "متر", "متر مربع", "متر مكعب", "كيس", "لتر", "علبة", "رول"];

const SupervisorDashboard = () => {
  const { user, logout, getAuthHeaders, API_URL } = useAuth();
  const [requests, setRequests] = useState([]);
  const [engineers, setEngineers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [pendingDeliveries, setPendingDeliveries] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deliveryDialogOpen, setDeliveryDialogOpen] = useState(false);
  const [projectDialogOpen, setProjectDialogOpen] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [selectedDelivery, setSelectedDelivery] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [deliveryItems, setDeliveryItems] = useState([]);
  const [deliveryNotes, setDeliveryNotes] = useState("");
  
  // Filter state - نظام الفلاتر المحسن
  const [filterMode, setFilterMode] = useState("all"); // all, pending_engineer, approved, ordered, delivered
  const [requestsPage, setRequestsPage] = useState(1);
  const ITEMS_PER_PAGE = 10;

  // Form state
  const [items, setItems] = useState([]);
  const [newItemName, setNewItemName] = useState("");
  const [newItemQty, setNewItemQty] = useState("");
  const [newItemUnit, setNewItemUnit] = useState("قطعة");
  const [newItemEstPrice, setNewItemEstPrice] = useState("");
  const [projectId, setProjectId] = useState("");
  const [reason, setReason] = useState("");
  const [engineerId, setEngineerId] = useState("");
  const [expectedDeliveryDate, setExpectedDeliveryDate] = useState("");

  // Project form state
  const [newProject, setNewProject] = useState({ name: "", owner_name: "", description: "", location: "" });
  const [editingProject, setEditingProject] = useState(null);

  // Edit form state
  const [editItems, setEditItems] = useState([]);
  const [editNewItemName, setEditNewItemName] = useState("");
  const [editNewItemQty, setEditNewItemQty] = useState("");
  const [editNewItemUnit, setEditNewItemUnit] = useState("قطعة");
  const [editNewItemEstPrice, setEditNewItemEstPrice] = useState("");
  const [editProjectId, setEditProjectId] = useState("");
  const [editReason, setEditReason] = useState("");
  const [editEngineerId, setEditEngineerId] = useState("");
  const [editExpectedDeliveryDate, setEditExpectedDeliveryDate] = useState("");

  const fetchData = async () => {
    try {
      const [requestsRes, engineersRes, statsRes, deliveriesRes, projectsRes] = await Promise.all([
        axios.get(`${API_URL}/requests`, getAuthHeaders()),
        axios.get(`${API_URL}/users/engineers`, getAuthHeaders()),
        axios.get(`${API_URL}/v2/dashboard/stats`, getAuthHeaders()),
        axios.get(`${API_URL}/purchase-orders/pending-delivery`, getAuthHeaders()),
        axios.get(`${API_URL}/projects`, getAuthHeaders()),
      ]);
      setRequests(requestsRes.data);
      setEngineers(engineersRes.data);
      setStats(statsRes.data);
      setPendingDeliveries(deliveriesRes.data || []);
      setProjects(projectsRes.data || []);
    } catch (error) {
      toast.error("فشل في تحميل البيانات");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    toast.success("تم تحديث البيانات");
  };

  useEffect(() => { fetchData(); }, []);
  
  // Filtered requests based on filter mode
  const getFilteredRequests = () => {
    let filtered = [...requests];
    switch (filterMode) {
      case "pending_engineer":
        filtered = filtered.filter(r => r.status === "pending_engineer");
        break;
      case "approved":
        filtered = filtered.filter(r => r.status === "approved_by_engineer" || r.status === "partially_ordered");
        break;
      case "ordered":
        filtered = filtered.filter(r => r.status === "purchase_order_issued");
        break;
      case "delivered":
        filtered = filtered.filter(r => r.status === "delivered");
        break;
      default:
        break;
    }
    return filtered;
  };
  
  const filteredRequests = getFilteredRequests();
  const totalPages = Math.ceil(filteredRequests.length / ITEMS_PER_PAGE);
  const paginatedRequests = filteredRequests.slice((requestsPage - 1) * ITEMS_PER_PAGE, requestsPage * ITEMS_PER_PAGE);
  
  // Reset page when filter changes
  useEffect(() => {
    setRequestsPage(1);
  }, [filterMode]);
  
  // Filter counts for badges
  const filterCounts = {
    all: requests.length,
    pending_engineer: requests.filter(r => r.status === "pending_engineer").length,
    approved: requests.filter(r => r.status === "approved_by_engineer" || r.status === "partially_ordered").length,
    ordered: requests.filter(r => r.status === "purchase_order_issued").length,
    delivered: requests.filter(r => r.status === "delivered").length,
  };

  // Delivery functions
  const openDeliveryDialog = (order) => {
    setSelectedDelivery(order);
    // Initialize delivery items with remaining quantities
    const items = order.items.map(item => ({
      name: item.name,
      quantity: item.quantity,
      delivered_quantity: item.delivered_quantity || 0,
      remaining: item.quantity - (item.delivered_quantity || 0),
      quantity_to_deliver: 0
    }));
    setDeliveryItems(items);
    setDeliveryNotes("");
    setDeliveryDialogOpen(true);
  };

  const handleRecordDelivery = async () => {
    const itemsToDeliver = deliveryItems.filter(item => item.quantity_to_deliver > 0);
    if (itemsToDeliver.length === 0) {
      toast.error("الرجاء تحديد كمية واحدة على الأقل");
      return;
    }

    setSubmitting(true);
    try {
      await axios.put(`${API_URL}/purchase-orders/${selectedDelivery.id}/deliver`, {
        items_delivered: itemsToDeliver.map(item => ({
          name: item.name,
          quantity_delivered: item.quantity_to_deliver
        })),
        notes: deliveryNotes,
        received_by: user.name
      }, getAuthHeaders());
      
      toast.success("تم تسجيل الاستلام بنجاح");
      setDeliveryDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تسجيل الاستلام");
    } finally {
      setSubmitting(false);
    }
  };

  // Add item to list
  const addItem = () => {
    if (!newItemName.trim()) { toast.error("أدخل اسم المادة"); return; }
    if (!newItemQty || parseInt(newItemQty) <= 0) { toast.error("أدخل الكمية"); return; }
    
    setItems([...items, { 
      name: newItemName.trim(), 
      quantity: newItemQty, 
      unit: newItemUnit,
      estimated_price: newItemEstPrice ? parseFloat(newItemEstPrice) : null
    }]);
    setNewItemName("");
    setNewItemQty("");
    setNewItemUnit("قطعة");
    setNewItemEstPrice("");
    toast.success("تم إضافة الصنف");
  };

  const removeItem = (index) => setItems(items.filter((_, i) => i !== index));

  // Edit item functions
  const addEditItem = () => {
    if (!editNewItemName.trim()) { toast.error("أدخل اسم المادة"); return; }
    if (!editNewItemQty || parseInt(editNewItemQty) <= 0) { toast.error("أدخل الكمية"); return; }
    
    setEditItems([...editItems, { 
      name: editNewItemName.trim(), 
      quantity: editNewItemQty, 
      unit: editNewItemUnit,
      estimated_price: editNewItemEstPrice ? parseFloat(editNewItemEstPrice) : null
    }]);
    setEditNewItemName("");
    setEditNewItemQty("");
    setEditNewItemUnit("قطعة");
    setEditNewItemEstPrice("");
  };

  const removeEditItem = (index) => setEditItems(editItems.filter((_, i) => i !== index));

  const resetForm = () => {
    setItems([]);
    setNewItemName("");
    setNewItemQty("");
    setNewItemUnit("قطعة");
    setNewItemEstPrice("");
    setProjectId("");
    setReason("");
    setEngineerId("");
    setExpectedDeliveryDate("");
  };

  // Project management functions
  const handleCreateProject = async () => {
    if (!newProject.name || !newProject.owner_name) {
      toast.error("الرجاء إدخال اسم المشروع واسم المالك");
      return;
    }
    try {
      await axios.post(`${API_URL}/projects`, newProject, getAuthHeaders());
      toast.success("تم إنشاء المشروع بنجاح");
      setNewProject({ name: "", owner_name: "", description: "", location: "" });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في إنشاء المشروع");
    }
  };

  const handleUpdateProject = async () => {
    if (!editingProject) return;
    try {
      await axios.put(`${API_URL}/projects/${editingProject.id}`, {
        name: editingProject.name,
        owner_name: editingProject.owner_name,
        description: editingProject.description,
        location: editingProject.location,
        status: editingProject.status
      }, getAuthHeaders());
      toast.success("تم تحديث المشروع بنجاح");
      setEditingProject(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تحديث المشروع");
    }
  };

  const handleDeleteProject = async (projectId) => {
    if (!window.confirm("هل أنت متأكد من حذف هذا المشروع؟")) return;
    try {
      await axios.delete(`${API_URL}/projects/${projectId}`, getAuthHeaders());
      toast.success("تم حذف المشروع بنجاح");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في حذف المشروع");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (items.length === 0) { toast.error("الرجاء إضافة صنف واحد على الأقل"); return; }
    if (!projectId || !reason || !engineerId) { toast.error("الرجاء إكمال جميع الحقول"); return; }

    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/requests`, {
        items: items.map(item => ({ 
          name: item.name, 
          quantity: parseInt(item.quantity), 
          unit: item.unit,
          estimated_price: item.estimated_price
        })),
        project_id: projectId, 
        reason, 
        engineer_id: engineerId,
        expected_delivery_date: expectedDeliveryDate || null
      }, getAuthHeaders());
      toast.success("تم إنشاء الطلب بنجاح");
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في إنشاء الطلب");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = async (e) => {
    e.preventDefault();
    if (editItems.length === 0) { toast.error("الرجاء إضافة صنف واحد على الأقل"); return; }
    if (!editProjectId || !editReason || !editEngineerId) { toast.error("الرجاء إكمال جميع الحقول"); return; }

    setSubmitting(true);
    try {
      await axios.put(`${API_URL}/requests/${selectedRequest.id}/edit`, {
        items: editItems.map(item => ({ name: item.name, quantity: parseInt(item.quantity), unit: item.unit || "قطعة" })),
        project_id: editProjectId, reason: editReason, engineer_id: editEngineerId,
      }, getAuthHeaders());
      toast.success("تم تعديل الطلب بنجاح");
      setEditDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تعديل الطلب");
    } finally {
      setSubmitting(false);
    }
  };

  const openEditDialog = (request) => {
    setSelectedRequest(request);
    setEditItems(request.items.map(item => ({ name: item.name, quantity: String(item.quantity), unit: item.unit || "قطعة" })));
    setEditNewItemName("");
    setEditNewItemQty("");
    setEditNewItemUnit("قطعة");
    setEditProjectId(request.project_id || "");
    setEditReason(request.reason);
    setEditEngineerId(request.engineer_id);
    setEditDialogOpen(true);
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      pending_engineer: { label: "بانتظار المهندس", color: "bg-yellow-100 text-yellow-800 border-yellow-300" },
      approved_by_engineer: { label: "معتمد", color: "bg-green-100 text-green-800 border-green-300" },
      rejected_by_engineer: { label: "مرفوض", color: "bg-red-100 text-red-800 border-red-300" },
      purchase_order_issued: { label: "تم إصدار أمر الشراء", color: "bg-blue-100 text-blue-800 border-blue-300" },
      partially_ordered: { label: "جاري الإصدار", color: "bg-indigo-100 text-indigo-800 border-indigo-300" },
    };
    const statusInfo = statusMap[status] || { label: status, color: "bg-slate-100 text-slate-800" };
    return <Badge className={`${statusInfo.color} border text-xs`}>{statusInfo.label}</Badge>;
  };

  const formatDate = (dateString) => new Date(dateString).toLocaleDateString("ar-SA", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const getItemsSummary = (items) => !items?.length ? "-" : items.length === 1 ? items[0].name : `${items[0].name} +${items.length - 1}`;

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-slate-50"><div className="w-10 h-10 border-4 border-orange-600 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-slate-900 text-white shadow-lg sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-3 sm:px-6">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-orange-600 rounded flex items-center justify-center">
                <Package className="w-5 h-5" />
              </div>
              <div className="hidden sm:block">
                <h1 className="text-sm font-bold">نظام طلبات المواد</h1>
                <p className="text-xs text-slate-400">لوحة تحكم المشرف</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => setProjectDialogOpen(true)} className="text-slate-300 hover:text-white h-8 px-2">
                <Building className="w-4 h-4 ml-1" /><span className="hidden sm:inline">المشاريع</span>
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setPasswordDialogOpen(true)} className="text-slate-300 hover:text-white h-8 px-2">
                <KeyRound className="w-4 h-4" />
              </Button>
              <span className="text-xs sm:text-sm text-slate-300 hidden sm:inline">{user?.name}</span>
              <Button variant="ghost" size="sm" onClick={logout} className="text-slate-300 hover:text-white h-8 px-2">
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline mr-1">خروج</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-3 sm:px-6 py-4">
        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-4">
          {[
            { label: "الإجمالي", value: stats.total || 0, color: "border-orange-500" },
            { label: "معلقة", value: stats.pending || 0, color: "border-yellow-500" },
            { label: "معتمدة", value: stats.approved || 0, color: "border-green-500" },
            { label: "مرفوضة", value: stats.rejected || 0, color: "border-red-500" },
            { label: "بانتظار الاستلام", value: pendingDeliveries.length, color: "border-purple-500" },
          ].map((stat, i) => (
            <Card key={i} className={`border-r-4 ${stat.color}`}>
              <CardContent className="p-3">
                <p className="text-xs text-slate-500">{stat.label}</p>
                <p className="text-2xl font-bold">{stat.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Pending Deliveries Section */}
        {pendingDeliveries.length > 0 && (
          <Card className="mb-4 border-purple-200 bg-purple-50">
            <CardHeader className="p-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Truck className="w-5 h-5 text-purple-600" />
                <span>أوامر بانتظار الاستلام ({pendingDeliveries.length})</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-3 pt-0">
              <div className="space-y-2">
                {pendingDeliveries.map(order => (
                  <div key={order.id} className="flex items-center justify-between bg-white p-3 rounded-lg border">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-orange-600 font-bold text-sm">{order.id?.slice(0,8).toUpperCase()}</span>
                        <Badge className={order.status === 'shipped' ? 'bg-purple-100 text-purple-800 border-purple-300' : 'bg-orange-100 text-orange-800 border-orange-300'}>
                          {order.status === 'shipped' ? 'تم الشحن' : 'تسليم جزئي'}
                        </Badge>
                      </div>
                      <p className="text-sm text-slate-600">{order.project_name} - {order.supplier_name}</p>
                      <p className="text-xs text-slate-400">{order.items?.length} صنف</p>
                    </div>
                    <Button size="sm" onClick={() => openDeliveryDialog(order)} className="bg-purple-600 hover:bg-purple-700 h-8">
                      <PackageCheck className="w-4 h-4 ml-1" />استلام
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        <div className="flex items-center justify-between mb-4 gap-2">
          <h2 className="text-lg sm:text-xl font-bold text-slate-900">طلباتي</h2>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => exportRequestsTableToPDF(requests, 'طلباتي')} disabled={!requests.length} className="h-8 px-2 text-xs">
              <Download className="w-3 h-3 sm:ml-1" /><span className="hidden sm:inline">تصدير</span>
            </Button>
            <Button variant="outline" size="sm" onClick={fetchData} className="h-8 px-2">
              <RefreshCw className="w-3 h-3" />
            </Button>
            <Dialog open={dialogOpen} onOpenChange={(o) => { setDialogOpen(o); if (!o) resetForm(); }}>
              <DialogTrigger asChild>
                <Button size="sm" className="bg-orange-600 hover:bg-orange-700 text-white h-8 px-3 text-xs">
                  <Plus className="w-3 h-3 ml-1" />طلب جديد
                </Button>
              </DialogTrigger>
              <DialogContent className="w-[95vw] max-w-md max-h-[90vh] overflow-y-auto p-4" dir="rtl">
                <DialogHeader><DialogTitle className="text-center text-lg">إنشاء طلب مواد جديد</DialogTitle></DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                  
                  {/* Items List - inline */}
                  {items.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-slate-700">الأصناف المضافة ({items.length})</p>
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        {items.map((item, index) => (
                          <div key={`item-${index}`} className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg p-3">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                                {index + 1}
                              </div>
                              <div>
                                <p className="font-medium text-slate-800">{item.name}</p>
                                <p className="text-sm text-slate-500">{item.quantity} {item.unit}</p>
                              </div>
                            </div>
                            <Button 
                              type="button" 
                              variant="ghost" 
                              size="sm" 
                              onClick={() => removeItem(index)} 
                              className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                            >
                              <X className="w-5 h-5" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Add Item Input - inline */}
                  <div className="bg-orange-50 border-2 border-dashed border-orange-300 rounded-xl p-4">
                    <p className="text-sm font-medium text-orange-800 mb-3 text-center">إضافة صنف جديد</p>
                    <div className="space-y-3">
                      <Input 
                        placeholder="اسم المادة (مثال: حديد تسليح)" 
                        value={newItemName} 
                        onChange={(e) => setNewItemName(e.target.value)} 
                        className="h-11 text-center bg-white"
                      />
                      <div className="flex gap-2">
                        <Input 
                          type="number" 
                          min="1" 
                          placeholder="الكمية" 
                          value={newItemQty} 
                          onChange={(e) => setNewItemQty(e.target.value)} 
                          className="h-11 flex-1 text-center bg-white"
                        />
                        <select 
                          value={newItemUnit} 
                          onChange={(e) => setNewItemUnit(e.target.value)} 
                          className="h-11 flex-1 border rounded-lg bg-white px-3 text-sm"
                        >
                          {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                        </select>
                      </div>
                      <Input 
                        type="number" 
                        min="0" 
                        step="0.01"
                        placeholder="السعر التقديري (اختياري)" 
                        value={newItemEstPrice} 
                        onChange={(e) => setNewItemEstPrice(e.target.value)} 
                        className="h-11 text-center bg-white"
                      />
                      <Button 
                        type="button" 
                        onClick={addItem} 
                        className="w-full h-11 bg-orange-600 hover:bg-orange-700 text-white font-medium"
                      >
                        <Plus className="w-5 h-5 ml-2" />
                        إضافة للقائمة
                      </Button>
                    </div>
                  </div>

                  <hr className="border-slate-200" />

                  <div>
                    <Label className="text-sm font-medium">المشروع</Label>
                    <div className="flex gap-2 mt-1">
                      <select value={projectId} onChange={(e) => setProjectId(e.target.value)} className="flex-1 h-11 border rounded-lg bg-white px-3">
                        <option value="">اختر المشروع</option>
                        {projects.filter(p => p.status === 'active').map((proj) => (
                          <option key={proj.id} value={proj.id}>{proj.name} - {proj.owner_name}</option>
                        ))}
                      </select>
                      <Button type="button" variant="outline" onClick={() => setProjectDialogOpen(true)} className="h-11 px-3">
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>

                  <div>
                    <Label className="text-sm font-medium">تاريخ الحاجة المتوقع</Label>
                    <Input type="date" value={expectedDeliveryDate} onChange={(e) => setExpectedDeliveryDate(e.target.value)} className="h-11 mt-1" />
                  </div>

                  <div>
                    <Label className="text-sm font-medium">سبب الطلب</Label>
                    <Textarea placeholder="اذكر سبب طلب هذه المواد..." value={reason} onChange={(e) => setReason(e.target.value)} rows={2} className="mt-1" />
                  </div>

                  <div>
                    <Label className="text-sm font-medium">المهندس المعتمد</Label>
                    <select value={engineerId} onChange={(e) => setEngineerId(e.target.value)} className="w-full h-11 mt-1 border rounded-lg bg-white px-3">
                      <option value="">اختر المهندس</option>
                      {engineers.map((eng) => <option key={eng.id} value={eng.id}>{eng.name}</option>)}
                    </select>
                  </div>

                  <Button type="submit" className="w-full h-12 bg-green-600 hover:bg-green-700 text-white font-bold text-base" disabled={submitting || items.length === 0}>
                    {submitting ? "جاري الإرسال..." : `إرسال الطلب (${items.length} صنف)`}
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Requests */}
        <Card className="shadow-sm">
          <CardContent className="p-0">
            {!requests.length ? (
              <div className="text-center py-12">
                <Package className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <p className="text-slate-500">لا توجد طلبات</p>
              </div>
            ) : (
              <>
                {/* Mobile View */}
                <div className="sm:hidden divide-y">
                  {requests.map((req) => (
                    <div key={req.id} className="p-3 space-y-2">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-bold text-blue-600">طلب #{req.request_number || '-'}</p>
                          <p className="font-medium text-sm">{getItemsSummary(req.items)}</p>
                          <p className="text-xs text-slate-500">{req.project_name}</p>
                        </div>
                        {getStatusBadge(req.status)}
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-slate-400">{formatDate(req.created_at)}</span>
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" onClick={() => { setSelectedRequest(req); setViewDialogOpen(true); }} className="h-7 w-7 p-0"><Eye className="w-3 h-3" /></Button>
                          {req.status === "pending_engineer" && <Button size="sm" variant="ghost" onClick={() => openEditDialog(req)} className="h-7 w-7 p-0"><Edit className="w-3 h-3 text-blue-600" /></Button>}
                          <Button size="sm" variant="ghost" onClick={() => exportRequestToPDF(req)} className="h-7 w-7 p-0"><Download className="w-3 h-3 text-green-600" /></Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Desktop View */}
                <div className="hidden sm:block overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-50">
                        <TableHead className="text-right">رقم الطلب</TableHead>
                        <TableHead className="text-right">الأصناف</TableHead>
                        <TableHead className="text-right">المشروع</TableHead>
                        <TableHead className="text-right">المهندس</TableHead>
                        <TableHead className="text-right">الحالة</TableHead>
                        <TableHead className="text-right">التاريخ</TableHead>
                        <TableHead className="text-right">الإجراءات</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {requests.map((req) => (
                        <TableRow key={req.id}>
                          <TableCell className="font-bold text-blue-600">{req.request_number || '-'}</TableCell>
                          <TableCell className="font-medium">{getItemsSummary(req.items)}</TableCell>
                          <TableCell>{req.project_name}</TableCell>
                          <TableCell>{req.engineer_name}</TableCell>
                          <TableCell>{getStatusBadge(req.status)}</TableCell>
                          <TableCell className="text-slate-500 text-sm">{formatDate(req.created_at)}</TableCell>
                          <TableCell>
                            <div className="flex gap-1">
                              <Button size="sm" variant="ghost" onClick={() => { setSelectedRequest(req); setViewDialogOpen(true); }} className="h-8 w-8 p-0"><Eye className="w-4 h-4" /></Button>
                              {req.status === "pending_engineer" && <Button size="sm" variant="ghost" onClick={() => openEditDialog(req)} className="h-8 w-8 p-0"><Edit className="w-4 h-4 text-blue-600" /></Button>}
                              <Button size="sm" variant="ghost" onClick={() => exportRequestToPDF(req)} className="h-8 w-8 p-0"><Download className="w-4 h-4 text-green-600" /></Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </main>

      {/* View Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="w-[95vw] max-w-md max-h-[85vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader><DialogTitle className="text-center">تفاصيل الطلب</DialogTitle></DialogHeader>
          {selectedRequest && (
            <div className="space-y-3 mt-2">
              <div className="bg-slate-50 p-3 rounded-lg space-y-2">
                <p className="text-sm font-medium border-b pb-2">الأصناف ({selectedRequest.items?.length || 0})</p>
                {selectedRequest.items?.map((item, idx) => (
                  <div key={idx} className="flex justify-between text-sm bg-white p-2 rounded border">
                    <span className="font-medium">{item.name}</span>
                    <span className="text-slate-600">{item.quantity} {item.unit}</span>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-slate-500">المشروع:</span><p className="font-medium">{selectedRequest.project_name}</p></div>
                <div><span className="text-slate-500">المهندس:</span><p className="font-medium">{selectedRequest.engineer_name}</p></div>
              </div>
              <div><span className="text-slate-500 text-sm">السبب:</span><p className="text-sm">{selectedRequest.reason}</p></div>
              {selectedRequest.rejection_reason && (
                <div className="bg-red-50 p-2 rounded text-sm border border-red-200">
                  <span className="text-red-600 font-medium">سبب الرفض:</span>
                  <p className="text-red-800">{selectedRequest.rejection_reason}</p>
                </div>
              )}
              <Button className="w-full bg-green-600 hover:bg-green-700" onClick={() => exportRequestToPDF(selectedRequest)}>
                <Download className="w-4 h-4 ml-2" />تصدير PDF
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="w-[95vw] max-w-md max-h-[90vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader><DialogTitle className="text-center">تعديل الطلب</DialogTitle></DialogHeader>
          <form onSubmit={handleEdit} className="space-y-4 mt-4">
            
            {/* Edit Items List - inline */}
            {editItems.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-slate-700">الأصناف الحالية ({editItems.length})</p>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {editItems.map((item, index) => (
                    <div key={`edit-item-${index}`} className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg p-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                          {index + 1}
                        </div>
                        <div>
                          <p className="font-medium text-slate-800">{item.name}</p>
                          <p className="text-sm text-slate-500">{item.quantity} {item.unit}</p>
                        </div>
                      </div>
                      <Button 
                        type="button" 
                        variant="ghost" 
                        size="sm" 
                        onClick={() => removeEditItem(index)} 
                        className="h-8 w-8 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                      >
                        <X className="w-5 h-5" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Add Edit Item Input - inline */}
            <div className="bg-orange-50 border-2 border-dashed border-orange-300 rounded-xl p-4">
              <p className="text-sm font-medium text-orange-800 mb-3 text-center">إضافة صنف جديد</p>
              <div className="space-y-3">
                <Input 
                  placeholder="اسم المادة (مثال: حديد تسليح)" 
                  value={editNewItemName} 
                  onChange={(e) => setEditNewItemName(e.target.value)} 
                  className="h-11 text-center bg-white"
                />
                <div className="flex gap-2">
                  <Input 
                    type="number" 
                    min="1" 
                    placeholder="الكمية" 
                    value={editNewItemQty} 
                    onChange={(e) => setEditNewItemQty(e.target.value)} 
                    className="h-11 flex-1 text-center bg-white"
                  />
                  <select 
                    value={editNewItemUnit} 
                    onChange={(e) => setEditNewItemUnit(e.target.value)} 
                    className="h-11 flex-1 border rounded-lg bg-white px-3 text-sm"
                  >
                    {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                  </select>
                </div>
                <Button 
                  type="button" 
                  onClick={addEditItem} 
                  className="w-full h-11 bg-orange-600 hover:bg-orange-700 text-white font-medium"
                >
                  <Plus className="w-5 h-5 ml-2" />
                  إضافة للقائمة
                </Button>
              </div>
            </div>

            <hr className="border-slate-200" />

            <div>
              <Label className="text-sm font-medium">المشروع</Label>
              <select value={editProjectId} onChange={(e) => setEditProjectId(e.target.value)} className="w-full h-11 mt-1 border rounded-lg bg-white px-3">
                <option value="">اختر المشروع</option>
                {projects.filter(p => p.status === 'active').map((proj) => (
                  <option key={proj.id} value={proj.id}>{proj.name} - {proj.owner_name}</option>
                ))}
              </select>
            </div>
            <div>
              <Label className="text-sm font-medium">سبب الطلب</Label>
              <Textarea value={editReason} onChange={(e) => setEditReason(e.target.value)} rows={2} className="mt-1" />
            </div>
            <div>
              <Label className="text-sm font-medium">المهندس</Label>
              <select value={editEngineerId} onChange={(e) => setEditEngineerId(e.target.value)} className="w-full h-11 mt-1 border rounded-lg bg-white px-3">
                <option value="">اختر المهندس</option>
                {engineers.map((eng) => <option key={eng.id} value={eng.id}>{eng.name}</option>)}
              </select>
            </div>
            <Button type="submit" className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-bold" disabled={submitting || editItems.length === 0}>
              {submitting ? "جاري الحفظ..." : `حفظ التعديلات (${editItems.length} صنف)`}
            </Button>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delivery Dialog */}
      <Dialog open={deliveryDialogOpen} onOpenChange={setDeliveryDialogOpen}>
        <DialogContent className="w-[95vw] max-w-md max-h-[90vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader>
            <DialogTitle className="text-center flex items-center justify-center gap-2">
              <PackageCheck className="w-5 h-5 text-purple-600" />
              تسجيل استلام المواد
            </DialogTitle>
          </DialogHeader>
          
          {selectedDelivery && (
            <div className="space-y-4 mt-4">
              {/* Order Info */}
              <div className="bg-slate-50 p-3 rounded-lg">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><span className="text-slate-500">رقم الأمر:</span> <span className="font-mono font-bold text-orange-600">{selectedDelivery.id?.slice(0,8).toUpperCase()}</span></div>
                  <div><span className="text-slate-500">المورد:</span> {selectedDelivery.supplier_name}</div>
                  <div><span className="text-slate-500">المشروع:</span> {selectedDelivery.project_name}</div>
                  <div><span className="text-slate-500">الإجمالي:</span> {(selectedDelivery.total_amount || 0).toLocaleString('ar-SA')} ر.س</div>
                </div>
              </div>

              {/* Items to Deliver */}
              <div className="space-y-2">
                <Label className="text-sm font-medium">الأصناف المُسلَّمة</Label>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {deliveryItems.map((item, idx) => (
                    <div key={idx} className={`p-3 rounded-lg border ${item.remaining <= 0 ? 'bg-green-50 border-green-200' : 'bg-white'}`}>
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <p className="font-medium">{item.name}</p>
                          <p className="text-xs text-slate-500">
                            المطلوب: {item.quantity} | المُستلَم سابقاً: {item.delivered_quantity} | المتبقي: {item.remaining}
                          </p>
                        </div>
                        {item.remaining <= 0 && (
                          <Badge className="bg-green-100 text-green-800 text-xs">مكتمل</Badge>
                        )}
                      </div>
                      {item.remaining > 0 && (
                        <div className="flex items-center gap-2">
                          <Label className="text-xs text-slate-500 whitespace-nowrap">الكمية المُستلَمة:</Label>
                          <Input
                            type="number"
                            min="0"
                            max={item.remaining}
                            value={item.quantity_to_deliver || ""}
                            onChange={(e) => {
                              const val = Math.min(parseInt(e.target.value) || 0, item.remaining);
                              const newItems = [...deliveryItems];
                              newItems[idx].quantity_to_deliver = val;
                              setDeliveryItems(newItems);
                            }}
                            className="h-8 w-20 text-center"
                          />
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const newItems = [...deliveryItems];
                              newItems[idx].quantity_to_deliver = item.remaining;
                              setDeliveryItems(newItems);
                            }}
                            className="h-8 text-xs"
                          >
                            الكل
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Notes */}
              <div>
                <Label className="text-sm">ملاحظات الاستلام</Label>
                <Textarea
                  placeholder="أي ملاحظات على الاستلام..."
                  value={deliveryNotes}
                  onChange={(e) => setDeliveryNotes(e.target.value)}
                  rows={2}
                  className="mt-1"
                />
              </div>

              {/* Submit Button */}
              <Button
                className="w-full h-11 bg-purple-600 hover:bg-purple-700"
                onClick={handleRecordDelivery}
                disabled={submitting || !deliveryItems.some(item => item.quantity_to_deliver > 0)}
              >
                {submitting ? "جاري التسجيل..." : (
                  <>
                    <PackageCheck className="w-4 h-4 ml-2" />
                    تأكيد الاستلام ({deliveryItems.filter(i => i.quantity_to_deliver > 0).length} صنف)
                  </>
                )}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Projects Dialog */}
      <Dialog open={projectDialogOpen} onOpenChange={setProjectDialogOpen}>
        <DialogContent className="w-[95vw] max-w-2xl max-h-[90vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader>
            <DialogTitle>إدارة المشاريع</DialogTitle>
          </DialogHeader>
          
          {/* Add New Project Form */}
          <div className="bg-slate-50 p-4 rounded-lg space-y-3">
            <h3 className="font-medium text-sm mb-2">إضافة مشروع جديد</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">اسم المشروع *</Label>
                <Input 
                  placeholder="مثال: مشروع برج السلام" 
                  value={newProject.name}
                  onChange={(e) => setNewProject({...newProject, name: e.target.value})}
                  className="h-9 mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">اسم المالك *</Label>
                <Input 
                  placeholder="اسم مالك المشروع" 
                  value={newProject.owner_name}
                  onChange={(e) => setNewProject({...newProject, owner_name: e.target.value})}
                  className="h-9 mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">الموقع</Label>
                <Input 
                  placeholder="موقع المشروع" 
                  value={newProject.location}
                  onChange={(e) => setNewProject({...newProject, location: e.target.value})}
                  className="h-9 mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">الوصف</Label>
                <Input 
                  placeholder="وصف مختصر" 
                  value={newProject.description}
                  onChange={(e) => setNewProject({...newProject, description: e.target.value})}
                  className="h-9 mt-1"
                />
              </div>
            </div>
            <Button onClick={handleCreateProject} className="w-full sm:w-auto bg-orange-600 hover:bg-orange-700">
              <Plus className="w-4 h-4 ml-1" /> إضافة المشروع
            </Button>
          </div>

          {/* Projects List */}
          <div className="space-y-2 mt-4">
            <h3 className="font-medium text-sm">المشاريع ({projects.length})</h3>
            {projects.length === 0 ? (
              <p className="text-center text-slate-500 py-4">لا توجد مشاريع بعد</p>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {projects.map(proj => (
                  <div key={proj.id} className={`bg-white border rounded-lg p-3 ${proj.status !== 'active' ? 'opacity-60' : ''}`}>
                    {editingProject?.id === proj.id ? (
                      <div className="space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                          <Input 
                            placeholder="اسم المشروع"
                            value={editingProject.name}
                            onChange={(e) => setEditingProject({...editingProject, name: e.target.value})}
                            className="h-8"
                          />
                          <Input 
                            placeholder="اسم المالك"
                            value={editingProject.owner_name}
                            onChange={(e) => setEditingProject({...editingProject, owner_name: e.target.value})}
                            className="h-8"
                          />
                          <Input 
                            placeholder="الموقع"
                            value={editingProject.location || ""}
                            onChange={(e) => setEditingProject({...editingProject, location: e.target.value})}
                            className="h-8"
                          />
                          <select
                            value={editingProject.status}
                            onChange={(e) => setEditingProject({...editingProject, status: e.target.value})}
                            className="h-8 border rounded px-2 text-sm"
                          >
                            <option value="active">نشط</option>
                            <option value="completed">مكتمل</option>
                            <option value="on_hold">معلق</option>
                          </select>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" onClick={handleUpdateProject} className="bg-green-600 hover:bg-green-700">حفظ</Button>
                          <Button size="sm" variant="outline" onClick={() => setEditingProject(null)}>إلغاء</Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium">{proj.name}</p>
                            <Badge className={
                              proj.status === 'active' ? 'bg-green-100 text-green-800' :
                              proj.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                              'bg-yellow-100 text-yellow-800'
                            }>
                              {proj.status === 'active' ? 'نشط' : proj.status === 'completed' ? 'مكتمل' : 'معلق'}
                            </Badge>
                          </div>
                          <p className="text-xs text-slate-500">المالك: {proj.owner_name}</p>
                          {proj.location && <p className="text-xs text-slate-400">{proj.location}</p>}
                        </div>
                        <div className="text-left text-xs">
                          <p>الطلبات: <span className="font-medium">{proj.total_requests}</span></p>
                          <p>الأوامر: <span className="font-medium">{proj.total_orders}</span></p>
                          <p>المصروف: <span className="font-medium text-orange-600">{proj.total_spent?.toLocaleString('ar-SA')} ر.س</span></p>
                        </div>
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" onClick={() => setEditingProject({...proj})} className="h-8 w-8 p-0">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => handleDeleteProject(proj.id)} className="h-8 w-8 p-0 text-red-500 hover:text-red-700">
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Change Password Dialog */}
      <ChangePasswordDialog 
        open={passwordDialogOpen} 
        onOpenChange={setPasswordDialogOpen}
        token={localStorage.getItem("token")}
      />
    </div>
  );
};

export default SupervisorDashboard;
