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
import { Package, LogOut, Truck, PackageCheck, Clock, CheckCircle, Eye, FileText, ClipboardCheck, KeyRound, Download, Printer } from "lucide-react";
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

  // تصدير إيصال الاستلام كـ PDF
  const exportReceiptPDF = (order) => {
    const printWindow = window.open('', '_blank', 'width=800,height=600');
    
    const itemsRows = order.items?.map((item, idx) => `
      <tr style="background: ${idx % 2 === 0 ? '#f9fafb' : '#fff'};">
        <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: center;">${idx + 1}</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb;">${item.name}</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: center;">${item.quantity}</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: center;">${item.unit || 'قطعة'}</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: center; color: #059669; font-weight: bold;">${item.delivered_quantity || 0}</td>
        <td style="padding: 8px; border: 1px solid #e5e7eb; text-align: center; color: ${(item.quantity - (item.delivered_quantity || 0)) > 0 ? '#dc2626' : '#059669'};">
          ${item.quantity - (item.delivered_quantity || 0)}
        </td>
      </tr>
    `).join('') || '';

    const html = `
      <!DOCTYPE html>
      <html lang="ar" dir="rtl">
      <head>
        <meta charset="UTF-8">
        <title>إيصال استلام - ${order.id?.slice(0, 8).toUpperCase()}</title>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body {
            font-family: 'Cairo', Arial, sans-serif;
            direction: rtl;
            padding: 20px;
            background: white;
            font-size: 12px;
            max-width: 800px;
            margin: 0 auto;
          }
          @media print {
            body { padding: 10px; }
            .no-print { display: none !important; }
            @page { size: A4; margin: 10mm; }
          }
          .header {
            border: 2px solid #059669;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            text-align: center;
            background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
          }
          .header h1 { color: #059669; font-size: 24px; margin-bottom: 5px; }
          .header .order-num { font-size: 14px; color: #374151; }
          .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            background: #f9fafb;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
          }
          .info-item { display: flex; gap: 8px; }
          .info-label { color: #6b7280; min-width: 100px; }
          .info-value { font-weight: 600; color: #1f2937; }
          .receipt-box {
            background: #fef3c7;
            border: 2px solid #f59e0b;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            text-align: center;
          }
          .receipt-box h2 { color: #92400e; font-size: 14px; margin-bottom: 10px; }
          .receipt-number {
            font-size: 28px;
            font-weight: 700;
            color: #1f2937;
            letter-spacing: 2px;
            background: white;
            padding: 10px 20px;
            border-radius: 6px;
            display: inline-block;
          }
          table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
          th {
            background: #374151;
            color: white;
            padding: 10px;
            font-size: 11px;
            border: 1px solid #374151;
          }
          .signature-area {
            display: flex;
            justify-content: space-between;
            margin-top: 40px;
            padding: 0 30px;
          }
          .signature-box {
            text-align: center;
            width: 40%;
          }
          .signature-line {
            border-top: 1px solid #9ca3af;
            padding-top: 8px;
            margin-top: 40px;
            color: #6b7280;
            font-size: 11px;
          }
          .footer {
            border-top: 1px solid #e5e7eb;
            padding-top: 15px;
            margin-top: 30px;
            text-align: center;
            color: #9ca3af;
            font-size: 10px;
          }
          .print-btn {
            position: fixed;
            top: 20px;
            left: 20px;
            background: #059669;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-family: inherit;
          }
          .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
          }
          .status-delivered { background: #d1fae5; color: #065f46; }
          .status-partial { background: #ffedd5; color: #9a3412; }
        </style>
      </head>
      <body>
        <button class="print-btn no-print" onclick="window.print()">طباعة / حفظ PDF</button>
        
        <div class="header">
          <h1>إيصال استلام مواد</h1>
          <div class="order-num">أمر شراء رقم: ${order.id?.slice(0, 8).toUpperCase()}</div>
          <span class="status-badge ${order.status === 'delivered' ? 'status-delivered' : 'status-partial'}">
            ${order.status === 'delivered' ? 'تم التسليم بالكامل' : 'تسليم جزئي'}
          </span>
        </div>
        
        <div class="receipt-box">
          <h2>رقم استلام المورد</h2>
          <div class="receipt-number">${order.supplier_receipt_number || '-'}</div>
        </div>
        
        <div class="info-grid">
          <div class="info-item"><span class="info-label">المشروع:</span> <span class="info-value">${order.project_name || '-'}</span></div>
          <div class="info-item"><span class="info-label">تاريخ الاستلام:</span> <span class="info-value">${formatDate(order.delivery_date || order.updated_at)}</span></div>
          <div class="info-item"><span class="info-label">المورد:</span> <span class="info-value">${order.supplier_name || '-'}</span></div>
          <div class="info-item"><span class="info-label">تاريخ أمر الشراء:</span> <span class="info-value">${formatDate(order.created_at)}</span></div>
          <div class="info-item"><span class="info-label">المستلم:</span> <span class="info-value">${order.received_by_name || '-'}</span></div>
          <div class="info-item"><span class="info-label">المبلغ الإجمالي:</span> <span class="info-value" style="color: #059669;">${order.total_amount?.toLocaleString('ar-SA') || 0} ر.س</span></div>
        </div>
        
        <h3 style="color: #374151; margin-bottom: 10px; font-size: 14px; border-bottom: 2px solid #059669; padding-bottom: 5px;">تفاصيل المواد المستلمة</h3>
        <table>
          <thead>
            <tr>
              <th style="width: 40px;">#</th>
              <th>اسم المادة</th>
              <th style="width: 80px;">الكمية المطلوبة</th>
              <th style="width: 60px;">الوحدة</th>
              <th style="width: 80px;">الكمية المستلمة</th>
              <th style="width: 80px;">المتبقي</th>
            </tr>
          </thead>
          <tbody>${itemsRows}</tbody>
        </table>
        
        ${order.delivery_notes ? `
          <div style="background: #eff6ff; border: 1px solid #93c5fd; border-radius: 6px; padding: 10px; margin-bottom: 20px;">
            <strong style="color: #1d4ed8;">ملاحظات الاستلام:</strong>
            <p style="margin-top: 5px; color: #374151;">${order.delivery_notes}</p>
          </div>
        ` : ''}
        
        <div class="signature-area">
          <div class="signature-box">
            <div class="signature-line">توقيع المستلم</div>
          </div>
          <div class="signature-box">
            <div class="signature-line">توقيع المورد / المندوب</div>
          </div>
        </div>
        
        <div class="footer">
          <p>نظام إدارة طلبات المواد - إيصال استلام</p>
          <p style="margin-top: 5px;">تاريخ الطباعة: ${formatDate(new Date().toISOString())}</p>
        </div>
        
        <script>
          document.fonts.ready.then(() => { setTimeout(() => window.print(), 500); });
        </script>
      </body>
      </html>
    `;
    
    printWindow.document.write(html);
    printWindow.document.close();
  };

  // تقسيم الأوامر حسب الحالة
  const pendingOrders = orders.filter(o => ['approved', 'printed', 'shipped', 'partially_delivered'].includes(o.status));
  const deliveredOrders = orders.filter(o => o.status === 'delivered');

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

      {/* Pending Orders - بانتظار الاستلام */}
      <Card className="mb-4">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Clock className="w-5 h-5 text-orange-600" />
            أوامر بانتظار الاستلام
            <Badge className="bg-orange-100 text-orange-800">{pendingOrders.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-3">
          {pendingOrders.length === 0 ? (
            <p className="text-center text-slate-500 py-6">لا توجد أوامر بانتظار الاستلام</p>
          ) : (
            <>
              {/* Mobile View */}
              <div className="sm:hidden space-y-3">
                {pendingOrders.map((order) => (
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
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => { setSelectedOrder(order); setViewDialogOpen(true); }} className="flex-1">
                        <Eye className="w-3 h-3 ml-1" />التفاصيل
                      </Button>
                      <Button size="sm" onClick={() => openReceiptDialog(order)} className="flex-1 bg-orange-600 hover:bg-orange-700">
                        <ClipboardCheck className="w-3 h-3 ml-1" />تأكيد الاستلام
                      </Button>
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
                      <TableHead className="text-center">الحالة</TableHead>
                      <TableHead className="text-center">إجراءات</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pendingOrders.map((order) => (
                      <TableRow key={order.id}>
                        <TableCell className="font-bold text-orange-600">{order.id?.slice(0, 8).toUpperCase()}</TableCell>
                        <TableCell>{order.project_name}</TableCell>
                        <TableCell>{order.supplier_name}</TableCell>
                        <TableCell className="text-center font-bold text-emerald-600">{order.total_amount?.toLocaleString('ar-SA')} ر.س</TableCell>
                        <TableCell className="text-center">{getStatusBadge(order.status)}</TableCell>
                        <TableCell className="text-center">
                          <div className="flex gap-1 justify-center">
                            <Button size="sm" variant="ghost" onClick={() => { setSelectedOrder(order); setViewDialogOpen(true); }} className="h-8 w-8 p-0">
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button size="sm" onClick={() => openReceiptDialog(order)} className="h-8 bg-orange-600 hover:bg-orange-700">
                              <ClipboardCheck className="w-4 h-4 ml-1" />استلام
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

      {/* Delivered Orders - تم الاستلام */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-600" />
            أوامر تم استلامها
            <Badge className="bg-emerald-100 text-emerald-800">{deliveredOrders.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-3">
          {deliveredOrders.length === 0 ? (
            <p className="text-center text-slate-500 py-6">لا توجد أوامر مستلمة</p>
          ) : (
            <>
              {/* Mobile View */}
              <div className="sm:hidden space-y-3">
                {deliveredOrders.map((order) => (
                  <div key={order.id} className="bg-emerald-50 rounded-lg p-3 border border-emerald-200">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <p className="font-bold text-emerald-700">{order.id?.slice(0, 8).toUpperCase()}</p>
                        <p className="text-xs text-slate-500">{order.project_name}</p>
                      </div>
                      {getStatusBadge(order.status)}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                      <div><span className="text-slate-400">المورد:</span> {order.supplier_name}</div>
                      <div><span className="text-slate-400">المبلغ:</span> <span className="font-bold text-emerald-600">{order.total_amount?.toLocaleString('ar-SA')} ر.س</span></div>
                      <div className="col-span-2">
                        <span className="text-slate-400">رقم الاستلام:</span> 
                        <span className="font-bold text-blue-600 mr-1">{order.supplier_receipt_number || '-'}</span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => { setSelectedOrder(order); setViewDialogOpen(true); }} className="flex-1">
                        <Eye className="w-3 h-3 ml-1" />التفاصيل
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => exportReceiptPDF(order)} className="flex-1 text-emerald-700 border-emerald-300 hover:bg-emerald-50">
                        <Download className="w-3 h-3 ml-1" />تصدير الإيصال
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Desktop View */}
              <div className="hidden sm:block overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-emerald-50">
                      <TableHead className="text-right">رقم الأمر</TableHead>
                      <TableHead className="text-right">المشروع</TableHead>
                      <TableHead className="text-right">المورد</TableHead>
                      <TableHead className="text-center">المبلغ</TableHead>
                      <TableHead className="text-center">رقم استلام المورد</TableHead>
                      <TableHead className="text-center">المستلم</TableHead>
                      <TableHead className="text-center">إجراءات</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {deliveredOrders.map((order) => (
                      <TableRow key={order.id} className="bg-emerald-50/50 hover:bg-emerald-100/50">
                        <TableCell className="font-bold text-emerald-700">{order.id?.slice(0, 8).toUpperCase()}</TableCell>
                        <TableCell>{order.project_name}</TableCell>
                        <TableCell>{order.supplier_name}</TableCell>
                        <TableCell className="text-center font-bold text-emerald-600">{order.total_amount?.toLocaleString('ar-SA')} ر.س</TableCell>
                        <TableCell className="text-center">
                          <span className="font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded">{order.supplier_receipt_number || '-'}</span>
                        </TableCell>
                        <TableCell className="text-center text-sm">{order.received_by_name || '-'}</TableCell>
                        <TableCell className="text-center">
                          <div className="flex gap-1 justify-center">
                            <Button size="sm" variant="ghost" onClick={() => { setSelectedOrder(order); setViewDialogOpen(true); }} className="h-8 w-8 p-0">
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => exportReceiptPDF(order)} className="h-8 text-emerald-700 border-emerald-300 hover:bg-emerald-50">
                              <Printer className="w-4 h-4 ml-1" />طباعة
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

      {/* Change Password Dialog */}
      <ChangePasswordDialog 
        open={passwordDialogOpen} 
        onOpenChange={setPasswordDialogOpen}
        token={localStorage.getItem("token")}
      />
    </div>
  );
};

export default DeliveryTrackerDashboard;
