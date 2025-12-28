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
import { Package, Plus, LogOut, FileText, Clock, CheckCircle, XCircle, RefreshCw, Download, Eye, Edit, Trash2, X } from "lucide-react";
import { exportRequestToPDF, exportRequestsTableToPDF } from "../utils/pdfExport";

const UNITS = ["قطعة", "طن", "كيلو", "متر", "متر مربع", "متر مكعب", "كيس", "لتر", "علبة", "رول"];

const SupervisorDashboard = () => {
  const { user, logout, getAuthHeaders, API_URL } = useAuth();
  const [requests, setRequests] = useState([]);
  const [engineers, setEngineers] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [items, setItems] = useState([]);
  const [newItemName, setNewItemName] = useState("");
  const [newItemQty, setNewItemQty] = useState("");
  const [newItemUnit, setNewItemUnit] = useState("قطعة");
  const [projectName, setProjectName] = useState("");
  const [reason, setReason] = useState("");
  const [engineerId, setEngineerId] = useState("");

  // Edit form state
  const [editItems, setEditItems] = useState([]);
  const [editNewItemName, setEditNewItemName] = useState("");
  const [editNewItemQty, setEditNewItemQty] = useState("");
  const [editNewItemUnit, setEditNewItemUnit] = useState("قطعة");
  const [editProjectName, setEditProjectName] = useState("");
  const [editReason, setEditReason] = useState("");
  const [editEngineerId, setEditEngineerId] = useState("");

  const fetchData = async () => {
    try {
      const [requestsRes, engineersRes, statsRes] = await Promise.all([
        axios.get(`${API_URL}/requests`, getAuthHeaders()),
        axios.get(`${API_URL}/users/engineers`, getAuthHeaders()),
        axios.get(`${API_URL}/dashboard/stats`, getAuthHeaders()),
      ]);
      setRequests(requestsRes.data);
      setEngineers(engineersRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error("فشل في تحميل البيانات");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  // Add item to list
  const addItem = () => {
    if (!newItemName.trim()) { toast.error("أدخل اسم المادة"); return; }
    if (!newItemQty || parseInt(newItemQty) <= 0) { toast.error("أدخل الكمية"); return; }
    
    setItems([...items, { name: newItemName.trim(), quantity: newItemQty, unit: newItemUnit }]);
    setNewItemName("");
    setNewItemQty("");
    setNewItemUnit("قطعة");
    toast.success("تم إضافة الصنف");
  };

  const removeItem = (index) => setItems(items.filter((_, i) => i !== index));

  // Edit item functions
  const addEditItem = () => {
    if (!editNewItemName.trim()) { toast.error("أدخل اسم المادة"); return; }
    if (!editNewItemQty || parseInt(editNewItemQty) <= 0) { toast.error("أدخل الكمية"); return; }
    
    setEditItems([...editItems, { name: editNewItemName.trim(), quantity: editNewItemQty, unit: editNewItemUnit }]);
    setEditNewItemName("");
    setEditNewItemQty("");
    setEditNewItemUnit("قطعة");
  };

  const removeEditItem = (index) => setEditItems(editItems.filter((_, i) => i !== index));

  const resetForm = () => {
    setItems([]);
    setNewItemName("");
    setNewItemQty("");
    setNewItemUnit("قطعة");
    setProjectName("");
    setReason("");
    setEngineerId("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (items.length === 0) { toast.error("الرجاء إضافة صنف واحد على الأقل"); return; }
    if (!projectName || !reason || !engineerId) { toast.error("الرجاء إكمال جميع الحقول"); return; }

    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/requests`, {
        items: items.map(item => ({ name: item.name, quantity: parseInt(item.quantity), unit: item.unit })),
        project_name: projectName, reason, engineer_id: engineerId,
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
    if (!editProjectName || !editReason || !editEngineerId) { toast.error("الرجاء إكمال جميع الحقول"); return; }

    setSubmitting(true);
    try {
      await axios.put(`${API_URL}/requests/${selectedRequest.id}/edit`, {
        items: editItems.map(item => ({ name: item.name, quantity: parseInt(item.quantity), unit: item.unit || "قطعة" })),
        project_name: editProjectName, reason: editReason, engineer_id: editEngineerId,
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
    setEditProjectName(request.project_name);
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
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          {[
            { label: "الإجمالي", value: stats.total || 0, color: "border-orange-500" },
            { label: "معلقة", value: stats.pending || 0, color: "border-yellow-500" },
            { label: "معتمدة", value: stats.approved || 0, color: "border-green-500" },
            { label: "مرفوضة", value: stats.rejected || 0, color: "border-red-500" },
          ].map((stat, i) => (
            <Card key={i} className={`border-r-4 ${stat.color}`}>
              <CardContent className="p-3">
                <p className="text-xs text-slate-500">{stat.label}</p>
                <p className="text-2xl font-bold">{stat.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>

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
                    <Label className="text-sm font-medium">اسم المشروع</Label>
                    <Input placeholder="مثال: مشروع برج الرياض" value={projectName} onChange={(e) => setProjectName(e.target.value)} className="h-11 mt-1" />
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
              <Label className="text-sm font-medium">اسم المشروع</Label>
              <Input value={editProjectName} onChange={(e) => setEditProjectName(e.target.value)} className="h-11 mt-1" />
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
    </div>
  );
};

export default SupervisorDashboard;
