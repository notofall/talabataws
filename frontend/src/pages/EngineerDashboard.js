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
import { Package, LogOut, Clock, CheckCircle, XCircle, RefreshCw, FileText, Check, X, Eye, Download } from "lucide-react";
import { exportRequestToPDF, exportRequestsTableToPDF } from "../utils/pdfExport";

const EngineerDashboard = () => {
  const { user, logout, getAuthHeaders, API_URL } = useAuth();
  const [requests, setRequests] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const fetchData = async () => {
    try {
      const [requestsRes, statsRes] = await Promise.all([
        axios.get(`${API_URL}/requests`, getAuthHeaders()),
        axios.get(`${API_URL}/dashboard/stats`, getAuthHeaders()),
      ]);
      setRequests(requestsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error("فشل في تحميل البيانات");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleApprove = async (requestId) => {
    setActionLoading(true);
    try {
      await axios.put(`${API_URL}/requests/${requestId}/approve`, {}, getAuthHeaders());
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
      await axios.put(`${API_URL}/requests/${selectedRequest.id}/reject`, { reason: rejectionReason }, getAuthHeaders());
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

  const getStatusBadge = (status) => {
    const map = {
      pending_engineer: { label: "معلق", color: "bg-yellow-100 text-yellow-800 border-yellow-300" },
      approved_by_engineer: { label: "معتمد", color: "bg-green-100 text-green-800 border-green-300" },
      rejected_by_engineer: { label: "مرفوض", color: "bg-red-100 text-red-800 border-red-300" },
      purchase_order_issued: { label: "تم الإصدار", color: "bg-blue-100 text-blue-800 border-blue-300" },
    };
    const info = map[status] || { label: status, color: "bg-slate-100 text-slate-800" };
    return <Badge className={`${info.color} border text-xs`}>{info.label}</Badge>;
  };

  const formatDate = (dateString) => new Date(dateString).toLocaleDateString("ar-SA", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const getItemsSummary = (items) => !items?.length ? "-" : items.length === 1 ? items[0].name : `${items[0].name} +${items.length - 1}`;

  const pendingRequests = requests.filter((r) => r.status === "pending_engineer");
  const processedRequests = requests.filter((r) => r.status !== "pending_engineer");

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
                <p className="text-xs text-slate-400">لوحة تحكم المهندس</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
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
        <div className="grid grid-cols-3 gap-3 mb-4">
          <Card className="border-r-4 border-orange-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">الإجمالي</p>
              <p className="text-2xl font-bold">{stats.total || 0}</p>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-yellow-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">معلقة</p>
              <p className="text-2xl font-bold text-yellow-600">{stats.pending || 0}</p>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-green-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">معتمدة</p>
              <p className="text-2xl font-bold text-green-600">{stats.approved || 0}</p>
            </CardContent>
          </Card>
        </div>

        {/* Pending Requests */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <Clock className="w-5 h-5 text-yellow-600" />
              طلبات تحتاج اعتمادك
              {pendingRequests.length > 0 && <Badge className="bg-yellow-500 text-white">{pendingRequests.length}</Badge>}
            </h2>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => exportRequestsTableToPDF(requests, 'طلبات المهندس').catch(() => {})} disabled={!requests.length} className="h-8 text-xs">
                <Download className="w-3 h-3" />
              </Button>
              <Button variant="outline" size="sm" onClick={fetchData} className="h-8"><RefreshCw className="w-3 h-3" /></Button>
            </div>
          </div>

          <Card className="shadow-sm">
            <CardContent className="p-0">
              {!pendingRequests.length ? (
                <div className="text-center py-8"><CheckCircle className="w-10 h-10 text-green-300 mx-auto mb-2" /><p className="text-slate-500 text-sm">لا توجد طلبات معلقة</p></div>
              ) : (
                <>
                  {/* Mobile */}
                  <div className="sm:hidden divide-y">
                    {pendingRequests.map((req) => (
                      <div key={req.id} className="p-3 space-y-2">
                        <div>
                          <p className="font-medium text-sm">{getItemsSummary(req.items)}</p>
                          <p className="text-xs text-slate-500">{req.project_name} • {req.supervisor_name}</p>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-xs text-slate-400">{formatDate(req.created_at)}</span>
                          <div className="flex gap-1">
                            <Button size="sm" variant="ghost" onClick={() => { setSelectedRequest(req); setViewDialogOpen(true); }} className="h-7 w-7 p-0"><Eye className="w-3 h-3" /></Button>
                            <Button size="sm" className="bg-green-600 h-7 text-xs px-2" onClick={() => handleApprove(req.id)} disabled={actionLoading}>
                              <Check className="w-3 h-3 ml-1" />اعتماد
                            </Button>
                            <Button size="sm" variant="destructive" className="h-7 text-xs px-2" onClick={() => { setSelectedRequest(req); setRejectDialogOpen(true); }} disabled={actionLoading}>
                              <X className="w-3 h-3 ml-1" />رفض
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
                        <TableHead className="text-right">التاريخ</TableHead>
                        <TableHead className="text-right">الإجراءات</TableHead>
                      </TableRow></TableHeader>
                      <TableBody>
                        {pendingRequests.map((req) => (
                          <TableRow key={req.id}>
                            <TableCell className="font-medium">{getItemsSummary(req.items)}</TableCell>
                            <TableCell>{req.project_name}</TableCell>
                            <TableCell>{req.supervisor_name}</TableCell>
                            <TableCell className="text-sm text-slate-500">{formatDate(req.created_at)}</TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                <Button size="sm" variant="ghost" onClick={() => { setSelectedRequest(req); setViewDialogOpen(true); }} className="h-8 w-8 p-0"><Eye className="w-4 h-4" /></Button>
                                <Button size="sm" className="bg-green-600 hover:bg-green-700" onClick={() => handleApprove(req.id)} disabled={actionLoading}><Check className="w-4 h-4 ml-1" />اعتماد</Button>
                                <Button size="sm" variant="destructive" onClick={() => { setSelectedRequest(req); setRejectDialogOpen(true); }} disabled={actionLoading}><X className="w-4 h-4 ml-1" />رفض</Button>
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

        {/* Processed Requests */}
        <div>
          <h2 className="text-lg font-bold mb-3">الطلبات السابقة</h2>
          <Card className="shadow-sm">
            <CardContent className="p-0">
              {!processedRequests.length ? (
                <div className="text-center py-8"><FileText className="w-10 h-10 text-slate-300 mx-auto mb-2" /><p className="text-slate-500 text-sm">لا توجد طلبات</p></div>
              ) : (
                <>
                  {/* Mobile */}
                  <div className="sm:hidden divide-y">
                    {processedRequests.map((req) => (
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
                            <Button size="sm" variant="ghost" onClick={() => exportRequestToPDF(req).catch(() => {})} className="h-7 w-7 p-0"><Download className="w-3 h-3 text-green-600" /></Button>
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
                        <TableHead className="text-right">الإجراءات</TableHead>
                      </TableRow></TableHeader>
                      <TableBody>
                        {processedRequests.map((req) => (
                          <TableRow key={req.id}>
                            <TableCell className="font-medium">{getItemsSummary(req.items)}</TableCell>
                            <TableCell>{req.project_name}</TableCell>
                            <TableCell>{req.supervisor_name}</TableCell>
                            <TableCell>{getStatusBadge(req.status)}</TableCell>
                            <TableCell className="text-sm text-slate-500">{formatDate(req.created_at)}</TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                <Button size="sm" variant="ghost" onClick={() => { setSelectedRequest(req); setViewDialogOpen(true); }} className="h-8 w-8 p-0"><Eye className="w-4 h-4" /></Button>
                                <Button size="sm" variant="ghost" onClick={() => exportRequestToPDF(req).catch(() => {})} className="h-8 w-8 p-0"><Download className="w-4 h-4 text-green-600" /></Button>
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
              <Button className="w-full bg-green-600 hover:bg-green-700" onClick={() => exportRequestToPDF(selectedRequest).catch(() => {})}>
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
    </div>
  );
};

export default EngineerDashboard;
