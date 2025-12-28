import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Checkbox } from "../components/ui/checkbox";
import { Package, LogOut, Clock, CheckCircle, RefreshCw, FileText, ShoppingCart, Truck, Eye, Download, Calendar, Filter, Check, AlertCircle, Plus, Users, X, Edit, DollarSign, BarChart3, Trash2 } from "lucide-react";
import { exportRequestToPDF, exportPurchaseOrderToPDF, exportRequestsTableToPDF, exportPurchaseOrdersTableToPDF } from "../utils/pdfExport";

const ProcurementDashboard = () => {
  const { user, logout, getAuthHeaders, API_URL } = useAuth();
  const [requests, setRequests] = useState([]);
  const [allOrders, setAllOrders] = useState([]);
  const [filteredOrders, setFilteredOrders] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [orderDialogOpen, setOrderDialogOpen] = useState(false);
  const [viewRequestDialogOpen, setViewRequestDialogOpen] = useState(false);
  const [viewOrderDialogOpen, setViewOrderDialogOpen] = useState(false);
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [supplierDialogOpen, setSupplierDialogOpen] = useState(false);
  const [suppliersListDialogOpen, setSuppliersListDialogOpen] = useState(false);
  
  // Supplier selection
  const [selectedSupplierId, setSelectedSupplierId] = useState("");
  const [supplierName, setSupplierName] = useState("");
  const [orderNotes, setOrderNotes] = useState("");
  const [termsConditions, setTermsConditions] = useState("");
  const [expectedDeliveryDate, setExpectedDeliveryDate] = useState("");
  const [selectedItemIndices, setSelectedItemIndices] = useState([]);
  const [itemPrices, setItemPrices] = useState({});
  const [submitting, setSubmitting] = useState(false);
  
  // New supplier form
  const [newSupplier, setNewSupplier] = useState({ name: "", contact_person: "", phone: "", email: "", address: "", notes: "" });
  const [editingSupplier, setEditingSupplier] = useState(null);
  
  // Filter states
  const [filterStartDate, setFilterStartDate] = useState("");
  const [filterEndDate, setFilterEndDate] = useState("");
  const [filterOrderId, setFilterOrderId] = useState("");
  const [filterRequestId, setFilterRequestId] = useState("");
  const [filterProject, setFilterProject] = useState("");
  const [filterSupplier, setFilterSupplier] = useState("");
  const [reportStartDate, setReportStartDate] = useState("");
  const [reportEndDate, setReportEndDate] = useState("");

  // Budget Categories states
  const [budgetCategories, setBudgetCategories] = useState([]);
  const [budgetReport, setBudgetReport] = useState(null);
  const [budgetDialogOpen, setBudgetDialogOpen] = useState(false);
  const [budgetReportDialogOpen, setBudgetReportDialogOpen] = useState(false);
  const [newCategory, setNewCategory] = useState({ name: "", project_id: "", estimated_budget: "" });
  const [editingCategory, setEditingCategory] = useState(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState("");  // For PO creation
  const [projects, setProjects] = useState([]);
  const [projectReportDialogOpen, setProjectReportDialogOpen] = useState(false);
  const [selectedProjectReport, setSelectedProjectReport] = useState(null);

  const fetchData = async () => {
    try {
      const [requestsRes, ordersRes, statsRes, suppliersRes, categoriesRes, projectsRes] = await Promise.all([
        axios.get(`${API_URL}/requests`, getAuthHeaders()),
        axios.get(`${API_URL}/purchase-orders`, getAuthHeaders()),
        axios.get(`${API_URL}/dashboard/stats`, getAuthHeaders()),
        axios.get(`${API_URL}/suppliers`, getAuthHeaders()),
        axios.get(`${API_URL}/budget-categories`, getAuthHeaders()),
        axios.get(`${API_URL}/projects`, getAuthHeaders()),
      ]);
      setRequests(requestsRes.data);
      setAllOrders(ordersRes.data);
      setFilteredOrders(ordersRes.data);
      setStats(statsRes.data);
      setSuppliers(suppliersRes.data);
      setBudgetCategories(categoriesRes.data);
      setProjects(projectsRes.data || []);
    } catch (error) {
      toast.error("فشل في تحميل البيانات");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  // Apply filters
  const applyFilter = () => {
    let filtered = [...allOrders];
    
    // Filter by order ID
    if (filterOrderId.trim()) {
      filtered = filtered.filter(o => 
        o.id?.toLowerCase().includes(filterOrderId.toLowerCase().trim())
      );
    }
    
    // Filter by request ID
    if (filterRequestId.trim()) {
      filtered = filtered.filter(o => 
        o.request_id?.toLowerCase().includes(filterRequestId.toLowerCase().trim())
      );
    }
    
    // Filter by project
    if (filterProject.trim()) {
      filtered = filtered.filter(o => 
        o.project_name?.toLowerCase().includes(filterProject.toLowerCase().trim())
      );
    }
    
    // Filter by supplier
    if (filterSupplier.trim()) {
      filtered = filtered.filter(o => 
        o.supplier_name?.toLowerCase().includes(filterSupplier.toLowerCase().trim())
      );
    }
    
    // Filter by start date
    if (filterStartDate) {
      const start = new Date(filterStartDate);
      start.setHours(0, 0, 0, 0);
      filtered = filtered.filter(o => new Date(o.created_at) >= start);
    }
    
    // Filter by end date
    if (filterEndDate) {
      const end = new Date(filterEndDate);
      end.setHours(23, 59, 59, 999);
      filtered = filtered.filter(o => new Date(o.created_at) <= end);
    }
    
    setFilteredOrders(filtered);
    toast.success(`تم عرض ${filtered.length} أمر شراء`);
  };

  const clearFilter = () => {
    setFilterStartDate("");
    setFilterEndDate("");
    setFilterOrderId("");
    setFilterRequestId("");
    setFilterProject("");
    setFilterSupplier("");
    setFilteredOrders(allOrders);
  };

  // Supplier management functions
  const handleCreateSupplier = async () => {
    if (!newSupplier.name.trim()) {
      toast.error("الرجاء إدخال اسم المورد");
      return;
    }
    
    try {
      const res = await axios.post(`${API_URL}/suppliers`, newSupplier, getAuthHeaders());
      setSuppliers([...suppliers, res.data]);
      setNewSupplier({ name: "", contact_person: "", phone: "", email: "", address: "", notes: "" });
      setSupplierDialogOpen(false);
      toast.success("تم إضافة المورد بنجاح");
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في إضافة المورد");
    }
  };

  const handleUpdateSupplier = async () => {
    if (!editingSupplier || !editingSupplier.name.trim()) {
      toast.error("الرجاء إدخال اسم المورد");
      return;
    }
    
    try {
      const res = await axios.put(`${API_URL}/suppliers/${editingSupplier.id}`, editingSupplier, getAuthHeaders());
      setSuppliers(suppliers.map(s => s.id === editingSupplier.id ? res.data : s));
      setEditingSupplier(null);
      toast.success("تم تحديث المورد بنجاح");
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تحديث المورد");
    }
  };

  const handleDeleteSupplier = async (supplierId) => {
    if (!window.confirm("هل أنت متأكد من حذف هذا المورد؟")) return;
    
    try {
      await axios.delete(`${API_URL}/suppliers/${supplierId}`, getAuthHeaders());
      setSuppliers(suppliers.filter(s => s.id !== supplierId));
      toast.success("تم حذف المورد بنجاح");
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في حذف المورد");
    }
  };

  // Calculate total amount
  const calculateTotal = () => {
    return selectedItemIndices.reduce((total, idx) => {
      const price = itemPrices[idx] || 0;
      const item = remainingItems[idx];
      return total + (price * (item?.quantity || 0));
    }, 0);
  };

  // Generate report
  const generateReport = () => {
    if (!reportStartDate || !reportEndDate) {
      toast.error("الرجاء تحديد تاريخ البداية والنهاية");
      return;
    }
    
    const start = new Date(reportStartDate);
    start.setHours(0, 0, 0, 0);
    const end = new Date(reportEndDate);
    end.setHours(23, 59, 59, 999);
    
    const reportOrders = allOrders.filter(o => {
      const orderDate = new Date(o.created_at);
      return orderDate >= start && orderDate <= end;
    });

    if (reportOrders.length === 0) {
      toast.error("لا توجد أوامر شراء في هذه الفترة");
      return;
    }

    exportPurchaseOrdersTableToPDF(reportOrders);
    toast.success(`تم تصدير تقرير بـ ${reportOrders.length} أمر شراء`);
    setReportDialogOpen(false);
  };

  // Budget Categories Functions
  const handleCreateCategory = async () => {
    if (!newCategory.name || !newCategory.project_id || !newCategory.estimated_budget) {
      toast.error("الرجاء ملء جميع الحقول");
      return;
    }
    try {
      await axios.post(`${API_URL}/budget-categories`, {
        name: newCategory.name,
        project_id: newCategory.project_id,
        estimated_budget: parseFloat(newCategory.estimated_budget)
      }, getAuthHeaders());
      toast.success("تم إضافة التصنيف بنجاح");
      setNewCategory({ name: "", project_id: "", estimated_budget: "" });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في إضافة التصنيف");
    }
  };

  const handleUpdateCategory = async () => {
    if (!editingCategory) return;
    try {
      await axios.put(`${API_URL}/budget-categories/${editingCategory.id}`, {
        name: editingCategory.name,
        estimated_budget: parseFloat(editingCategory.estimated_budget)
      }, getAuthHeaders());
      toast.success("تم تحديث التصنيف بنجاح");
      setEditingCategory(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تحديث التصنيف");
    }
  };

  const handleDeleteCategory = async (categoryId) => {
    if (!window.confirm("هل أنت متأكد من حذف هذا التصنيف؟")) return;
    try {
      await axios.delete(`${API_URL}/budget-categories/${categoryId}`, getAuthHeaders());
      toast.success("تم حذف التصنيف بنجاح");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في حذف التصنيف");
    }
  };

  const fetchBudgetReport = async () => {
    try {
      const res = await axios.get(`${API_URL}/budget-reports`, getAuthHeaders());
      setBudgetReport(res.data);
      setBudgetReportDialogOpen(true);
    } catch (error) {
      toast.error("فشل في تحميل تقرير الميزانية");
    }
  };

  // State for remaining items
  const [remainingItems, setRemainingItems] = useState([]);
  const [loadingItems, setLoadingItems] = useState(false);

  const openOrderDialog = async (request) => {
    setSelectedRequest(request);
    setSelectedSupplierId("");
    setSupplierName("");
    setOrderNotes("");
    setTermsConditions("");
    setExpectedDeliveryDate("");
    setSelectedItemIndices([]);
    setItemPrices({});
    setSelectedCategoryId("");  // Reset category selection
    setLoadingItems(true);
    setOrderDialogOpen(true);
    
    try {
      // Fetch remaining items from API
      const res = await axios.get(`${API_URL}/requests/${request.id}/remaining-items`, getAuthHeaders());
      const remaining = res.data.remaining_items || [];
      setRemainingItems(remaining);
      // Select all remaining items by default
      setSelectedItemIndices(remaining.map(item => item.index));
    } catch (error) {
      // If API fails, show all items
      setRemainingItems(request.items.map((item, idx) => ({ index: idx, ...item })));
      setSelectedItemIndices(request.items.map((_, idx) => idx));
    } finally {
      setLoadingItems(false);
    }
  };

  const toggleItemSelection = (idx) => {
    setSelectedItemIndices(prev => 
      prev.includes(idx) 
        ? prev.filter(i => i !== idx)
        : [...prev, idx]
    );
  };

  const selectAllItems = () => {
    setSelectedItemIndices(remainingItems.map(item => item.index));
  };

  const deselectAllItems = () => {
    setSelectedItemIndices([]);
  };

  const handleCreateOrder = async () => {
    if (!supplierName.trim()) { toast.error("الرجاء إدخال اسم المورد"); return; }
    if (selectedItemIndices.length === 0) { toast.error("الرجاء اختيار صنف واحد على الأقل"); return; }
    
    // Build item prices array
    const pricesArray = selectedItemIndices.map(idx => ({
      index: idx,
      unit_price: parseFloat(itemPrices[idx]) || 0
    }));
    
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/purchase-orders`, { 
        request_id: selectedRequest.id, 
        supplier_id: selectedSupplierId || null,
        supplier_name: supplierName, 
        selected_items: selectedItemIndices,
        item_prices: pricesArray,
        category_id: selectedCategoryId || null,  // Budget category
        notes: orderNotes,
        terms_conditions: termsConditions,
        expected_delivery_date: expectedDeliveryDate || null
      }, getAuthHeaders());
      toast.success("تم إصدار أمر الشراء بنجاح");
      setOrderDialogOpen(false);
      setSelectedSupplierId("");
      setSupplierName("");
      setOrderNotes("");
      setTermsConditions("");
      setExpectedDeliveryDate("");
      setSelectedItemIndices([]);
      setItemPrices({});
      setSelectedCategoryId("");
      setSelectedRequest(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في إصدار أمر الشراء");
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveOrder = async (orderId) => {
    try {
      await axios.put(`${API_URL}/purchase-orders/${orderId}/approve`, {}, getAuthHeaders());
      toast.success("تم اعتماد أمر الشراء");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في اعتماد أمر الشراء");
    }
  };

  const formatDate = (dateString) => new Date(dateString).toLocaleDateString("ar-SA", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const formatDateFull = (dateString) => new Date(dateString).toLocaleDateString("ar-SA", { year: "numeric", month: "long", day: "numeric" });
  const formatCurrency = (amount) => `${(amount || 0).toLocaleString('ar-SA')} ر.س`;
  
  const getItemsSummary = (items) => !items?.length ? "-" : items.length === 1 ? items[0].name : `${items[0].name} +${items.length - 1}`;

  const getRequestStatusBadge = (status) => {
    const map = {
      approved_by_engineer: { label: "معتمد", color: "bg-green-100 text-green-800 border-green-300" },
      partially_ordered: { label: "جاري الإصدار", color: "bg-yellow-100 text-yellow-800 border-yellow-300" },
      purchase_order_issued: { label: "تم الإصدار", color: "bg-blue-100 text-blue-800 border-blue-300" },
    };
    const info = map[status] || { label: status, color: "bg-slate-100 text-slate-800" };
    return <Badge className={`${info.color} border text-xs`}>{info.label}</Badge>;
  };

  const getOrderStatusBadge = (status) => {
    const map = {
      pending_approval: { label: "بانتظار الاعتماد", color: "bg-yellow-100 text-yellow-800 border-yellow-300" },
      approved: { label: "معتمد", color: "bg-green-100 text-green-800 border-green-300" },
      printed: { label: "تمت الطباعة", color: "bg-blue-100 text-blue-800 border-blue-300" },
      shipped: { label: "تم الشحن", color: "bg-purple-100 text-purple-800 border-purple-300" },
      partially_delivered: { label: "تسليم جزئي", color: "bg-orange-100 text-orange-800 border-orange-300" },
      delivered: { label: "تم التسليم", color: "bg-emerald-100 text-emerald-800 border-emerald-300" },
    };
    const info = map[status] || { label: status, color: "bg-slate-100 text-slate-800" };
    return <Badge className={`${info.color} border text-xs`}>{info.label}</Badge>;
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-slate-50"><div className="w-10 h-10 border-4 border-orange-600 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  // Filter orders by status
  const pendingApprovalOrders = filteredOrders.filter(o => o.status === "pending_approval");
  const approvedOrders = filteredOrders.filter(o => o.status !== "pending_approval");

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
                <p className="text-xs text-slate-400">مدير المشتريات</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => setBudgetDialogOpen(true)} className="text-slate-300 hover:text-white h-8 px-2">
                <DollarSign className="w-4 h-4 ml-1" /><span className="hidden sm:inline">الميزانيات</span>
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setSuppliersListDialogOpen(true)} className="text-slate-300 hover:text-white h-8 px-2">
                <Users className="w-4 h-4 ml-1" /><span className="hidden sm:inline">الموردين</span>
              </Button>
              <span className="text-xs sm:text-sm text-slate-300 hidden sm:inline">{user?.name}</span>
              <Button variant="ghost" size="sm" onClick={logout} className="text-slate-300 hover:text-white h-8 px-2">
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-3 sm:px-6 py-4">
        {/* Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          <Card className="border-r-4 border-yellow-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">طلبات معلقة</p>
              <p className="text-2xl font-bold text-yellow-600">{stats.pending_orders || 0}</p>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-orange-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">بانتظار الاعتماد</p>
              <p className="text-2xl font-bold text-orange-600">{stats.pending_approval || 0}</p>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-green-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">أوامر معتمدة</p>
              <p className="text-2xl font-bold text-green-600">{stats.approved_orders || 0}</p>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-blue-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">إجمالي الأوامر</p>
              <p className="text-2xl font-bold text-blue-600">{stats.total_orders || 0}</p>
            </CardContent>
          </Card>
        </div>

        {/* Approved Requests */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <Clock className="w-5 h-5 text-yellow-600" />
              طلبات معتمدة
              {requests.length > 0 && <Badge className="bg-yellow-500 text-white">{requests.length}</Badge>}
            </h2>
            <Button variant="outline" size="sm" onClick={fetchData} className="h-8"><RefreshCw className="w-3 h-3" /></Button>
          </div>

          <Card className="shadow-sm">
            <CardContent className="p-0">
              {!requests.length ? (
                <div className="text-center py-8"><CheckCircle className="w-10 h-10 text-green-300 mx-auto mb-2" /><p className="text-slate-500 text-sm">لا توجد طلبات معلقة</p></div>
              ) : (
                <>
                  {/* Mobile */}
                  <div className="sm:hidden divide-y">
                    {requests.map((req) => (
                      <div key={req.id} className="p-3 space-y-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium text-sm">{getItemsSummary(req.items)}</p>
                            <p className="text-xs text-slate-500">{req.project_name}</p>
                          </div>
                          {getRequestStatusBadge(req.status)}
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-xs text-slate-400">{formatDate(req.created_at)}</span>
                          <div className="flex gap-1">
                            <Button size="sm" variant="ghost" onClick={() => { setSelectedRequest(req); setViewRequestDialogOpen(true); }} className="h-7 w-7 p-0"><Eye className="w-3 h-3" /></Button>
                            <Button size="sm" className="bg-orange-600 h-7 text-xs px-2" onClick={() => openOrderDialog(req)}>
                              <ShoppingCart className="w-3 h-3 ml-1" />إصدار
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {/* Desktop */}
                  <div className="hidden sm:block overflow-x-auto">
                    <Table>
                      <TableHeader><TableRow className="bg-slate-50">
                        <TableHead className="text-right">الأصناف</TableHead>
                        <TableHead className="text-right">المشروع</TableHead>
                        <TableHead className="text-right">المشرف</TableHead>
                        <TableHead className="text-right">الحالة</TableHead>
                        <TableHead className="text-right">التاريخ</TableHead>
                        <TableHead className="text-right">الإجراء</TableHead>
                      </TableRow></TableHeader>
                      <TableBody>
                        {requests.map((req) => (
                          <TableRow key={req.id}>
                            <TableCell className="font-medium">{getItemsSummary(req.items)}</TableCell>
                            <TableCell>{req.project_name}</TableCell>
                            <TableCell>{req.supervisor_name}</TableCell>
                            <TableCell>{getRequestStatusBadge(req.status)}</TableCell>
                            <TableCell className="text-sm text-slate-500">{formatDate(req.created_at)}</TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                <Button size="sm" variant="ghost" onClick={() => { setSelectedRequest(req); setViewRequestDialogOpen(true); }} className="h-8 w-8 p-0"><Eye className="w-4 h-4" /></Button>
                                <Button size="sm" className="bg-orange-600 hover:bg-orange-700" onClick={() => openOrderDialog(req)}>
                                  <ShoppingCart className="w-4 h-4 ml-1" />إصدار أمر
                                </Button>
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
        </div>

        {/* Pending Approval Orders */}
        {pendingApprovalOrders.length > 0 && (
          <div className="mb-6">
            <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
              <AlertCircle className="w-5 h-5 text-orange-600" />
              أوامر بانتظار الاعتماد
              <Badge className="bg-orange-500 text-white">{pendingApprovalOrders.length}</Badge>
            </h2>
            <Card className="shadow-sm">
              <CardContent className="p-0">
                <div className="sm:hidden divide-y">
                  {pendingApprovalOrders.map((order) => (
                    <div key={order.id} className="p-3 space-y-2">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium text-sm">{getItemsSummary(order.items)}</p>
                          <p className="text-xs text-slate-500">{order.supplier_name}</p>
                        </div>
                        {getOrderStatusBadge(order.status)}
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-slate-400">{formatDate(order.created_at)}</span>
                        <Button size="sm" className="bg-green-600 h-7 text-xs px-2" onClick={() => handleApproveOrder(order.id)}>
                          <Check className="w-3 h-3 ml-1" />اعتماد
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="hidden sm:block overflow-x-auto">
                  <Table>
                    <TableHeader><TableRow className="bg-orange-50">
                      <TableHead className="text-right">الأصناف</TableHead>
                      <TableHead className="text-right">المشروع</TableHead>
                      <TableHead className="text-right">المورد</TableHead>
                      <TableHead className="text-right">التاريخ</TableHead>
                      <TableHead className="text-right">الإجراء</TableHead>
                    </TableRow></TableHeader>
                    <TableBody>
                      {pendingApprovalOrders.map((order) => (
                        <TableRow key={order.id}>
                          <TableCell className="font-medium">{getItemsSummary(order.items)}</TableCell>
                          <TableCell>{order.project_name}</TableCell>
                          <TableCell><Badge className="bg-green-50 text-green-800 border-green-200 border">{order.supplier_name}</Badge></TableCell>
                          <TableCell className="text-sm text-slate-500">{formatDate(order.created_at)}</TableCell>
                          <TableCell>
                            <Button size="sm" className="bg-green-600 hover:bg-green-700" onClick={() => handleApproveOrder(order.id)}>
                              <Check className="w-4 h-4 ml-1" />اعتماد
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Purchase Orders with Filter */}
        <div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <Truck className="w-5 h-5 text-green-600" />أوامر الشراء
            </h2>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => setReportDialogOpen(true)} className="h-8 text-xs">
                <FileText className="w-3 h-3 ml-1" />تقرير بتاريخ
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportPurchaseOrdersTableToPDF(approvedOrders)} disabled={!approvedOrders.length} className="h-8 text-xs">
                <Download className="w-3 h-3 ml-1" />تصدير
              </Button>
            </div>
          </div>

          {/* Advanced Filters */}
          <Card className="mb-3 bg-slate-50">
            <CardContent className="p-3">
              <div className="space-y-3">
                {/* Row 1: Order ID, Request ID, Project, Supplier */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div>
                    <Label className="text-xs">رقم أمر الشراء</Label>
                    <Input 
                      placeholder="ابحث..." 
                      value={filterOrderId} 
                      onChange={(e) => setFilterOrderId(e.target.value)} 
                      className="h-9 text-sm" 
                    />
                  </div>
                  <div>
                    <Label className="text-xs">رقم الطلب</Label>
                    <Input 
                      placeholder="ابحث..." 
                      value={filterRequestId} 
                      onChange={(e) => setFilterRequestId(e.target.value)} 
                      className="h-9 text-sm" 
                    />
                  </div>
                  <div>
                    <Label className="text-xs">المشروع</Label>
                    <Input 
                      placeholder="ابحث..." 
                      value={filterProject} 
                      onChange={(e) => setFilterProject(e.target.value)} 
                      className="h-9 text-sm" 
                    />
                  </div>
                  <div>
                    <Label className="text-xs">المورد</Label>
                    <Input 
                      placeholder="ابحث..." 
                      value={filterSupplier} 
                      onChange={(e) => setFilterSupplier(e.target.value)} 
                      className="h-9 text-sm" 
                    />
                  </div>
                </div>
                {/* Row 2: Dates and Buttons */}
                <div className="flex flex-col sm:flex-row gap-2 items-end">
                  <div className="flex-1 grid grid-cols-2 gap-2">
                    <div>
                      <Label className="text-xs">من تاريخ</Label>
                      <Input type="date" value={filterStartDate} onChange={(e) => setFilterStartDate(e.target.value)} className="h-9 text-sm" />
                    </div>
                    <div>
                      <Label className="text-xs">إلى تاريخ</Label>
                      <Input type="date" value={filterEndDate} onChange={(e) => setFilterEndDate(e.target.value)} className="h-9 text-sm" />
                    </div>
                  </div>
                  <div className="flex gap-2 w-full sm:w-auto">
                    <Button size="sm" onClick={applyFilter} className="flex-1 sm:flex-none h-9 bg-orange-600 hover:bg-orange-700">
                      <Filter className="w-3 h-3 ml-1" />فلترة
                    </Button>
                    <Button size="sm" variant="outline" onClick={clearFilter} className="h-9">مسح</Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-sm">
            <CardContent className="p-0">
              {!approvedOrders.length ? (
                <div className="text-center py-8"><FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" /><p className="text-slate-500 text-sm">لا توجد أوامر شراء معتمدة</p></div>
              ) : (
                <>
                  {/* Mobile */}
                  <div className="sm:hidden divide-y">
                    {approvedOrders.map((order) => (
                      <div key={order.id} className="p-3 space-y-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-mono text-orange-600 font-bold text-sm">{order.id?.slice(0, 8).toUpperCase()}</p>
                            <p className="text-xs text-slate-500">{order.project_name}</p>
                          </div>
                          {getOrderStatusBadge(order.status)}
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div><span className="text-slate-400">رقم الطلب:</span> <span className="font-bold text-blue-600">{order.request_number || order.request_id?.slice(0, 8).toUpperCase()}</span></div>
                          <div><span className="text-slate-400">المورد:</span> {order.supplier_name}</div>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-xs text-slate-400">{formatDate(order.created_at)}</span>
                          <div className="flex gap-1">
                            <Button size="sm" variant="ghost" onClick={() => { setSelectedOrder(order); setViewOrderDialogOpen(true); }} className="h-7 w-7 p-0"><Eye className="w-3 h-3" /></Button>
                            <Button size="sm" variant="ghost" onClick={() => exportPurchaseOrderToPDF(order)} className="h-7 w-7 p-0"><Download className="w-3 h-3 text-green-600" /></Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {/* Desktop */}
                  <div className="hidden sm:block overflow-x-auto">
                    <Table>
                      <TableHeader><TableRow className="bg-slate-50">
                        <TableHead className="text-right">رقم أمر الشراء</TableHead>
                        <TableHead className="text-right">رقم الطلب</TableHead>
                        <TableHead className="text-right">المشروع</TableHead>
                        <TableHead className="text-right">المورد</TableHead>
                        <TableHead className="text-right">المبلغ</TableHead>
                        <TableHead className="text-right">الحالة</TableHead>
                        <TableHead className="text-right">الإجراءات</TableHead>
                      </TableRow></TableHeader>
                      <TableBody>
                        {approvedOrders.map((order) => (
                          <TableRow key={order.id}>
                            <TableCell className="font-mono text-orange-600 font-bold">{order.id?.slice(0, 8).toUpperCase()}</TableCell>
                            <TableCell className="font-bold text-blue-600">{order.request_number || order.request_id?.slice(0, 8).toUpperCase()}</TableCell>
                            <TableCell>{order.project_name}</TableCell>
                            <TableCell><Badge className="bg-green-50 text-green-800 border-green-200 border">{order.supplier_name}</Badge></TableCell>
                            <TableCell className="font-bold text-emerald-600">{order.total_amount > 0 ? `${order.total_amount.toLocaleString('ar-SA')} ر.س` : '-'}</TableCell>
                            <TableCell>{getOrderStatusBadge(order.status)}</TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                <Button size="sm" variant="ghost" onClick={() => { setSelectedOrder(order); setViewOrderDialogOpen(true); }} className="h-8 w-8 p-0"><Eye className="w-4 h-4" /></Button>
                                <Button size="sm" variant="ghost" onClick={() => exportPurchaseOrderToPDF(order)} className="h-8 w-8 p-0"><Download className="w-4 h-4 text-green-600" /></Button>
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
        </div>
      </main>

      {/* View Request Dialog */}
      <Dialog open={viewRequestDialogOpen} onOpenChange={setViewRequestDialogOpen}>
        <DialogContent className="w-[95vw] max-w-md max-h-[85vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader><DialogTitle className="text-center">تفاصيل الطلب</DialogTitle></DialogHeader>
          {selectedRequest && (
            <div className="space-y-3 mt-2">
              <div className="bg-slate-50 p-3 rounded-lg space-y-2">
                <p className="text-sm font-medium border-b pb-2">الأصناف:</p>
                {selectedRequest.items?.map((item, idx) => (
                  <div key={idx} className="flex justify-between text-sm bg-white p-2 rounded">
                    <span>{item.name}</span>
                    <span className="text-slate-600">{item.quantity} {item.unit}</span>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-slate-500">المشروع:</span><p className="font-medium">{selectedRequest.project_name}</p></div>
                <div><span className="text-slate-500">المشرف:</span><p className="font-medium">{selectedRequest.supervisor_name}</p></div>
              </div>
              <Button className="w-full bg-green-600 hover:bg-green-700" onClick={() => exportRequestToPDF(selectedRequest)}>
                <Download className="w-4 h-4 ml-2" />تصدير PDF
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* View Order Dialog */}
      <Dialog open={viewOrderDialogOpen} onOpenChange={setViewOrderDialogOpen}>
        <DialogContent className="w-[95vw] max-w-md max-h-[85vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader><DialogTitle className="text-center">تفاصيل أمر الشراء</DialogTitle></DialogHeader>
          {selectedOrder && (
            <div className="space-y-3 mt-2">
              <div className="text-center pb-2 border-b">
                <p className="text-xs text-slate-500">رقم الأمر</p>
                <p className="text-lg font-bold text-orange-600">{selectedOrder.id.slice(0, 8).toUpperCase()}</p>
                <p className="text-xs text-slate-400">رقم الطلب: {selectedOrder.request_id?.slice(0, 8).toUpperCase()}</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg space-y-2">
                <p className="text-sm font-medium border-b pb-2">الأصناف:</p>
                {selectedOrder.items?.map((item, idx) => (
                  <div key={idx} className="flex justify-between text-sm bg-white p-2 rounded">
                    <div>
                      <span className="font-medium">{item.name}</span>
                      <span className="text-slate-500 mr-2">({item.quantity} {item.unit})</span>
                    </div>
                    {item.unit_price > 0 && (
                      <div className="text-left">
                        <span className="text-slate-600 text-xs">{item.unit_price} × {item.quantity} = </span>
                        <span className="font-bold text-emerald-600">{(item.total_price || item.unit_price * item.quantity).toLocaleString('ar-SA')} ر.س</span>
                      </div>
                    )}
                  </div>
                ))}
                {selectedOrder.total_amount > 0 && (
                  <div className="flex justify-between items-center pt-2 border-t mt-2">
                    <span className="font-bold">الإجمالي:</span>
                    <span className="text-lg font-bold text-orange-600">{selectedOrder.total_amount.toLocaleString('ar-SA')} ر.س</span>
                  </div>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-slate-500">المشروع:</span><p className="font-medium">{selectedOrder.project_name}</p></div>
                <div><span className="text-slate-500">المورد:</span><Badge className="bg-green-50 text-green-800 border">{selectedOrder.supplier_name}</Badge></div>
                <div><span className="text-slate-500">المشرف:</span><p className="font-medium">{selectedOrder.supervisor_name || '-'}</p></div>
                <div><span className="text-slate-500">المهندس:</span><p className="font-medium">{selectedOrder.engineer_name || '-'}</p></div>
              </div>
              <div><span className="text-slate-500 text-sm">الحالة:</span> {getOrderStatusBadge(selectedOrder.status)}</div>
              {selectedOrder.notes && <div><span className="text-slate-500 text-sm">ملاحظات:</span><p className="text-sm">{selectedOrder.notes}</p></div>}
              <Button className="w-full bg-green-600 hover:bg-green-700" onClick={() => exportPurchaseOrderToPDF(selectedOrder)}>
                <Download className="w-4 h-4 ml-2" />تصدير PDF
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Create Order Dialog - Shows only remaining items */}
      <Dialog open={orderDialogOpen} onOpenChange={setOrderDialogOpen}>
        <DialogContent className="w-[95vw] max-w-lg max-h-[90vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader><DialogTitle className="text-center">إصدار أمر شراء</DialogTitle></DialogHeader>
          {selectedRequest && (
            <div className="space-y-4 mt-2">
              <div className="bg-slate-50 p-3 rounded-lg space-y-2 text-sm">
                <div className="flex justify-between items-center border-b pb-2">
                  <span className="text-slate-500 font-medium">المشروع:</span>
                  <span className="font-medium">{selectedRequest.project_name}</span>
                </div>
                <div className="pt-2">
                  {loadingItems ? (
                    <div className="text-center py-4">
                      <div className="w-6 h-6 border-2 border-orange-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
                      <p className="text-slate-500 text-xs mt-2">جاري تحميل الأصناف...</p>
                    </div>
                  ) : remainingItems.length === 0 ? (
                    <div className="text-center py-4 bg-green-50 rounded-lg">
                      <CheckCircle className="w-8 h-8 text-green-500 mx-auto mb-2" />
                      <p className="text-green-700 font-medium">تم إصدار أوامر شراء لجميع الأصناف</p>
                    </div>
                  ) : (
                    <>
                      <div className="flex justify-between items-center mb-2">
                        <p className="text-slate-500 font-medium">الأصناف المتبقية ({remainingItems.length}):</p>
                        <div className="flex gap-1">
                          <Button size="sm" variant="outline" onClick={selectAllItems} className="h-6 text-xs px-2">الكل</Button>
                          <Button size="sm" variant="outline" onClick={deselectAllItems} className="h-6 text-xs px-2">إلغاء</Button>
                        </div>
                      </div>
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {remainingItems.map((item) => (
                          <div 
                            key={item.index} 
                            className={`flex items-center justify-between p-2 rounded border cursor-pointer transition-colors ${
                              selectedItemIndices.includes(item.index) 
                                ? 'bg-green-50 border-green-300' 
                                : 'bg-white border-slate-200 hover:bg-slate-50'
                            }`}
                            onClick={() => toggleItemSelection(item.index)}
                          >
                            <div className="flex items-center gap-2">
                              <Checkbox 
                                checked={selectedItemIndices.includes(item.index)}
                                onCheckedChange={() => toggleItemSelection(item.index)}
                              />
                              <span className="font-medium">{item.name}</span>
                            </div>
                            <span className="text-slate-600">{item.quantity} {item.unit}</span>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-slate-500 mt-2 text-center">
                        تم اختيار {selectedItemIndices.length} من {remainingItems.length} أصناف متبقية
                      </p>
                    </>
                  )}
                </div>
              </div>
              {remainingItems.length > 0 && (
                <>
                  {/* Supplier Selection */}
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">المورد</Label>
                    <div className="flex gap-2">
                      <select 
                        value={selectedSupplierId}
                        onChange={(e) => {
                          setSelectedSupplierId(e.target.value);
                          const supplier = suppliers.find(s => s.id === e.target.value);
                          if (supplier) setSupplierName(supplier.name);
                        }}
                        className="flex-1 h-10 border rounded-lg bg-white px-3 text-sm"
                      >
                        <option value="">-- اختر من القائمة --</option>
                        {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                      </select>
                      <Button type="button" variant="outline" size="sm" onClick={() => setSupplierDialogOpen(true)} className="h-10 px-3">
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                    <Input 
                      placeholder="أو اكتب اسم المورد يدوياً" 
                      value={supplierName} 
                      onChange={(e) => { setSupplierName(e.target.value); setSelectedSupplierId(""); }} 
                      className="h-10" 
                    />
                  </div>

                  {/* Budget Category Selection */}
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">تصنيف الميزانية</Label>
                    <select 
                      value={selectedCategoryId}
                      onChange={(e) => setSelectedCategoryId(e.target.value)}
                      className="w-full h-10 border rounded-lg bg-white px-3 text-sm"
                    >
                      <option value="">-- اختر التصنيف (اختياري) --</option>
                      {budgetCategories
                        .filter(c => c.project_name === selectedRequest?.project_name)
                        .map(c => (
                          <option key={c.id} value={c.id}>
                            {c.name} - متبقي: {(c.remaining || 0).toLocaleString('ar-SA')} ر.س
                          </option>
                        ))
                      }
                    </select>
                    {selectedCategoryId && (() => {
                      const cat = budgetCategories.find(c => c.id === selectedCategoryId);
                      if (!cat) return null;
                      const total = calculateTotal();
                      const willExceed = total > cat.remaining;
                      return (
                        <div className={`text-xs p-2 rounded ${willExceed ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
                          {willExceed 
                            ? `⚠️ تجاوز الميزانية بـ ${(total - cat.remaining).toLocaleString('ar-SA')} ر.س`
                            : `✓ ضمن الميزانية - سيتبقى ${(cat.remaining - total).toLocaleString('ar-SA')} ر.س`
                          }
                        </div>
                      );
                    })()}
                  </div>

                  {/* Item Prices */}
                  {selectedItemIndices.length > 0 && (
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">أسعار الأصناف المختارة</Label>
                      <div className="space-y-2 bg-slate-50 p-3 rounded-lg max-h-40 overflow-y-auto">
                        {selectedItemIndices.map(idx => {
                          const item = remainingItems.find(i => i.index === idx);
                          if (!item) return null;
                          return (
                            <div key={idx} className="flex items-center gap-2 bg-white p-2 rounded border">
                              <div className="flex-1">
                                <p className="text-sm font-medium">{item.name}</p>
                                <p className="text-xs text-slate-500">{item.quantity} {item.unit}</p>
                              </div>
                              <Input 
                                type="number" 
                                min="0" 
                                step="0.01"
                                placeholder="السعر"
                                value={itemPrices[idx] || ""}
                                onChange={(e) => setItemPrices({...itemPrices, [idx]: e.target.value})}
                                className="w-24 h-8 text-sm text-center"
                              />
                              <span className="text-xs text-slate-500">ر.س</span>
                            </div>
                          );
                        })}
                      </div>
                      <div className="flex justify-between items-center bg-orange-50 p-2 rounded-lg">
                        <span className="text-sm font-medium">الإجمالي:</span>
                        <span className="text-lg font-bold text-orange-600">{formatCurrency(calculateTotal())}</span>
                      </div>
                    </div>
                  )}

                  {/* Expected Delivery Date */}
                  <div>
                    <Label className="text-sm">تاريخ التسليم المتوقع</Label>
                    <Input type="date" value={expectedDeliveryDate} onChange={(e) => setExpectedDeliveryDate(e.target.value)} className="h-10 mt-1" />
                  </div>

                  {/* Notes & Terms */}
                  <div>
                    <Label className="text-sm">ملاحظات (اختياري)</Label>
                    <Textarea placeholder="أي ملاحظات..." value={orderNotes} onChange={(e) => setOrderNotes(e.target.value)} rows={2} className="mt-1" />
                  </div>
                  <div>
                    <Label className="text-sm">الشروط والأحكام (اختياري)</Label>
                    <Textarea placeholder="شروط الدفع والتسليم..." value={termsConditions} onChange={(e) => setTermsConditions(e.target.value)} rows={2} className="mt-1" />
                  </div>

                  <Button 
                    className="w-full h-11 bg-orange-600 hover:bg-orange-700" 
                    onClick={handleCreateOrder} 
                    disabled={submitting || selectedItemIndices.length === 0}
                  >
                    {submitting ? "جاري الإصدار..." : <><ShoppingCart className="w-4 h-4 ml-2" />إصدار أمر شراء ({selectedItemIndices.length} صنف) - {formatCurrency(calculateTotal())}</>}
                  </Button>
                </>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Suppliers List Dialog */}
      <Dialog open={suppliersListDialogOpen} onOpenChange={setSuppliersListDialogOpen}>
        <DialogContent className="w-[95vw] max-w-2xl max-h-[85vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader>
            <DialogTitle className="flex justify-between items-center">
              <span>إدارة الموردين</span>
              <Button size="sm" onClick={() => { setSupplierDialogOpen(true); setSuppliersListDialogOpen(false); }} className="bg-orange-600 hover:bg-orange-700">
                <Plus className="w-4 h-4 ml-1" />إضافة مورد
              </Button>
            </DialogTitle>
          </DialogHeader>
          <div className="mt-4">
            {suppliers.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <Users className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                <p>لا يوجد موردين مسجلين</p>
                <Button size="sm" className="mt-3 bg-orange-600" onClick={() => { setSupplierDialogOpen(true); setSuppliersListDialogOpen(false); }}>
                  <Plus className="w-4 h-4 ml-1" />إضافة مورد جديد
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {suppliers.map(supplier => (
                  <div key={supplier.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                    <div>
                      <p className="font-medium">{supplier.name}</p>
                      <p className="text-xs text-slate-500">
                        {supplier.contact_person && <span>{supplier.contact_person} • </span>}
                        {supplier.phone && <span>{supplier.phone}</span>}
                      </p>
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => { setEditingSupplier({...supplier}); setSuppliersListDialogOpen(false); }} className="h-8 w-8 p-0">
                        <Edit className="w-4 h-4 text-blue-600" />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleDeleteSupplier(supplier.id)} className="h-8 w-8 p-0">
                        <X className="w-4 h-4 text-red-600" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Add/Edit Supplier Dialog */}
      <Dialog open={supplierDialogOpen || editingSupplier !== null} onOpenChange={(open) => { setSupplierDialogOpen(open); if (!open) setEditingSupplier(null); }}>
        <DialogContent className="w-[95vw] max-w-md p-4" dir="rtl">
          <DialogHeader><DialogTitle className="text-center">{editingSupplier ? "تعديل المورد" : "إضافة مورد جديد"}</DialogTitle></DialogHeader>
          <div className="space-y-3 mt-2">
            <div>
              <Label className="text-sm">اسم المورد *</Label>
              <Input 
                placeholder="اسم الشركة أو المورد" 
                value={editingSupplier ? editingSupplier.name : newSupplier.name} 
                onChange={(e) => editingSupplier ? setEditingSupplier({...editingSupplier, name: e.target.value}) : setNewSupplier({...newSupplier, name: e.target.value})} 
                className="h-10 mt-1" 
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <Label className="text-sm">جهة الاتصال</Label>
                <Input 
                  placeholder="اسم الشخص" 
                  value={editingSupplier ? editingSupplier.contact_person : newSupplier.contact_person} 
                  onChange={(e) => editingSupplier ? setEditingSupplier({...editingSupplier, contact_person: e.target.value}) : setNewSupplier({...newSupplier, contact_person: e.target.value})} 
                  className="h-10 mt-1" 
                />
              </div>
              <div>
                <Label className="text-sm">رقم الهاتف</Label>
                <Input 
                  placeholder="05xxxxxxxx" 
                  value={editingSupplier ? editingSupplier.phone : newSupplier.phone} 
                  onChange={(e) => editingSupplier ? setEditingSupplier({...editingSupplier, phone: e.target.value}) : setNewSupplier({...newSupplier, phone: e.target.value})} 
                  className="h-10 mt-1" 
                />
              </div>
            </div>
            <div>
              <Label className="text-sm">البريد الإلكتروني</Label>
              <Input 
                type="email"
                placeholder="email@example.com" 
                value={editingSupplier ? editingSupplier.email : newSupplier.email} 
                onChange={(e) => editingSupplier ? setEditingSupplier({...editingSupplier, email: e.target.value}) : setNewSupplier({...newSupplier, email: e.target.value})} 
                className="h-10 mt-1" 
              />
            </div>
            <div>
              <Label className="text-sm">العنوان</Label>
              <Input 
                placeholder="المدينة - الحي" 
                value={editingSupplier ? editingSupplier.address : newSupplier.address} 
                onChange={(e) => editingSupplier ? setEditingSupplier({...editingSupplier, address: e.target.value}) : setNewSupplier({...newSupplier, address: e.target.value})} 
                className="h-10 mt-1" 
              />
            </div>
            <div>
              <Label className="text-sm">ملاحظات</Label>
              <Textarea 
                placeholder="ملاحظات إضافية..." 
                value={editingSupplier ? editingSupplier.notes : newSupplier.notes} 
                onChange={(e) => editingSupplier ? setEditingSupplier({...editingSupplier, notes: e.target.value}) : setNewSupplier({...newSupplier, notes: e.target.value})} 
                rows={2} 
                className="mt-1" 
              />
            </div>
            <Button 
              className="w-full h-11 bg-orange-600 hover:bg-orange-700" 
              onClick={editingSupplier ? handleUpdateSupplier : handleCreateSupplier}
            >
              {editingSupplier ? "تحديث المورد" : "إضافة المورد"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Report Dialog */}
      <Dialog open={reportDialogOpen} onOpenChange={setReportDialogOpen}>
        <DialogContent className="w-[95vw] max-w-sm p-4" dir="rtl">
          <DialogHeader><DialogTitle className="text-center">تقرير أوامر الشراء</DialogTitle></DialogHeader>
          <div className="space-y-4 mt-2">
            <p className="text-sm text-slate-600 text-center">اختر الفترة الزمنية للتقرير</p>
            <div>
              <Label className="text-sm">من تاريخ</Label>
              <Input type="date" value={reportStartDate} onChange={(e) => setReportStartDate(e.target.value)} className="h-10 mt-1" />
            </div>
            <div>
              <Label className="text-sm">إلى تاريخ</Label>
              <Input type="date" value={reportEndDate} onChange={(e) => setReportEndDate(e.target.value)} className="h-10 mt-1" />
            </div>
            <Button className="w-full h-11 bg-orange-600 hover:bg-orange-700" onClick={generateReport}>
              <Download className="w-4 h-4 ml-2" />تصدير التقرير PDF
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Budget Categories Dialog */}
      <Dialog open={budgetDialogOpen} onOpenChange={setBudgetDialogOpen}>
        <DialogContent className="w-[95vw] max-w-2xl max-h-[90vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>إدارة تصنيفات الميزانية</span>
              <Button size="sm" onClick={fetchBudgetReport} className="bg-blue-600 hover:bg-blue-700">
                <BarChart3 className="w-4 h-4 ml-1" /> تقرير الميزانية
              </Button>
            </DialogTitle>
          </DialogHeader>
          
          {/* Add New Category Form */}
          <div className="bg-slate-50 p-4 rounded-lg space-y-3">
            <h3 className="font-medium text-sm mb-2">إضافة تصنيف جديد</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">اسم التصنيف</Label>
                <Input 
                  placeholder="مثال: السباكة" 
                  value={newCategory.name}
                  onChange={(e) => setNewCategory({...newCategory, name: e.target.value})}
                  className="h-9 mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">المشروع</Label>
                <select 
                  value={newCategory.project_id}
                  onChange={(e) => setNewCategory({...newCategory, project_id: e.target.value})}
                  className="w-full h-9 mt-1 border rounded-lg bg-white px-2 text-sm"
                >
                  <option value="">اختر المشروع</option>
                  {projects.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <Label className="text-xs">الميزانية التقديرية (ر.س)</Label>
                <Input 
                  type="number"
                  placeholder="50000"
                  value={newCategory.estimated_budget}
                  onChange={(e) => setNewCategory({...newCategory, estimated_budget: e.target.value})}
                  className="h-9 mt-1"
                />
              </div>
            </div>
            <Button onClick={handleCreateCategory} className="w-full sm:w-auto bg-orange-600 hover:bg-orange-700">
              <Plus className="w-4 h-4 ml-1" /> إضافة التصنيف
            </Button>
          </div>

          {/* Categories List */}
          <div className="space-y-2 mt-4">
            <h3 className="font-medium text-sm">التصنيفات الحالية ({budgetCategories.length})</h3>
            {budgetCategories.length === 0 ? (
              <p className="text-center text-slate-500 py-4">لا توجد تصنيفات بعد</p>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {budgetCategories.map(cat => (
                  <div key={cat.id} className="bg-white border rounded-lg p-3">
                    {editingCategory?.id === cat.id ? (
                      <div className="space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                          <Input 
                            value={editingCategory.name}
                            onChange={(e) => setEditingCategory({...editingCategory, name: e.target.value})}
                            className="h-8"
                          />
                          <Input 
                            type="number"
                            value={editingCategory.estimated_budget}
                            onChange={(e) => setEditingCategory({...editingCategory, estimated_budget: e.target.value})}
                            className="h-8"
                          />
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" onClick={handleUpdateCategory} className="bg-green-600 hover:bg-green-700">حفظ</Button>
                          <Button size="sm" variant="outline" onClick={() => setEditingCategory(null)}>إلغاء</Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium">{cat.name}</p>
                          <p className="text-xs text-slate-500">{cat.project_name}</p>
                        </div>
                        <div className="text-left">
                          <p className="text-sm">
                            <span className="text-slate-500">التقديري: </span>
                            <span className="font-medium">{cat.estimated_budget?.toLocaleString('ar-SA')} ر.س</span>
                          </p>
                          <p className="text-sm">
                            <span className="text-slate-500">المصروف: </span>
                            <span className={`font-medium ${cat.actual_spent > cat.estimated_budget ? 'text-red-600' : 'text-green-600'}`}>
                              {cat.actual_spent?.toLocaleString('ar-SA')} ر.س
                            </span>
                          </p>
                          <p className="text-xs">
                            <span className="text-slate-500">المتبقي: </span>
                            <span className={cat.remaining < 0 ? 'text-red-600 font-bold' : 'text-blue-600'}>
                              {cat.remaining?.toLocaleString('ar-SA')} ر.س
                            </span>
                          </p>
                        </div>
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" onClick={() => setEditingCategory({...cat})} className="h-8 w-8 p-0">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => handleDeleteCategory(cat.id)} className="h-8 w-8 p-0 text-red-500 hover:text-red-700">
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

      {/* Budget Report Dialog */}
      <Dialog open={budgetReportDialogOpen} onOpenChange={setBudgetReportDialogOpen}>
        <DialogContent className="w-[95vw] max-w-3xl max-h-[90vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader>
            <DialogTitle>تقرير الميزانية - المقارنة بين التقديري والفعلي</DialogTitle>
          </DialogHeader>
          
          {budgetReport && (
            <div className="space-y-4">
              {/* Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Card className="border-r-4 border-blue-500">
                  <CardContent className="p-3">
                    <p className="text-xs text-slate-500">الميزانية التقديرية</p>
                    <p className="text-lg font-bold text-blue-600">{budgetReport.total_estimated?.toLocaleString('ar-SA')} ر.س</p>
                  </CardContent>
                </Card>
                <Card className="border-r-4 border-orange-500">
                  <CardContent className="p-3">
                    <p className="text-xs text-slate-500">المصروف الفعلي</p>
                    <p className="text-lg font-bold text-orange-600">{budgetReport.total_spent?.toLocaleString('ar-SA')} ر.س</p>
                  </CardContent>
                </Card>
                <Card className={`border-r-4 ${budgetReport.total_remaining >= 0 ? 'border-green-500' : 'border-red-500'}`}>
                  <CardContent className="p-3">
                    <p className="text-xs text-slate-500">المتبقي</p>
                    <p className={`text-lg font-bold ${budgetReport.total_remaining >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {budgetReport.total_remaining?.toLocaleString('ar-SA')} ر.س
                    </p>
                  </CardContent>
                </Card>
                <Card className={`border-r-4 ${budgetReport.overall_variance_percentage <= 0 ? 'border-green-500' : 'border-red-500'}`}>
                  <CardContent className="p-3">
                    <p className="text-xs text-slate-500">نسبة الاستهلاك</p>
                    <p className={`text-lg font-bold ${budgetReport.overall_variance_percentage <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {budgetReport.total_estimated > 0 
                        ? Math.round((budgetReport.total_spent / budgetReport.total_estimated) * 100) 
                        : 0}%
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Over Budget Alert */}
              {budgetReport.over_budget?.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <h3 className="font-medium text-red-700 flex items-center gap-2">
                    <AlertCircle className="w-5 h-5" />
                    تصنيفات تجاوزت الميزانية ({budgetReport.over_budget.length})
                  </h3>
                  <div className="mt-2 space-y-1">
                    {budgetReport.over_budget.map(cat => (
                      <div key={cat.id} className="flex justify-between text-sm">
                        <span>{cat.name} - {cat.project_name}</span>
                        <span className="text-red-600 font-medium">تجاوز: {Math.abs(cat.remaining)?.toLocaleString('ar-SA')} ر.س</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Categories Table */}
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-right">التصنيف</TableHead>
                      <TableHead className="text-right">المشروع</TableHead>
                      <TableHead className="text-center">التقديري</TableHead>
                      <TableHead className="text-center">الفعلي</TableHead>
                      <TableHead className="text-center">المتبقي</TableHead>
                      <TableHead className="text-center">الحالة</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {budgetReport.categories?.map(cat => (
                      <TableRow key={cat.id}>
                        <TableCell className="font-medium">{cat.name}</TableCell>
                        <TableCell className="text-sm text-slate-600">{cat.project_name}</TableCell>
                        <TableCell className="text-center">{cat.estimated_budget?.toLocaleString('ar-SA')}</TableCell>
                        <TableCell className="text-center">{cat.actual_spent?.toLocaleString('ar-SA')}</TableCell>
                        <TableCell className={`text-center font-medium ${cat.remaining < 0 ? 'text-red-600' : 'text-green-600'}`}>
                          {cat.remaining?.toLocaleString('ar-SA')}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge className={cat.status === 'over_budget' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}>
                            {cat.status === 'over_budget' ? 'تجاوز' : 'ضمن الميزانية'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProcurementDashboard;
