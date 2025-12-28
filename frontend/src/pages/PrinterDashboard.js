import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Card, CardContent } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Package, LogOut, RefreshCw, Printer, Eye, Download, CheckCircle, Clock } from "lucide-react";
import { exportPurchaseOrderToPDF } from "../utils/pdfExport";

const PrinterDashboard = () => {
  const { user, logout, getAuthHeaders, API_URL } = useAuth();
  const [orders, setOrders] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [printing, setPrinting] = useState(false);

  const fetchData = async () => {
    try {
      const [ordersRes, statsRes] = await Promise.all([
        axios.get(`${API_URL}/purchase-orders`, getAuthHeaders()),
        axios.get(`${API_URL}/dashboard/stats`, getAuthHeaders()),
      ]);
      setOrders(ordersRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error("فشل في تحميل البيانات");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handlePrint = async (order) => {
    setPrinting(true);
    try {
      // First export PDF
      exportPurchaseOrderToPDF(order);
      
      // Mark as printed
      await axios.put(`${API_URL}/purchase-orders/${order.id}/print`, {}, getAuthHeaders());
      toast.success("تم تسجيل طباعة أمر الشراء");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تسجيل الطباعة");
    } finally {
      setPrinting(false);
    }
  };

  const formatDate = (dateString) => new Date(dateString).toLocaleDateString("ar-SA", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  const getItemsSummary = (items) => !items?.length ? "-" : items.length === 1 ? items[0].name : `${items[0].name} +${items.length - 1}`;

  const getStatusBadge = (status) => {
    const map = {
      approved: { label: "جاهز للطباعة", color: "bg-yellow-100 text-yellow-800 border-yellow-300" },
      printed: { label: "تمت الطباعة", color: "bg-green-100 text-green-800 border-green-300" },
    };
    const info = map[status] || { label: status, color: "bg-slate-100 text-slate-800" };
    return <Badge className={`${info.color} border text-xs`}>{info.label}</Badge>;
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-slate-50"><div className="w-10 h-10 border-4 border-orange-600 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  const pendingOrders = orders.filter(o => o.status === "approved");
  const printedOrders = orders.filter(o => o.status === "printed");

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-slate-900 text-white shadow-lg sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-3 sm:px-6">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-orange-600 rounded flex items-center justify-center">
                <Printer className="w-5 h-5" />
              </div>
              <div className="hidden sm:block">
                <h1 className="text-sm font-bold">نظام طلبات المواد</h1>
                <p className="text-xs text-slate-400">موظف الطباعة</p>
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
        <div className="grid grid-cols-2 gap-3 mb-4">
          <Card className="border-r-4 border-yellow-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">بانتظار الطباعة</p>
              <p className="text-2xl font-bold text-yellow-600">{stats.pending_print || 0}</p>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-green-500">
            <CardContent className="p-3">
              <p className="text-xs text-slate-500">تمت طباعتها</p>
              <p className="text-2xl font-bold text-green-600">{stats.printed || 0}</p>
            </CardContent>
          </Card>
        </div>

        {/* Pending Orders */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <Clock className="w-5 h-5 text-yellow-600" />
              أوامر بانتظار الطباعة
              {pendingOrders.length > 0 && <Badge className="bg-yellow-500 text-white">{pendingOrders.length}</Badge>}
            </h2>
            <Button variant="outline" size="sm" onClick={fetchData} className="h-8"><RefreshCw className="w-3 h-3" /></Button>
          </div>

          <Card className="shadow-sm">
            <CardContent className="p-0">
              {!pendingOrders.length ? (
                <div className="text-center py-8"><CheckCircle className="w-10 h-10 text-green-300 mx-auto mb-2" /><p className="text-slate-500 text-sm">لا توجد أوامر بانتظار الطباعة</p></div>
              ) : (
                <>
                  {/* Mobile */}
                  <div className="sm:hidden divide-y">
                    {pendingOrders.map((order) => (
                      <div key={order.id} className="p-3 space-y-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium text-sm">{getItemsSummary(order.items)}</p>
                            <p className="text-xs text-slate-500">{order.project_name}</p>
                          </div>
                          <Badge className="bg-green-100 text-green-800 border-green-300 border text-xs">{order.supplier_name}</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-xs text-slate-400">{formatDate(order.created_at)}</span>
                          <div className="flex gap-1">
                            <Button size="sm" variant="ghost" onClick={() => { setSelectedOrder(order); setViewDialogOpen(true); }} className="h-7 w-7 p-0"><Eye className="w-3 h-3" /></Button>
                            <Button size="sm" className="bg-orange-600 h-7 text-xs px-2" onClick={() => handlePrint(order)} disabled={printing}>
                              <Printer className="w-3 h-3 ml-1" />طباعة
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
                        <TableHead className="text-right">المورد</TableHead>
                        <TableHead className="text-right">التاريخ</TableHead>
                        <TableHead className="text-right">الإجراء</TableHead>
                      </TableRow></TableHeader>
                      <TableBody>
                        {pendingOrders.map((order) => (
                          <TableRow key={order.id}>
                            <TableCell className="font-medium">{getItemsSummary(order.items)}</TableCell>
                            <TableCell>{order.project_name}</TableCell>
                            <TableCell><Badge className="bg-green-50 text-green-800 border-green-200 border">{order.supplier_name}</Badge></TableCell>
                            <TableCell className="text-sm text-slate-500">{formatDate(order.created_at)}</TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                <Button size="sm" variant="ghost" onClick={() => { setSelectedOrder(order); setViewDialogOpen(true); }} className="h-8 w-8 p-0"><Eye className="w-4 h-4" /></Button>
                                <Button size="sm" className="bg-orange-600 hover:bg-orange-700" onClick={() => handlePrint(order)} disabled={printing}>
                                  <Printer className="w-4 h-4 ml-1" />طباعة وتسجيل
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

        {/* Printed Orders */}
        <div>
          <h2 className="text-lg font-bold flex items-center gap-2 mb-3">
            <CheckCircle className="w-5 h-5 text-green-600" />
            أوامر تمت طباعتها
          </h2>
          <Card className="shadow-sm">
            <CardContent className="p-0">
              {!printedOrders.length ? (
                <div className="text-center py-8"><Printer className="w-10 h-10 text-slate-300 mx-auto mb-2" /><p className="text-slate-500 text-sm">لا توجد أوامر مطبوعة</p></div>
              ) : (
                <>
                  {/* Mobile */}
                  <div className="sm:hidden divide-y">
                    {printedOrders.map((order) => (
                      <div key={order.id} className="p-3 space-y-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-medium text-sm">{getItemsSummary(order.items)}</p>
                            <p className="text-xs text-slate-500">{order.project_name}</p>
                          </div>
                          {getStatusBadge(order.status)}
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-xs text-slate-400">طُبع: {order.printed_at ? formatDate(order.printed_at) : '-'}</span>
                          <Button size="sm" variant="ghost" onClick={() => exportPurchaseOrderToPDF(order)} className="h-7 w-7 p-0"><Download className="w-3 h-3" /></Button>
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
                        <TableHead className="text-right">المورد</TableHead>
                        <TableHead className="text-right">تاريخ الطباعة</TableHead>
                        <TableHead className="text-right">الحالة</TableHead>
                        <TableHead className="text-right">تصدير</TableHead>
                      </TableRow></TableHeader>
                      <TableBody>
                        {printedOrders.map((order) => (
                          <TableRow key={order.id}>
                            <TableCell className="font-medium">{getItemsSummary(order.items)}</TableCell>
                            <TableCell>{order.project_name}</TableCell>
                            <TableCell>{order.supplier_name}</TableCell>
                            <TableCell className="text-sm text-slate-500">{order.printed_at ? formatDate(order.printed_at) : '-'}</TableCell>
                            <TableCell>{getStatusBadge(order.status)}</TableCell>
                            <TableCell>
                              <Button size="sm" variant="ghost" onClick={() => exportPurchaseOrderToPDF(order)} className="h-8 w-8 p-0"><Download className="w-4 h-4 text-green-600" /></Button>
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

      {/* View Order Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="w-[95vw] max-w-md max-h-[85vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader><DialogTitle className="text-center">تفاصيل أمر الشراء</DialogTitle></DialogHeader>
          {selectedOrder && (
            <div className="space-y-3 mt-2">
              <div className="text-center pb-2 border-b">
                <p className="text-xs text-slate-500">رقم الأمر</p>
                <p className="text-lg font-bold text-orange-600">{selectedOrder.id.slice(0, 8).toUpperCase()}</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-lg space-y-2">
                <p className="text-sm font-medium border-b pb-2">الأصناف:</p>
                {selectedOrder.items?.map((item, idx) => (
                  <div key={idx} className="flex justify-between text-sm bg-white p-2 rounded">
                    <span>{item.name}</span>
                    <span className="text-slate-600">{item.quantity} {item.unit}</span>
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-slate-500">المشروع:</span><p className="font-medium">{selectedOrder.project_name}</p></div>
                <div><span className="text-slate-500">المورد:</span><Badge className="bg-green-50 text-green-800 border">{selectedOrder.supplier_name}</Badge></div>
              </div>
              {selectedOrder.notes && <div><span className="text-slate-500 text-sm">ملاحظات:</span><p className="text-sm">{selectedOrder.notes}</p></div>}
              <div className="flex gap-2">
                <Button className="flex-1 bg-green-600 hover:bg-green-700" onClick={() => exportPurchaseOrderToPDF(selectedOrder)}>
                  <Download className="w-4 h-4 ml-2" />تصدير PDF
                </Button>
                {selectedOrder.status === "approved" && (
                  <Button className="flex-1 bg-orange-600 hover:bg-orange-700" onClick={() => { handlePrint(selectedOrder); setViewDialogOpen(false); }} disabled={printing}>
                    <Printer className="w-4 h-4 ml-2" />طباعة
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PrinterDashboard;
