import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { toast } from "sonner";
import { Package, LogOut, Truck, PackageCheck, Clock, CheckCircle, Eye, FileText, ClipboardCheck, KeyRound } from "lucide-react";
import ChangePasswordDialog from "../components/ChangePasswordDialog";

const DeliveryTrackerDashboard = () => {
  const { user, logout, getAuthHeaders, API_URL } = useAuth();
  const [orders, setOrders] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [receiptDialogOpen, setReceiptDialogOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  
  // Receipt form
  const [supplierReceiptNumber, setSupplierReceiptNumber] = useState("");
  const [deliveryNotes, setDeliveryNotes] = useState("");
  const [deliveryItems, setDeliveryItems] = useState([]);

  const fetchData = async () => {
    try {
      const [ordersRes, statsRes] = await Promise.all([
        axios.get(`${API_URL}/delivery-tracker/orders`, getAuthHeaders()),
        axios.get(`${API_URL}/delivery-tracker/stats`, getAuthHeaders()),
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

  const getStatusBadge = (status) => {
    const statusMap = {
      pending_approval: { label: "بانتظار الاعتماد", color: "bg-yellow-100 text-yellow-800" },
      approved: { label: "معتمد", color: "bg-green-100 text-green-800" },
      printed: { label: "تمت الطباعة", color: "bg-blue-100 text-blue-800" },
      shipped: { label: "تم الشحن", color: "bg-purple-100 text-purple-800" },
      partially_delivered: { label: "تسليم جزئي", color: "bg-orange-100 text-orange-800" },
      delivered: { label: "تم التسليم", color: "bg-emerald-100 text-emerald-800" },
    };
    const info = statusMap[status] || { label: status, color: "bg-slate-100 text-slate-800" };
    return <Badge className={`${info.color} text-xs`}>{info.label}</Badge>;
  };

  const openReceiptDialog = (order) => {
    setSelectedOrder(order);
    setSupplierReceiptNumber(order.supplier_receipt_number || "");
    setDeliveryNotes("");
    setDeliveryItems(order.items?.map(item => ({
      name: item.name,
      quantity: item.quantity,
      delivered_before: item.delivered_quantity || 0,
      remaining: item.quantity - (item.delivered_quantity || 0),
      quantity_delivered: 0
    })) || []);
    setReceiptDialogOpen(true);
  };

  const handleConfirmReceipt = async () => {
    if (!supplierReceiptNumber.trim()) {
      toast.error("الرجاء إدخال رقم استلام المورد");
      return;
    }

    const itemsToDeliver = deliveryItems.filter(item => item.quantity_delivered > 0);
    if (itemsToDeliver.length === 0) {
      toast.error("الرجاء تحديد كمية مستلمة لصنف واحد على الأقل");
      return;
    }

    setSubmitting(true);
    try {
      await axios.put(`${API_URL}/delivery-tracker/orders/${selectedOrder.id}/confirm-receipt`, {
        supplier_receipt_number: supplierReceiptNumber,
        delivery_notes: deliveryNotes,
        items_delivered: itemsToDeliver.map(item => ({
          name: item.name,
          quantity_delivered: item.quantity_delivered
        }))
      }, getAuthHeaders());
      
      toast.success("تم تأكيد الاستلام بنجاح");
      setReceiptDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تأكيد الاستلام");
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    try {
      return new Date(dateStr).toLocaleDateString('ar-SA');
    } catch { return dateStr; }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><div className="w-8 h-8 border-4 border-orange-600 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-3 sm:p-4" dir="rtl">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-900 text-white p-3 sm:p-4 rounded-xl shadow-lg mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-600 rounded-lg flex items-center justify-center">
              <Truck className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold">نظام متابعة التوريد</h1>
              <p className="text-xs text-slate-400">لوحة تحكم متابع التوريد</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
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

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <Card className="border-r-4 border-purple-500">
          <CardContent className="p-3">
            <div className="flex items-center gap-2">
              <Truck className="w-5 h-5 text-purple-500" />
              <div>
                <p className="text-xs text-slate-500">بانتظار التسليم</p>
                <p className="text-xl font-bold text-purple-600">{stats.pending_delivery || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-r-4 border-orange-500">
          <CardContent className="p-3">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-orange-500" />
              <div>
                <p className="text-xs text-slate-500">تسليم جزئي</p>
                <p className="text-xl font-bold text-orange-600">{stats.partially_delivered || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-r-4 border-emerald-500">
          <CardContent className="p-3">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-emerald-500" />
              <div>
                <p className="text-xs text-slate-500">تم التسليم</p>
                <p className="text-xl font-bold text-emerald-600">{stats.delivered || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-r-4 border-blue-500">
          <CardContent className="p-3">
            <div className="flex items-center gap-2">
              <Package className="w-5 h-5 text-blue-500" />
              <div>
                <p className="text-xs text-slate-500">بانتظار الشحن</p>
                <p className="text-xl font-bold text-blue-600">{stats.awaiting_shipment || 0}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Orders List */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="w-5 h-5 text-orange-600" />
            أوامر الشراء - متابعة التوريد
          </CardTitle>
        </CardHeader>
        <CardContent className="p-3">
          {orders.length === 0 ? (
            <p className="text-center text-slate-500 py-8">لا توجد أوامر تحتاج متابعة</p>
          ) : (
            <>
              {/* Mobile View */}
              <div className="sm:hidden space-y-3">
                {orders.map((order) => (
                  <div key={order.id} className="bg-slate-50 rounded-lg p-3 border">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <p className="font-bold text-orange-600">{order.id?.slice(0, 8).toUpperCase()}</p>
                        <p className="text-xs text-slate-500">{order.project_name}</p>
                      </div>
                      {getStatusBadge(order.status)}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                      <div><span className="text-slate-400">المورد:</span> {order.supplier_name}</div>
                      <div><span className="text-slate-400">المبلغ:</span> <span className="font-bold text-emerald-600">{order.total_amount?.toLocaleString('ar-SA')} ر.س</span></div>
                      {order.supplier_receipt_number && (
                        <div className="col-span-2"><span className="text-slate-400">رقم الاستلام:</span> <span className="font-bold text-blue-600">{order.supplier_receipt_number}</span></div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => { setSelectedOrder(order); setViewDialogOpen(true); }} className="flex-1">
                        <Eye className="w-3 h-3 ml-1" />التفاصيل
                      </Button>
                      {order.status !== 'delivered' && (
                        <Button size="sm" onClick={() => openReceiptDialog(order)} className="flex-1 bg-orange-600 hover:bg-orange-700">
                          <ClipboardCheck className="w-3 h-3 ml-1" />تأكيد الاستلام
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Desktop View */}
              <div className="hidden sm:block overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-right">رقم الأمر</TableHead>
                      <TableHead className="text-right">المشروع</TableHead>
                      <TableHead className="text-right">المورد</TableHead>
                      <TableHead className="text-center">المبلغ</TableHead>
                      <TableHead className="text-center">رقم استلام المورد</TableHead>
                      <TableHead className="text-center">الحالة</TableHead>
                      <TableHead className="text-center">إجراءات</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orders.map((order) => (
                      <TableRow key={order.id}>
                        <TableCell className="font-bold text-orange-600">{order.id?.slice(0, 8).toUpperCase()}</TableCell>
                        <TableCell>{order.project_name}</TableCell>
                        <TableCell>{order.supplier_name}</TableCell>
                        <TableCell className="text-center font-bold text-emerald-600">{order.total_amount?.toLocaleString('ar-SA')} ر.س</TableCell>
                        <TableCell className="text-center">
                          {order.supplier_receipt_number ? (
                            <span className="font-bold text-blue-600">{order.supplier_receipt_number}</span>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-center">{getStatusBadge(order.status)}</TableCell>
                        <TableCell className="text-center">
                          <div className="flex gap-1 justify-center">
                            <Button size="sm" variant="ghost" onClick={() => { setSelectedOrder(order); setViewDialogOpen(true); }} className="h-8 w-8 p-0">
                              <Eye className="w-4 h-4" />
                            </Button>
                            {order.status !== 'delivered' && (
                              <Button size="sm" onClick={() => openReceiptDialog(order)} className="h-8 bg-orange-600 hover:bg-orange-700">
                                <ClipboardCheck className="w-4 h-4 ml-1" />استلام
                              </Button>
                            )}
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

      {/* View Order Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="w-[95vw] max-w-lg max-h-[90vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader>
            <DialogTitle>تفاصيل أمر الشراء</DialogTitle>
          </DialogHeader>
          {selectedOrder && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-slate-500">رقم الأمر:</span> <span className="font-bold">{selectedOrder.id?.slice(0, 8).toUpperCase()}</span></div>
                <div><span className="text-slate-500">المشروع:</span> {selectedOrder.project_name}</div>
                <div><span className="text-slate-500">المورد:</span> {selectedOrder.supplier_name}</div>
                <div><span className="text-slate-500">المبلغ:</span> <span className="font-bold text-emerald-600">{selectedOrder.total_amount?.toLocaleString('ar-SA')} ر.س</span></div>
                <div><span className="text-slate-500">الحالة:</span> {getStatusBadge(selectedOrder.status)}</div>
                <div><span className="text-slate-500">التاريخ:</span> {formatDate(selectedOrder.created_at)}</div>
                {selectedOrder.supplier_receipt_number && (
                  <div className="col-span-2"><span className="text-slate-500">رقم استلام المورد:</span> <span className="font-bold text-blue-600">{selectedOrder.supplier_receipt_number}</span></div>
                )}
                {selectedOrder.received_by_name && (
                  <div className="col-span-2"><span className="text-slate-500">تم الاستلام بواسطة:</span> {selectedOrder.received_by_name}</div>
                )}
              </div>
              <div className="bg-slate-50 p-3 rounded-lg">
                <p className="text-sm font-medium mb-2">الأصناف:</p>
                {selectedOrder.items?.map((item, idx) => (
                  <div key={idx} className="flex justify-between text-sm py-1 border-b last:border-0">
                    <span>{item.name}</span>
                    <div className="text-left">
                      <span className="text-slate-500">المطلوب: {item.quantity}</span>
                      <span className="mx-2">|</span>
                      <span className={item.delivered_quantity >= item.quantity ? 'text-emerald-600 font-bold' : 'text-orange-600'}>
                        المستلم: {item.delivered_quantity || 0}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Receipt Dialog */}
      <Dialog open={receiptDialogOpen} onOpenChange={setReceiptDialogOpen}>
        <DialogContent className="w-[95vw] max-w-lg max-h-[90vh] overflow-y-auto p-4" dir="rtl">
          <DialogHeader>
            <DialogTitle>تأكيد استلام - {selectedOrder?.id?.slice(0, 8).toUpperCase()}</DialogTitle>
          </DialogHeader>
          {selectedOrder && (
            <div className="space-y-4">
              <div className="bg-blue-50 p-3 rounded-lg text-sm">
                <p><span className="text-slate-500">المشروع:</span> {selectedOrder.project_name}</p>
                <p><span className="text-slate-500">المورد:</span> {selectedOrder.supplier_name}</p>
              </div>

              <div>
                <Label className="text-sm font-medium">رقم استلام المورد *</Label>
                <Input 
                  placeholder="أدخل رقم الاستلام من المورد" 
                  value={supplierReceiptNumber}
                  onChange={(e) => setSupplierReceiptNumber(e.target.value)}
                  className="h-11 mt-1"
                />
              </div>

              <div className="bg-slate-50 p-3 rounded-lg">
                <p className="text-sm font-medium mb-2">الأصناف المستلمة:</p>
                {deliveryItems.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div className="flex-1">
                      <p className="font-medium text-sm">{item.name}</p>
                      <p className="text-xs text-slate-500">المطلوب: {item.quantity} | المُستلم سابقاً: {item.delivered_before} | المتبقي: {item.remaining}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Input 
                        type="number"
                        min="0"
                        max={item.remaining}
                        value={item.quantity_delivered || ""}
                        onChange={(e) => {
                          const val = Math.min(parseInt(e.target.value) || 0, item.remaining);
                          const newItems = [...deliveryItems];
                          newItems[idx].quantity_delivered = val;
                          setDeliveryItems(newItems);
                        }}
                        className="w-20 h-9 text-center"
                        placeholder="0"
                      />
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => {
                          const newItems = [...deliveryItems];
                          newItems[idx].quantity_delivered = item.remaining;
                          setDeliveryItems(newItems);
                        }}
                        className="h-9"
                      >
                        الكل
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              <div>
                <Label className="text-sm font-medium">ملاحظات الاستلام</Label>
                <Textarea 
                  placeholder="أي ملاحظات على الاستلام..."
                  value={deliveryNotes}
                  onChange={(e) => setDeliveryNotes(e.target.value)}
                  rows={2}
                  className="mt-1"
                />
              </div>

              <Button 
                onClick={handleConfirmReceipt} 
                disabled={submitting || !supplierReceiptNumber.trim()}
                className="w-full h-12 bg-orange-600 hover:bg-orange-700"
              >
                {submitting ? "جاري التأكيد..." : `تأكيد الاستلام (${deliveryItems.filter(i => i.quantity_delivered > 0).length} صنف)`}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DeliveryTrackerDashboard;
