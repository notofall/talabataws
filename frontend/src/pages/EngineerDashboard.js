import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Package, LogOut, Clock, CheckCircle, XCircle, RefreshCw, FileText, Check, X, Eye, Download, KeyRound, Loader2, Send } from "lucide-react";
import { exportRequestToPDF, exportRequestsTableToPDF, fetchAndCacheCompanySettings } from "../utils/pdfExport";
import ChangePasswordDialog from "../components/ChangePasswordDialog";

const EngineerDashboard = () => {
  const { user, logout, getAuthHeaders, API_URL } = useAuth();
  const [requests, setRequests] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  
  // Filter and pagination state
  const [filterMode, setFilterMode] = useState("pending"); // pending, approved, rejected, ordered, all
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;

  const fetchData = async () => {
    try {
      // Using PostgreSQL APIs
      const requestsRes = await axios.get(`${API_URL}/requests`, getAuthHeaders());
      setRequests(requestsRes.data);
      // Calculate stats from data
      setStats({
        total: requestsRes.data.length,
        pending: requestsRes.data.filter(r => r.status === 'pending_engineer').length,
        approved: requestsRes.data.filter(r => r.status === 'approved_by_engineer').length
      });
    } catch (error) {
      console.error("Error fetching data:", error);
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
  
  // Reset page when filter changes
  useEffect(() => { setCurrentPage(1); }, [filterMode]);
  
  // Filter counts
  const filterCounts = {
    all: requests.length,
    pending: requests.filter(r => r.status === "pending_engineer").length,
    approved: requests.filter(r => r.status === "approved_by_engineer" || r.status === "partially_ordered").length,
    rejected: requests.filter(r => r.status === "rejected_by_engineer").length,
    rejected_by_manager: requests.filter(r => r.status === "rejected_by_manager").length,
    ordered: requests.filter(r => r.status === "purchase_order_issued").length,
  };
  
  // Get filtered requests
  const getFilteredRequests = () => {
    switch (filterMode) {
      case "pending": return requests.filter(r => r.status === "pending_engineer");
      case "approved": return requests.filter(r => r.status === "approved_by_engineer" || r.status === "partially_ordered");
      case "rejected": return requests.filter(r => r.status === "rejected_by_engineer");
      case "rejected_by_manager": return requests.filter(r => r.status === "rejected_by_manager");
      case "ordered": return requests.filter(r => r.status === "purchase_order_issued");
      default: return requests;
    }
  };
  
  const filteredRequests = getFilteredRequests();
  const totalPages = Math.ceil(filteredRequests.length / ITEMS_PER_PAGE);
  const paginatedRequests = filteredRequests.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  const handleApprove = async (requestId) => {
    setActionLoading(true);
    try {
      await axios.post(`${API_URL}/requests/${requestId}/approve`, {}, getAuthHeaders());
      toast.success("تم اعتماد الطلب بنجاح");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في اعتماد الطلب");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) { toast.error("الرجاء إدخال سبب الرفض"); return; }
    setActionLoading(true);
    try {
      await axios.post(`${API_URL}/requests/${selectedRequest.id}/reject`, { reason: rejectionReason }, getAuthHeaders());
      toast.success("تم رفض الطلب");
      setRejectDialogOpen(false);
      setRejectionReason("");
      setSelectedRequest(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في رفض الطلب");
    } finally {
      setActionLoading(false);
    }
  };

  // إعادة إرسال الطلب المرفوض من مدير المشتريات
  const handleResubmit = async (requestId) => {
    if (!window.confirm("هل تريد إعادة إرسال هذا الطلب؟")) return;
    
    setActionLoading(true);
    try {
      await axios.post(`${API_URL}/requests/${requestId}/resubmit`, {}, getAuthHeaders());
      toast.success("تم إعادة إرسال الطلب بنجاح");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في إعادة إرسال الطلب");
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const map = {
      pending_engineer: { label: "معلق", color: "bg-yellow-100 text-yellow-800 border-yellow-300" },
      approved_by_engineer: { label: "معتمد", color: "bg-green-100 text-green-800 border-green-300" },
      rejected_by_engineer: { label: "مرفوض", color: "bg-red-100 text-red-800 border-red-300" },
      rejected_by_manager: { label: "مرفوض من المشتريات", color: "bg-orange-100 text-orange-800 border-orange-300" },
      purchase_order_issued: { label: "تم الإصدار", color: "bg-blue-100 text-blue-800 border-blue-300" },
    };
    const info = map[status] || { label: status, color: "bg-slate-100 text-slate-800" };
    return <Badge className={`${info.color} border text-xs`}>{info.label}</Badge>;
  };

  const formatDate = (dateString) => new Date(dateString).toLocaleDateString("ar-SA", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const getItemsSummary = (items) => !items?.length ? "-" : items.length === 1 ? items[0].name : `${items[0].name} +${items.length - 1}`;

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-slate-50"><div className="w-10 h-10 border-4 border-orange-600 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-slate-900 text-white shadow-lg sticky top-0 z-40 pwa-header">
        <div className="max-w-7xl mx-auto px-3 sm:px-6">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-orange-600 rounded flex items-center justify-center">
                <Package className="w-5 h-5" />
              </div>
              <div className="hidden sm:block">
                <h1 className="text-sm font-bold">نظام طلبات المواد</h1>
                <p className="text-xs text-slate-400">لوحة تحكم المهندس</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={handleRefresh} disabled={refreshing} className="text-slate-300 hover:text-white h-8 px-2">
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setPasswordDialogOpen(true)} className="text-slate-300 hover:text-white h-8 px-2">
                <KeyRound className="w-4 h-4" />
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
          <Card className="border-r-4 border-orange-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">الإجمالي</p>
              <p className="text-2xl font-bold">{filterCounts.all}</p>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-yellow-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">بانتظار الاعتماد</p>
              <p className="text-2xl font-bold text-yellow-600">{filterCounts.pending}</p>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-green-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">معتمدة</p>
              <p className="text-2xl font-bold text-green-600">{filterCounts.approved}</p>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-blue-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">تم الإصدار</p>
              <p className="text-2xl font-bold text-blue-600">{filterCounts.ordered}</p>
            </CardContent>
          </Card>
        </div>

        {/* Requests Section */}
        <div className="mb-4">
          <div className="flex flex-col gap-3 mb-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold flex items-center gap-2">
                <FileText className="w-5 h-5 text-slate-700" />
                الطلبات
                {refreshing && <Loader2 className="w-4 h-4 animate-spin text-orange-500" />}
              </h2>
              <Button variant="outline" size="sm" onClick={() => exportRequestsTableToPDF(filteredRequests, 'طلبات المهندس')} disabled={!filteredRequests.length} className="h-8 text-xs">
                <Download className="w-3 h-3 ml-1" />تصدير
              </Button>
            </div>
            
            {/* Filter Buttons */}
            <div className="flex flex-wrap gap-2">
              <Button 
                size="sm" 
                variant={filterMode === "pending" ? "default" : "outline"}
                onClick={() => setFilterMode("pending")}
                className={`h-8 text-xs ${filterMode === "pending" ? "bg-yellow-600 hover:bg-yellow-700" : "text-yellow-700 border-yellow-300 hover:bg-yellow-50"}`}
              >
                بانتظار الاعتماد
                <Badge className="mr-1 bg-yellow-500 text-white text-xs">{filterCounts.pending}</Badge>
              </Button>
              <Button 
                size="sm" 
                variant={filterMode === "approved" ? "default" : "outline"}
                onClick={() => setFilterMode("approved")}
                className={`h-8 text-xs ${filterMode === "approved" ? "bg-green-600 hover:bg-green-700" : "text-green-700 border-green-300 hover:bg-green-50"}`}
              >
                معتمدة
                <Badge className="mr-1 bg-green-500 text-white text-xs">{filterCounts.approved}</Badge>
              </Button>
              <Button 
                size="sm" 
                variant={filterMode === "rejected" ? "default" : "outline"}
                onClick={() => setFilterMode("rejected")}
                className={`h-8 text-xs ${filterMode === "rejected" ? "bg-red-600 hover:bg-red-700" : "text-red-700 border-red-300 hover:bg-red-50"}`}
              >
                مرفوضة
                <Badge className="mr-1 bg-red-500 text-white text-xs">{filterCounts.rejected}</Badge>
              </Button>
              {filterCounts.rejected_by_manager > 0 && (
                <Button 
                  size="sm" 
                  variant={filterMode === "rejected_by_manager" ? "default" : "outline"}
                  onClick={() => setFilterMode("rejected_by_manager")}
                  className={`h-8 text-xs ${filterMode === "rejected_by_manager" ? "bg-orange-600 hover:bg-orange-700" : "text-orange-700 border-orange-300 hover:bg-orange-50"}`}
                >
                  تحتاج تعديل
                  <Badge className="mr-1 bg-orange-500 text-white text-xs">{filterCounts.rejected_by_manager}</Badge>
                </Button>
              )}
              <Button 
                size="sm" 
                variant={filterMode === "ordered" ? "default" : "outline"}
                onClick={() => setFilterMode("ordered")}
                className={`h-8 text-xs ${filterMode === "ordered" ? "bg-blue-600 hover:bg-blue-700" : "text-blue-700 border-blue-300 hover:bg-blue-50"}`}
              >
                تم الإصدار
                <Badge className="mr-1 bg-blue-500 text-white text-xs">{filterCounts.ordered}</Badge>
              </Button>
              <Button 
                size="sm" 
                variant={filterMode === "all" ? "default" : "outline"}
                onClick={() => setFilterMode("all")}
                className={`h-8 text-xs ${filterMode === "all" ? "bg-slate-600 hover:bg-slate-700" : "text-slate-700 border-slate-300 hover:bg-slate-50"}`}
              >
                الكل
                <Badge className="mr-1 bg-slate-500 text-white text-xs">{filterCounts.all}</Badge>
              </Button>
            </div>
          </div>

          <Card className="shadow-sm">
            <CardContent className="p-0">
              {!paginatedRequests.length ? (
                <div className="text-center py-8">
                  <Package className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                  <p className="text-slate-500 text-sm">{filterMode === "all" ? "لا توجد طلبات" : "لا توجد طلبات في هذا التصنيف"}</p>
                </div>
              ) : (
                <>
                  {/* Mobile */}
                  <div className="sm:hidden divide-y">
                    {paginatedRequests.map((req) => (
                      <div key={req.id} className="p-3 space-y-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-bold text-blue-600">طلب #{req.request_number || '-'}</p>
                            <p className="font-medium text-sm">{getItemsSummary(req.items)}</p>
                            <p className="text-xs text-slate-500">{req.project_name} • {req.supervisor_name}</p>
                          </div>
                          {getStatusBadge(req.status)}
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-xs text-slate-400">{formatDate(req.created_at)}</span>
                          <div className="flex gap-1">
                            <Button size="sm" variant="ghost" onClick={() => { setSelectedRequest(req); setViewDialogOpen(true); }} className="h-7 w-7 p-0"><Eye className="w-3 h-3" /></Button>
                            {req.status === "pending_engineer" && (
                              <>
                                <Button size="sm" className="bg-green-600 h-7 text-xs px-2" onClick={() => handleApprove(req.id)} disabled={actionLoading}>
                                  <Check className="w-3 h-3 ml-1" />اعتماد
                                </Button>
                                <Button size="sm" variant="destructive" className="h-7 text-xs px-2" onClick={() => { setSelectedRequest(req); setRejectDialogOpen(true); }} disabled={actionLoading}>
                                  <X className="w-3 h-3 ml-1" />رفض
                                </Button>
                              </>
                            )}
                            {req.status === "rejected_by_manager" && (
                              <Button size="sm" className="bg-orange-600 h-7 text-xs px-2" onClick={() => handleResubmit(req.id)} disabled={actionLoading}>
                                <Send className="w-3 h-3 ml-1" />إعادة إرسال
                              </Button>
                            )}
                            <Button size="sm" variant="ghost" onClick={() => exportRequestToPDF(req)} className="h-7 w-7 p-0"><Download className="w-3 h-3 text-green-600" /></Button>
                          </div>
                        </div>
                        {req.status === "rejected_by_manager" && req.manager_rejection_reason && (
                          <div className="bg-orange-50 border border-orange-200 rounded p-2 text-xs text-orange-700">
                            <strong>سبب الرفض:</strong> {req.manager_rejection_reason}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  {/* Desktop */}
                  <div className="hidden sm:block overflow-x-auto">
                    <Table>
                      <TableHeader><TableRow className="bg-slate-50">
                        <TableHead className="text-right">رقم الطلب</TableHead>
                        <TableHead className="text-right">الأصناف</TableHead>
                        <TableHead className="text-right">المشروع</TableHead>
                        <TableHead className="text-right">المشرف</TableHead>
                        <TableHead className="text-right">الحالة</TableHead>
                        <TableHead className="text-right">التاريخ</TableHead>
                        <TableHead className="text-right">الإجراءات</TableHead>
                      </TableRow></TableHeader>
                      <TableBody>
                        {paginatedRequests.map((req) => (
                          <TableRow key={req.id}>
                            <TableCell className="font-bold text-blue-600">{req.request_number || '-'}</TableCell>
                            <TableCell className="font-medium">{getItemsSummary(req.items)}</TableCell>
                            <TableCell>{req.project_name}</TableCell>
                            <TableCell>{req.supervisor_name}</TableCell>
                            <TableCell>{getStatusBadge(req.status)}</TableCell>
                            <TableCell className="text-sm text-slate-500">{formatDate(req.created_at)}</TableCell>
                            <TableCell>
                              <div className="flex gap-1 flex-wrap">
                                <Button size="sm" variant="ghost" onClick={() => { setSelectedRequest(req); setViewDialogOpen(true); }} className="h-8 w-8 p-0"><Eye className="w-4 h-4" /></Button>
                                {req.status === "pending_engineer" && (
                                  <>
                                    <Button size="sm" className="bg-green-600 hover:bg-green-700" onClick={() => handleApprove(req.id)} disabled={actionLoading}><Check className="w-4 h-4 ml-1" />اعتماد</Button>
                                    <Button size="sm" variant="destructive" onClick={() => { setSelectedRequest(req); setRejectDialogOpen(true); }} disabled={actionLoading}><X className="w-4 h-4 ml-1" />رفض</Button>
                                  </>
                                )}
                                {req.status === "rejected_by_manager" && (
                                  <Button size="sm" className="bg-orange-600 hover:bg-orange-700" onClick={() => handleResubmit(req.id)} disabled={actionLoading}>
                                    <Send className="w-4 h-4 ml-1" />إعادة إرسال
                                  </Button>
                                )}
                                <Button size="sm" variant="ghost" onClick={() => exportRequestToPDF(req)} className="h-8 w-8 p-0"><Download className="w-4 h-4 text-green-600" /></Button>
                              </div>
                              {req.status === "rejected_by_manager" && req.manager_rejection_reason && (
                                <div className="mt-1 text-xs text-orange-600 max-w-xs truncate" title={req.manager_rejection_reason}>
                                  سبب الرفض: {req.manager_rejection_reason}
                                </div>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  
                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between p-3 border-t bg-slate-50">
                      <span className="text-xs text-slate-500">
                        عرض {(currentPage - 1) * ITEMS_PER_PAGE + 1}-{Math.min(currentPage * ITEMS_PER_PAGE, filteredRequests.length)} من {filteredRequests.length}
                      </span>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                          disabled={currentPage === 1}
                          className="h-7 px-2 text-xs"
                        >
                          السابق
                        </Button>
                        <span className="flex items-center px-2 text-xs text-slate-600">
                          {currentPage} / {totalPages}
                        </span>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                          disabled={currentPage === totalPages}
                          className="h-7 px-2 text-xs"
                        >
                          التالي
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </main>

      {/* View Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
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
              <div><span className="text-slate-500 text-sm">السبب:</span><p className="text-sm">{selectedRequest.reason}</p></div>
              {selectedRequest.rejection_reason && (
                <div className="bg-red-50 p-2 rounded text-sm">
                  <span className="text-red-600">سبب الرفض:</span>
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

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onOpenChange={setRejectDialogOpen}>
        <DialogContent className="w-[95vw] max-w-sm p-4" dir="rtl">
          <DialogHeader><DialogTitle className="text-center">رفض الطلب</DialogTitle></DialogHeader>
          <div className="space-y-4 mt-2">
            <p className="text-sm text-slate-600">هل أنت متأكد من رفض هذا الطلب؟</p>
            <Textarea placeholder="اذكر سبب الرفض..." value={rejectionReason} onChange={(e) => setRejectionReason(e.target.value)} rows={3} />
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => { setRejectDialogOpen(false); setRejectionReason(""); }}>إلغاء</Button>
              <Button variant="destructive" className="flex-1" onClick={handleReject} disabled={actionLoading}>{actionLoading ? "جاري..." : "تأكيد الرفض"}</Button>
            </div>
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

export default EngineerDashboard;
