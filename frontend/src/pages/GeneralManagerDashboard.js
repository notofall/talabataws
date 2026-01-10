import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import axios from 'axios';
import { 
  ClipboardCheck, 
  LogOut, 
  DollarSign, 
  Clock, 
  CheckCircle,
  XCircle,
  Eye,
  Settings,
  RefreshCw,
  AlertTriangle,
  KeyRound,
  FileText,
  Truck,
  Download
} from 'lucide-react';
import ChangePasswordDialog from '../components/ChangePasswordDialog';
import { exportPurchaseOrderToPDF } from '../utils/pdfExport';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function GeneralManagerDashboard() {
  const { user, logout, token } = useAuth();
  const [stats, setStats] = useState({
    pending_approval: 0,
    approved_this_month: 0,
    total_approved_amount: 0,
    approval_limit: 20000
  });
  const [pendingOrders, setPendingOrders] = useState([]);
  const [gmApprovedOrders, setGmApprovedOrders] = useState([]); // الأوامر المعتمدة من المدير العام
  const [procurementApprovedOrders, setProcurementApprovedOrders] = useState([]); // الأوامر المعتمدة من المشتريات
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [settings, setSettings] = useState([]);
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [orderToReject, setOrderToReject] = useState(null);
  const [activeTab, setActiveTab] = useState('pending'); // 'pending', 'gm_approved', 'procurement_approved'
  const [pendingPage, setPendingPage] = useState(1);
  const [gmApprovedPage, setGmApprovedPage] = useState(1);
  const [procurementApprovedPage, setProcurementApprovedPage] = useState(1);
  const [pendingTotalPages, setPendingTotalPages] = useState(1);
  const [gmApprovedTotalPages, setGmApprovedTotalPages] = useState(1);
  const [procurementApprovedTotalPages, setProcurementApprovedTotalPages] = useState(1);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      
      const [statsRes, pendingRes, gmApprovedRes, procurementApprovedRes] = await Promise.all([
        axios.get(`${API_URL}/api/gm/stats`, { headers }),
        axios.get(`${API_URL}/api/gm/all-orders?status=pending&page=${pendingPage}&page_size=10`, { headers }),
        axios.get(`${API_URL}/api/gm/all-orders?status=gm_approved&page=${gmApprovedPage}&page_size=10`, { headers }),
        axios.get(`${API_URL}/api/gm/all-orders?status=procurement_approved&page=${procurementApprovedPage}&page_size=10`, { headers })
      ]);
      
      setStats(statsRes.data);
      setPendingOrders(pendingRes.data.items || []);
      setPendingTotalPages(pendingRes.data.total_pages || 1);
      setGmApprovedOrders(gmApprovedRes.data.items || []);
      setGmApprovedTotalPages(gmApprovedRes.data.total_pages || 1);
      setProcurementApprovedOrders(procurementApprovedRes.data.items || []);
      setProcurementApprovedTotalPages(procurementApprovedRes.data.total_pages || 1);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('حدث خطأ في تحميل البيانات');
    } finally {
      setLoading(false);
    }
  }, [token, pendingPage, gmApprovedPage, procurementApprovedPage]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const fetchSettings = async () => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const res = await axios.get(`${API_URL}/api/system-settings`, { headers });
      setSettings(res.data);
      setShowSettingsDialog(true);
    } catch (error) {
      toast.error('حدث خطأ في تحميل الإعدادات');
    }
  };

  const updateSetting = async (key, value) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.put(`${API_URL}/api/system-settings/${key}`, { value }, { headers });
      toast.success('تم تحديث الإعداد بنجاح');
      fetchData();
    } catch (error) {
      toast.error('حدث خطأ في تحديث الإعداد');
    }
  };

  const handleApprove = async (orderId) => {
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.put(`${API_URL}/api/gm/approve/${orderId}`, {}, { headers });
      toast.success('تم اعتماد أمر الشراء بنجاح');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'حدث خطأ في الاعتماد');
    }
  };

  const handleReject = async () => {
    if (!orderToReject) return;
    
    try {
      const headers = { Authorization: `Bearer ${token}` };
      await axios.put(`${API_URL}/api/gm/reject/${orderToReject}?rejection_reason=${encodeURIComponent(rejectionReason)}`, {}, { headers });
      toast.success('تم رفض أمر الشراء');
      setShowRejectDialog(false);
      setOrderToReject(null);
      setRejectionReason('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'حدث خطأ في الرفض');
    }
  };

  const openRejectDialog = (orderId) => {
    setOrderToReject(orderId);
    setShowRejectDialog(true);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ar-SA', {
      style: 'currency',
      currency: 'SAR',
      minimumFractionDigits: 0
    }).format(amount || 0);
  };

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('ar-SA');
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      'pending_gm_approval': { label: 'بانتظار الموافقة', color: 'bg-amber-100 text-amber-800' },
      'approved': { label: 'معتمد', color: 'bg-green-100 text-green-800' },
      'delivered': { label: 'تم التسليم', color: 'bg-blue-100 text-blue-800' },
      'partially_delivered': { label: 'تسليم جزئي', color: 'bg-cyan-100 text-cyan-800' },
      'rejected_by_gm': { label: 'مرفوض', color: 'bg-red-100 text-red-800' },
    };
    const statusInfo = statusMap[status] || { label: status, color: 'bg-slate-100 text-slate-800' };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusInfo.color}`}>
        {statusInfo.label}
      </span>
    );
  };

  const currentOrders = activeTab === 'pending' ? pendingOrders : approvedOrders;
  const currentPage = activeTab === 'pending' ? pendingPage : approvedPage;
  const totalPages = activeTab === 'pending' ? pendingTotalPages : approvedTotalPages;
  const setCurrentPage = activeTab === 'pending' ? setPendingPage : setApprovedPage;

  return (
    <div className="min-h-screen bg-slate-50" dir="rtl">
      {/* Header */}
      <header className="bg-gradient-to-l from-purple-700 to-purple-600 text-white shadow-lg">
        <div className="container mx-auto px-3 sm:px-4 py-3 sm:py-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
                <ClipboardCheck className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-lg sm:text-xl font-bold">لوحة تحكم المدير العام</h1>
                <p className="text-purple-200 text-xs sm:text-sm">مرحباً، {user?.name}</p>
              </div>
            </div>
            <div className="flex items-center gap-1 sm:gap-2 flex-wrap">
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchSettings}
                className="text-white hover:bg-white/20 h-8 px-2 text-xs sm:text-sm"
              >
                <Settings className="w-4 h-4 sm:ml-1" />
                <span className="hidden sm:inline">الإعدادات</span>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={fetchData}
                className="text-white hover:bg-white/20 h-8 px-2 text-xs sm:text-sm"
              >
                <RefreshCw className="w-4 h-4 sm:ml-1" />
                <span className="hidden sm:inline">تحديث</span>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPasswordDialogOpen(true)}
                className="text-white hover:bg-white/20 h-8 px-2"
              >
                <KeyRound className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                className="text-white hover:bg-white/20 h-8 px-2 text-xs sm:text-sm"
              >
                <LogOut className="w-4 h-4 sm:ml-1" />
                <span className="hidden sm:inline">خروج</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Stats Cards */}
      <div className="container mx-auto px-3 sm:px-4 py-4 sm:py-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4 mb-4 sm:mb-6">
          <div className="bg-white rounded-xl shadow-sm p-3 sm:p-4 border border-slate-100">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-amber-100 rounded-lg flex items-center justify-center shrink-0">
                <Clock className="w-5 h-5 sm:w-6 sm:h-6 text-amber-600" />
              </div>
              <div className="min-w-0">
                <p className="text-slate-500 text-xs sm:text-sm truncate">بانتظار الموافقة</p>
                <p className="text-xl sm:text-2xl font-bold text-slate-800">{stats.pending_approval}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-3 sm:p-4 border border-slate-100">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-green-100 rounded-lg flex items-center justify-center shrink-0">
                <CheckCircle className="w-5 h-5 sm:w-6 sm:h-6 text-green-600" />
              </div>
              <div className="min-w-0">
                <p className="text-slate-500 text-xs sm:text-sm truncate">معتمد هذا الشهر</p>
                <p className="text-xl sm:text-2xl font-bold text-slate-800">{stats.approved_this_month}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-3 sm:p-4 border border-slate-100">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-blue-100 rounded-lg flex items-center justify-center shrink-0">
                <DollarSign className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600" />
              </div>
              <div className="min-w-0">
                <p className="text-slate-500 text-xs sm:text-sm truncate">إجمالي المعتمد</p>
                <p className="text-lg sm:text-xl font-bold text-slate-800">{formatCurrency(stats.total_approved_amount)}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-3 sm:p-4 border border-slate-100">
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-purple-100 rounded-lg flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5 sm:w-6 sm:h-6 text-purple-600" />
              </div>
              <div className="min-w-0">
                <p className="text-slate-500 text-xs sm:text-sm truncate">حد الموافقة</p>
                <p className="text-lg sm:text-xl font-bold text-slate-800">{formatCurrency(stats.approval_limit)}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Orders Section with Tabs */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100">
          {/* Tabs */}
          <div className="border-b border-slate-100">
            <div className="flex">
              <button
                onClick={() => setActiveTab('pending')}
                className={`flex-1 sm:flex-none px-4 sm:px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'pending'
                    ? 'border-purple-600 text-purple-600 bg-purple-50'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                }`}
              >
                <Clock className="w-4 h-4 inline-block ml-1" />
                بانتظار الموافقة
                {pendingOrders.length > 0 && (
                  <span className="mr-2 px-2 py-0.5 bg-amber-100 text-amber-700 rounded-full text-xs">
                    {pendingOrders.length}
                  </span>
                )}
              </button>
              <button
                onClick={() => setActiveTab('approved')}
                className={`flex-1 sm:flex-none px-4 sm:px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'approved'
                    ? 'border-purple-600 text-purple-600 bg-purple-50'
                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-50'
                }`}
              >
                <CheckCircle className="w-4 h-4 inline-block ml-1" />
                الأوامر المعتمدة
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-3 sm:p-4 border-b border-slate-100">
            <h2 className="text-base sm:text-lg font-bold text-slate-800">
              {activeTab === 'pending' ? 'أوامر الشراء بانتظار الموافقة' : 'أوامر الشراء المعتمدة'}
            </h2>
            <p className="text-xs sm:text-sm text-slate-500">
              {activeTab === 'pending' 
                ? `أوامر شراء تتجاوز ${formatCurrency(stats.approval_limit)}`
                : 'جميع أوامر الشراء التي تمت الموافقة عليها'}
            </p>
          </div>

          {loading ? (
            <div className="p-8 text-center">
              <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
              <p className="text-slate-500">جاري التحميل...</p>
            </div>
          ) : currentOrders.length === 0 ? (
            <div className="p-8 text-center">
              {activeTab === 'pending' ? (
                <>
                  <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-2" />
                  <p className="text-slate-500">لا توجد طلبات بانتظار الموافقة</p>
                </>
              ) : (
                <>
                  <FileText className="w-12 h-12 text-slate-300 mx-auto mb-2" />
                  <p className="text-slate-500">لا توجد أوامر معتمدة</p>
                </>
              )}
            </div>
          ) : (
            <>
              {/* Mobile Cards View */}
              <div className="block sm:hidden divide-y divide-slate-100">
                {currentOrders.map((order) => (
                  <div key={order.id} className="p-3 hover:bg-slate-50">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <p className="font-medium text-slate-800">{order.request_number || order.id.slice(0, 8)}</p>
                        <p className="text-xs text-slate-500">{order.project_name}</p>
                      </div>
                      <div className="text-left">
                        <span className="text-sm font-bold text-purple-600 block">{formatCurrency(order.total_amount)}</span>
                        {getStatusBadge(order.status)}
                      </div>
                    </div>
                    <div className="flex justify-between items-center text-xs text-slate-500 mb-3">
                      <span>{order.supplier_name}</span>
                      <span>{formatDate(order.created_at)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => { setSelectedOrder(order); setShowDetailsDialog(true); }}
                        className="flex-1 h-8 text-xs"
                      >
                        <Eye className="w-3 h-3 ml-1" />
                        تفاصيل
                      </Button>
                      {activeTab === 'approved' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => exportPurchaseOrderToPDF(order)}
                          className="flex-1 h-8 text-xs text-green-600 border-green-200 hover:bg-green-50"
                        >
                          <Download className="w-3 h-3 ml-1" />
                          PDF
                        </Button>
                      )}
                      {activeTab === 'pending' && (
                        <>
                          <Button
                            size="sm"
                            onClick={() => handleApprove(order.id)}
                            className="flex-1 h-8 text-xs bg-green-600 hover:bg-green-700"
                          >
                            <CheckCircle className="w-3 h-3 ml-1" />
                            اعتماد
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => openRejectDialog(order.id)}
                            className="flex-1 h-8 text-xs"
                          >
                            <XCircle className="w-3 h-3 ml-1" />
                            رفض
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Desktop Table View */}
              <div className="hidden sm:block overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">رقم الأمر</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">المشروع</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">المورد</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">المبلغ</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">الحالة</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">التاريخ</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">الإجراءات</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {currentOrders.map((order) => (
                      <tr key={order.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-800 font-medium">{order.request_number || order.id.slice(0, 8)}</td>
                        <td className="px-4 py-3 text-sm text-slate-800">{order.project_name}</td>
                        <td className="px-4 py-3 text-sm text-slate-800">{order.supplier_name}</td>
                        <td className="px-4 py-3">
                          <span className="text-sm font-bold text-purple-600">{formatCurrency(order.total_amount)}</span>
                        </td>
                        <td className="px-4 py-3">{getStatusBadge(order.status)}</td>
                        <td className="px-4 py-3 text-sm text-slate-500">{formatDate(order.created_at)}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => { setSelectedOrder(order); setShowDetailsDialog(true); }}
                              className="text-slate-600 hover:text-purple-600"
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                            {activeTab === 'approved' && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => exportPurchaseOrderToPDF(order)}
                                className="text-green-600 border-green-200 hover:bg-green-50"
                              >
                                <Download className="w-4 h-4 ml-1" />
                                PDF
                              </Button>
                            )}
                            {activeTab === 'pending' && (
                              <>
                                <Button
                                  variant="default"
                                  size="sm"
                                  onClick={() => handleApprove(order.id)}
                                  className="bg-green-600 hover:bg-green-700"
                                >
                                  <CheckCircle className="w-4 h-4 ml-1" />
                                  اعتماد
                                </Button>
                                <Button
                                  variant="destructive"
                                  size="sm"
                                  onClick={() => openRejectDialog(order.id)}
                                >
                                  <XCircle className="w-4 h-4 ml-1" />
                                  رفض
                                </Button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between p-4 border-t border-slate-100">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                  >
                    السابق
                  </Button>
                  <span className="text-sm text-slate-500">
                    صفحة {currentPage} من {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                  >
                    التالي
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Order Details Dialog */}
      {showDetailsDialog && selectedOrder && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center sticky top-0 bg-white">
              <h3 className="text-lg font-bold text-slate-800">تفاصيل أمر الشراء</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowDetailsDialog(false)}>
                <XCircle className="w-5 h-5" />
              </Button>
            </div>
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-500">رقم الأمر</p>
                  <p className="font-medium">{selectedOrder.request_number || selectedOrder.id.slice(0, 8)}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">المشروع</p>
                  <p className="font-medium">{selectedOrder.project_name}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">المورد</p>
                  <p className="font-medium">{selectedOrder.supplier_name}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">الحالة</p>
                  {getStatusBadge(selectedOrder.status)}
                </div>
                <div>
                  <p className="text-sm text-slate-500">التاريخ</p>
                  <p className="font-medium">{formatDate(selectedOrder.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">المبلغ الإجمالي</p>
                  <p className="font-bold text-purple-600 text-lg">{formatCurrency(selectedOrder.total_amount)}</p>
                </div>
              </div>

              {selectedOrder.items && selectedOrder.items.length > 0 && (
                <div>
                  <p className="text-sm text-slate-500 mb-2">الأصناف</p>
                  <div className="border rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50">
                        <tr>
                          <th className="px-3 py-2 text-right">الصنف</th>
                          <th className="px-3 py-2 text-right">الكمية</th>
                          <th className="px-3 py-2 text-right">السعر</th>
                          <th className="px-3 py-2 text-right">الإجمالي</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {selectedOrder.items.map((item, idx) => (
                          <tr key={idx}>
                            <td className="px-3 py-2">{item.name}</td>
                            <td className="px-3 py-2">{item.quantity} {item.unit}</td>
                            <td className="px-3 py-2">{formatCurrency(item.unit_price)}</td>
                            <td className="px-3 py-2">{formatCurrency(item.total_price)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {selectedOrder.notes && (
                <div>
                  <p className="text-sm text-slate-500">ملاحظات</p>
                  <p className="bg-slate-50 p-3 rounded-lg text-sm">{selectedOrder.notes}</p>
                </div>
              )}

              {selectedOrder.gm_approved_at && (
                <div className="bg-green-50 p-3 rounded-lg">
                  <p className="text-sm text-green-800">
                    <CheckCircle className="w-4 h-4 inline ml-1" />
                    تم الاعتماد بواسطة {selectedOrder.gm_approved_by_name} في {formatDate(selectedOrder.gm_approved_at)}
                  </p>
                </div>
              )}

              {/* Export PDF Button */}
              {selectedOrder.status !== 'pending_gm_approval' && (
                <div className="pt-2 border-t">
                  <Button 
                    onClick={() => exportPurchaseOrderToPDF(selectedOrder)}
                    className="w-full bg-green-600 hover:bg-green-700"
                  >
                    <Download className="w-4 h-4 ml-2" />
                    تصدير أمر الشراء PDF
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Reject Dialog */}
      {showRejectDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
            <div className="p-4 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-800">رفض أمر الشراء</h3>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">سبب الرفض (اختياري)</label>
                <textarea
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg p-3 text-sm"
                  rows={3}
                  placeholder="أدخل سبب الرفض..."
                />
              </div>
              <div className="flex gap-2">
                <Button
                  variant="destructive"
                  onClick={handleReject}
                  className="flex-1"
                >
                  تأكيد الرفض
                </Button>
                <Button
                  variant="outline"
                  onClick={() => { setShowRejectDialog(false); setOrderToReject(null); setRejectionReason(''); }}
                  className="flex-1"
                >
                  إلغاء
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Settings Dialog */}
      {showSettingsDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center">
              <h3 className="text-lg font-bold text-slate-800">إعدادات النظام</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowSettingsDialog(false)}>
                <XCircle className="w-5 h-5" />
              </Button>
            </div>
            <div className="p-4 space-y-4">
              {settings.map((setting) => (
                <div key={setting.key} className="flex justify-between items-center">
                  <div>
                    <p className="font-medium text-slate-800">
                      {setting.key === 'approval_limit' ? 'حد الموافقة' : setting.key}
                    </p>
                    <p className="text-xs text-slate-500">
                      {setting.key === 'approval_limit' && 'أوامر الشراء التي تتجاوز هذا المبلغ تحتاج موافقتك'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      value={setting.value}
                      onChange={(e) => {
                        const newSettings = settings.map(s => 
                          s.key === setting.key ? {...s, value: parseInt(e.target.value)} : s
                        );
                        setSettings(newSettings);
                      }}
                      className="w-28 border border-slate-200 rounded px-2 py-1 text-sm"
                    />
                    <Button
                      size="sm"
                      onClick={() => updateSetting(setting.key, setting.value)}
                      className="bg-purple-600 hover:bg-purple-700"
                    >
                      حفظ
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Change Password Dialog */}
      <ChangePasswordDialog 
        open={passwordDialogOpen} 
        onOpenChange={setPasswordDialogOpen}
        token={token}
      />
    </div>
  );
}
