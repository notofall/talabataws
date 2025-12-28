import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import {
  Package,
  Plus,
  LogOut,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  RefreshCw,
  Download,
  Eye,
  Edit,
} from "lucide-react";
import { exportRequestToPDF, exportRequestsTableToPDF } from "../utils/pdfExport";

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
  const [formData, setFormData] = useState({
    material_name: "",
    quantity: "",
    project_name: "",
    reason: "",
    engineer_id: "",
  });

  // Edit form state
  const [editFormData, setEditFormData] = useState({
    material_name: "",
    quantity: "",
    project_name: "",
    reason: "",
    engineer_id: "",
  });

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

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.material_name || !formData.quantity || !formData.project_name || !formData.reason || !formData.engineer_id) {
      toast.error("الرجاء إكمال جميع الحقول");
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(
        `${API_URL}/requests`,
        {
          ...formData,
          quantity: parseInt(formData.quantity),
        },
        getAuthHeaders()
      );
      toast.success("تم إنشاء الطلب بنجاح");
      setDialogOpen(false);
      setFormData({
        material_name: "",
        quantity: "",
        project_name: "",
        reason: "",
        engineer_id: "",
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في إنشاء الطلب");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = async (e) => {
    e.preventDefault();
    if (!editFormData.material_name || !editFormData.quantity || !editFormData.project_name || !editFormData.reason || !editFormData.engineer_id) {
      toast.error("الرجاء إكمال جميع الحقول");
      return;
    }

    setSubmitting(true);
    try {
      await axios.put(
        `${API_URL}/requests/${selectedRequest.id}/edit`,
        {
          ...editFormData,
          quantity: parseInt(editFormData.quantity),
        },
        getAuthHeaders()
      );
      toast.success("تم تعديل الطلب بنجاح");
      setEditDialogOpen(false);
      setSelectedRequest(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تعديل الطلب");
    } finally {
      setSubmitting(false);
    }
  };

  const openEditDialog = (request) => {
    setSelectedRequest(request);
    setEditFormData({
      material_name: request.material_name,
      quantity: String(request.quantity),
      project_name: request.project_name,
      reason: request.reason,
      engineer_id: request.engineer_id,
    });
    setEditDialogOpen(true);
  };

  const openViewDialog = (request) => {
    setSelectedRequest(request);
    setViewDialogOpen(true);
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      pending_engineer: { label: "بانتظار المهندس", variant: "warning", icon: Clock },
      approved_by_engineer: { label: "معتمد", variant: "success", icon: CheckCircle },
      rejected_by_engineer: { label: "مرفوض", variant: "destructive", icon: XCircle },
      purchase_order_issued: { label: "تم إصدار أمر الشراء", variant: "default", icon: FileText },
    };

    const statusInfo = statusMap[status] || { label: status, variant: "secondary", icon: Clock };
    const Icon = statusInfo.icon;

    const variantClasses = {
      warning: "bg-yellow-50 text-yellow-800 border-yellow-200",
      success: "bg-green-50 text-green-800 border-green-200",
      destructive: "bg-red-50 text-red-800 border-red-200",
      default: "bg-blue-50 text-blue-800 border-blue-200",
      secondary: "bg-slate-50 text-slate-800 border-slate-200",
    };

    return (
      <Badge className={`${variantClasses[statusInfo.variant]} border flex items-center gap-1 font-medium`}>
        <Icon className="w-3 h-3" />
        {statusInfo.label}
      </Badge>
    );
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString("ar-SA", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-orange-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600 font-medium">جاري التحميل...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-slate-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-orange-600 rounded-sm flex items-center justify-center">
                <Package className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-lg font-bold">نظام طلبات المواد</h1>
                <p className="text-sm text-slate-400">لوحة تحكم المشرف</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-slate-300">مرحباً، {user?.name}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                className="text-slate-300 hover:text-white hover:bg-slate-800"
                data-testid="logout-btn"
              >
                <LogOut className="w-4 h-4 ml-2" />
                خروج
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card className="border-r-4 border-r-orange-500 hover-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-500">إجمالي الطلبات</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-slate-900">{stats.total || 0}</div>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-r-yellow-500 hover-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-500">بانتظار الاعتماد</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-yellow-600">{stats.pending || 0}</div>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-r-green-500 hover-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-500">معتمدة</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{stats.approved || 0}</div>
            </CardContent>
          </Card>
          <Card className="border-r-4 border-r-red-500 hover-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-slate-500">مرفوضة</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-600">{stats.rejected || 0}</div>
            </CardContent>
          </Card>
        </div>

        {/* Actions Bar */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-slate-900">طلباتي</h2>
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => exportRequestsTableToPDF(requests, 'طلباتي')}
              className="border-slate-300"
              disabled={requests.length === 0}
              data-testid="export-all-pdf-btn"
            >
              <Download className="w-4 h-4 ml-2" />
              تصدير PDF
            </Button>
            <Button
              variant="outline"
              onClick={fetchData}
              className="border-slate-300"
              data-testid="refresh-btn"
            >
              <RefreshCw className="w-4 h-4 ml-2" />
              تحديث
            </Button>
            <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
              <DialogTrigger asChild>
                <Button
                  className="bg-orange-600 hover:bg-orange-700 text-white font-bold"
                  data-testid="new-request-btn"
                >
                  <Plus className="w-4 h-4 ml-2" />
                  طلب جديد
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[500px]" dir="rtl">
                <DialogHeader>
                  <DialogTitle className="text-xl font-bold text-center">إنشاء طلب مواد جديد</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                  <div className="space-y-2">
                    <Label htmlFor="material_name">اسم المادة</Label>
                    <Input
                      id="material_name"
                      placeholder="مثال: حديد تسليح 12مم"
                      value={formData.material_name}
                      onChange={(e) => setFormData({ ...formData, material_name: e.target.value })}
                      className="h-11"
                      data-testid="material-name-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="quantity">الكمية</Label>
                    <Input
                      id="quantity"
                      type="number"
                      min="1"
                      placeholder="مثال: 100"
                      value={formData.quantity}
                      onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                      className="h-11"
                      data-testid="quantity-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="project_name">اسم المشروع</Label>
                    <Input
                      id="project_name"
                      placeholder="مثال: مشروع برج السلام"
                      value={formData.project_name}
                      onChange={(e) => setFormData({ ...formData, project_name: e.target.value })}
                      className="h-11"
                      data-testid="project-name-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="reason">سبب الطلب</Label>
                    <Textarea
                      id="reason"
                      placeholder="اذكر سبب طلب هذه المواد..."
                      value={formData.reason}
                      onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                      rows={3}
                      data-testid="reason-input"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="engineer">اختر المهندس</Label>
                    <Select
                      value={formData.engineer_id}
                      onValueChange={(value) => setFormData({ ...formData, engineer_id: value })}
                    >
                      <SelectTrigger className="h-11" data-testid="engineer-select">
                        <SelectValue placeholder="اختر المهندس للاعتماد" />
                      </SelectTrigger>
                      <SelectContent>
                        {engineers.map((eng) => (
                          <SelectItem key={eng.id} value={eng.id} data-testid={`engineer-option-${eng.id}`}>
                            {eng.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <Button
                    type="submit"
                    className="w-full h-12 bg-orange-600 hover:bg-orange-700 text-white font-bold"
                    disabled={submitting}
                    data-testid="submit-request-btn"
                  >
                    {submitting ? (
                      <div className="flex items-center gap-2">
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>جاري الإرسال...</span>
                      </div>
                    ) : (
                      "إرسال الطلب"
                    )}
                  </Button>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Requests Table */}
        <Card className="shadow-sm">
          <CardContent className="p-0">
            {requests.length === 0 ? (
              <div className="text-center py-16">
                <Package className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-slate-600 mb-2">لا توجد طلبات</h3>
                <p className="text-slate-500 mb-4">ابدأ بإنشاء طلب مواد جديد</p>
                <Button
                  onClick={() => setDialogOpen(true)}
                  className="bg-orange-600 hover:bg-orange-700 text-white"
                >
                  <Plus className="w-4 h-4 ml-2" />
                  إنشاء طلب
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50">
                    <TableHead className="text-right font-bold">اسم المادة</TableHead>
                    <TableHead className="text-right font-bold">الكمية</TableHead>
                    <TableHead className="text-right font-bold">المشروع</TableHead>
                    <TableHead className="text-right font-bold">المهندس</TableHead>
                    <TableHead className="text-right font-bold">الحالة</TableHead>
                    <TableHead className="text-right font-bold">التاريخ</TableHead>
                    <TableHead className="text-right font-bold">الإجراءات</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requests.map((request) => (
                    <TableRow key={request.id} className="table-row-hover" data-testid={`request-row-${request.id}`}>
                      <TableCell className="font-medium">{request.material_name}</TableCell>
                      <TableCell>{request.quantity}</TableCell>
                      <TableCell>{request.project_name}</TableCell>
                      <TableCell>{request.engineer_name}</TableCell>
                      <TableCell>{getStatusBadge(request.status)}</TableCell>
                      <TableCell className="text-slate-500 text-sm">
                        {formatDate(request.created_at)}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => openViewDialog(request)}
                            className="h-8 w-8 p-0"
                            data-testid={`view-btn-${request.id}`}
                          >
                            <Eye className="w-4 h-4 text-slate-600" />
                          </Button>
                          {request.status === "pending_engineer" && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => openEditDialog(request)}
                              className="h-8 w-8 p-0"
                              data-testid={`edit-btn-${request.id}`}
                            >
                              <Edit className="w-4 h-4 text-blue-600" />
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => exportRequestToPDF(request)}
                            className="h-8 w-8 p-0"
                            data-testid={`export-btn-${request.id}`}
                          >
                            <Download className="w-4 h-4 text-green-600" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>

      {/* View Request Dialog */}
      <Dialog open={viewDialogOpen} onOpenChange={setViewDialogOpen}>
        <DialogContent className="sm:max-w-[500px]" dir="rtl">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-center">تفاصيل الطلب</DialogTitle>
          </DialogHeader>
          {selectedRequest && (
            <div className="space-y-4 mt-4">
              <div className="bg-slate-50 p-4 rounded-lg space-y-3">
                <div className="flex justify-between">
                  <span className="text-slate-500">اسم المادة:</span>
                  <span className="font-semibold">{selectedRequest.material_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">الكمية:</span>
                  <span className="font-semibold">{selectedRequest.quantity}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">المشروع:</span>
                  <span className="font-semibold">{selectedRequest.project_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">المهندس:</span>
                  <span className="font-semibold">{selectedRequest.engineer_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">الحالة:</span>
                  {getStatusBadge(selectedRequest.status)}
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">التاريخ:</span>
                  <span className="font-semibold">{formatDate(selectedRequest.created_at)}</span>
                </div>
                <div className="pt-2 border-t">
                  <span className="text-slate-500 block mb-1">سبب الطلب:</span>
                  <p className="font-medium">{selectedRequest.reason}</p>
                </div>
                {selectedRequest.rejection_reason && (
                  <div className="pt-2 border-t bg-red-50 p-3 rounded">
                    <span className="text-red-600 block mb-1">سبب الرفض:</span>
                    <p className="font-medium text-red-800">{selectedRequest.rejection_reason}</p>
                  </div>
                )}
              </div>
              <Button
                className="w-full bg-green-600 hover:bg-green-700 text-white"
                onClick={() => exportRequestToPDF(selectedRequest)}
              >
                <Download className="w-4 h-4 ml-2" />
                تصدير PDF
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Edit Request Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-[500px]" dir="rtl">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-center">تعديل الطلب</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEdit} className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label htmlFor="edit_material_name">اسم المادة</Label>
              <Input
                id="edit_material_name"
                value={editFormData.material_name}
                onChange={(e) => setEditFormData({ ...editFormData, material_name: e.target.value })}
                className="h-11"
                data-testid="edit-material-name-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit_quantity">الكمية</Label>
              <Input
                id="edit_quantity"
                type="number"
                min="1"
                value={editFormData.quantity}
                onChange={(e) => setEditFormData({ ...editFormData, quantity: e.target.value })}
                className="h-11"
                data-testid="edit-quantity-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit_project_name">اسم المشروع</Label>
              <Input
                id="edit_project_name"
                value={editFormData.project_name}
                onChange={(e) => setEditFormData({ ...editFormData, project_name: e.target.value })}
                className="h-11"
                data-testid="edit-project-name-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit_reason">سبب الطلب</Label>
              <Textarea
                id="edit_reason"
                value={editFormData.reason}
                onChange={(e) => setEditFormData({ ...editFormData, reason: e.target.value })}
                rows={3}
                data-testid="edit-reason-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit_engineer">المهندس</Label>
              <Select
                value={editFormData.engineer_id}
                onValueChange={(value) => setEditFormData({ ...editFormData, engineer_id: value })}
              >
                <SelectTrigger className="h-11" data-testid="edit-engineer-select">
                  <SelectValue placeholder="اختر المهندس" />
                </SelectTrigger>
                <SelectContent>
                  {engineers.map((eng) => (
                    <SelectItem key={eng.id} value={eng.id}>
                      {eng.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              type="submit"
              className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-bold"
              disabled={submitting}
              data-testid="save-edit-btn"
            >
              {submitting ? "جاري الحفظ..." : "حفظ التعديلات"}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default SupervisorDashboard;
