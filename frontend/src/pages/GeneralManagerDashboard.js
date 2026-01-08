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
  AlertTriangle
} from 'lucide-react';

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
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [settings, setSettings] = useState([]);
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [orderToReject, setOrderToReject] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      
      const [statsRes, ordersRes] = await Promise.all([
        axios.get(`${API_URL}/api/gm/stats`, { headers }),
        axios.get(`${API_URL}/api/gm/pending-approvals?page=${page}&page_size=10`, { headers })
      ]);
      
      setStats(statsRes.data);
      setPendingOrders(ordersRes.data.items || []);
      setTotalPages(ordersRes.data.total_pages || 1);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('حدث خطأ في تحميل البيانات');
    } finally {
      setLoading(false);
    }
  }, [token, page]);

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

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-gradient-to-l from-purple-700 to-purple-600 text-white shadow-lg">
        <div className="container mx-auto px-3 sm:px-4 py-3 sm:py-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center">
                <ClipboardCheck className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-lg sm:text-xl font-bold">المدير العام</h1>
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

        {/* Pending Orders Table */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-100">
          <div className="p-3 sm:p-4 border-b border-slate-100">
            <h2 className="text-base sm:text-lg font-bold text-slate-800">أوامر الشراء بانتظار الموافقة</h2>
            <p className="text-xs sm:text-sm text-slate-500">أوامر شراء تتجاوز {formatCurrency(stats.approval_limit)}</p>
          </div>

          {loading ? (
            <div className="p-8 text-center">
              <div className="w-8 h-8 border-4 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
              <p className="text-slate-500">جاري التحميل...</p>
            </div>
          ) : pendingOrders.length === 0 ? (
            <div className="p-8 text-center">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-2" />
              <p className="text-slate-500">لا توجد طلبات بانتظار الموافقة</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">رقم الطلب</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">المشروع</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">المورد</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">المبلغ</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">التاريخ</th>
                      <th className="px-4 py-3 text-right text-sm font-medium text-slate-600">الإجراءات</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {pendingOrders.map((order) => (
                      <tr key={order.id} className="hover:bg-slate-50">
                        <td className="px-4 py-3 text-sm text-slate-800">{order.request_number || order.id.slice(0, 8)}</td>
                        <td className="px-4 py-3 text-sm text-slate-800">{order.project_name}</td>
                        <td className="px-4 py-3 text-sm text-slate-800">{order.supplier_name}</td>
                        <td className="px-4 py-3">
                          <span className="text-sm font-bold text-red-600">{formatCurrency(order.total_amount)}</span>
                        </td>
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
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    السابق
                  </Button>
                  <span className="text-sm text-slate-500">
                    صفحة {page} من {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
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
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center">
              <h3 className="text-lg font-bold">تفاصيل أمر الشراء</h3>
              <Button variant="ghost" size="sm" onClick={() => setShowDetailsDialog(false)}>×</Button>
            </div>
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-500">رقم الطلب</p>
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
                  <p className="text-sm text-slate-500">المبلغ الإجمالي</p>
                  <p className="font-bold text-red-600">{formatCurrency(selectedOrder.total_amount)}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">المشرف</p>
                  <p className="font-medium">{selectedOrder.supervisor_name}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">المهندس</p>
                  <p className="font-medium">{selectedOrder.engineer_name}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">مدير المشتريات</p>
                  <p className="font-medium">{selectedOrder.manager_name}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">التاريخ</p>
                  <p className="font-medium">{formatDate(selectedOrder.created_at)}</p>
                </div>
              </div>

              {/* Items */}
              <div className="mt-4">
                <h4 className="font-medium mb-2">الأصناف</h4>
                <div className="bg-slate-50 rounded-lg p-3">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="text-right pb-2">الصنف</th>
                        <th className="text-right pb-2">الكمية</th>
                        <th className="text-right pb-2">السعر</th>
                        <th className="text-right pb-2">الإجمالي</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedOrder.items?.map((item, idx) => (
                        <tr key={idx} className="border-b border-slate-100 last:border-0">
                          <td className="py-2">{item.name}</td>
                          <td className="py-2">{item.quantity} {item.unit}</td>
                          <td className="py-2">{formatCurrency(item.unit_price)}</td>
                          <td className="py-2 font-medium">{formatCurrency(item.total_price)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {selectedOrder.notes && (
                <div>
                  <p className="text-sm text-slate-500">ملاحظات</p>
                  <p className="bg-slate-50 p-2 rounded">{selectedOrder.notes}</p>
                </div>
              )}
            </div>
            <div className="p-4 border-t border-slate-100 flex gap-2 justify-end">
              <Button variant="outline" onClick={() => setShowDetailsDialog(false)}>إغلاق</Button>
              <Button className="bg-green-600 hover:bg-green-700" onClick={() => { handleApprove(selectedOrder.id); setShowDetailsDialog(false); }}>
                <CheckCircle className="w-4 h-4 ml-1" />
                اعتماد
              </Button>
              <Button variant="destructive" onClick={() => { openRejectDialog(selectedOrder.id); setShowDetailsDialog(false); }}>
                <XCircle className="w-4 h-4 ml-1" />
                رفض
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Dialog */}
      {showRejectDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            <div className="p-4 border-b border-slate-100">
              <h3 className="text-lg font-bold text-red-600">رفض أمر الشراء</h3>
            </div>
            <div className="p-4">
              <label className="block text-sm font-medium text-slate-700 mb-2">سبب الرفض (اختياري)</label>
              <textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
                rows={3}
                placeholder="أدخل سبب الرفض..."
              />
            </div>
            <div className="p-4 border-t border-slate-100 flex gap-2 justify-end">
              <Button variant="outline" onClick={() => { setShowRejectDialog(false); setOrderToReject(null); setRejectionReason(''); }}>
                إلغاء
              </Button>
              <Button variant="destructive" onClick={handleReject}>
                تأكيد الرفض
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Settings Dialog */}
      {showSettingsDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
            <div className="p-4 border-b border-slate-100">
              <h3 className="text-lg font-bold">إعدادات النظام</h3>
            </div>
            <div className="p-4 space-y-4">
              {settings.map((setting) => (
                <div key={setting.key} className="bg-slate-50 rounded-lg p-3">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-medium">{setting.key === 'approval_limit' ? 'حد الموافقة' : setting.key}</p>
                      <p className="text-xs text-slate-500">{setting.description}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type={setting.key === 'approval_limit' ? 'number' : 'text'}
                      defaultValue={setting.value}
                      onBlur={(e) => {
                        if (e.target.value !== setting.value) {
                          updateSetting(setting.key, e.target.value);
                        }
                      }}
                      className="flex-1 px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                    />
                    {setting.key === 'approval_limit' && <span className="text-slate-500">ريال</span>}
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 border-t border-slate-100 flex justify-end">
              <Button onClick={() => setShowSettingsDialog(false)}>إغلاق</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
