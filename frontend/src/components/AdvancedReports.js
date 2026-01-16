import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Label } from "../components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { 
  BarChart3, TrendingUp, Users, Package, DollarSign, 
  RefreshCw, Calendar, Building2, Truck, CheckCircle2, 
  XCircle, Clock, PieChart, Download, FileSpreadsheet, FileText, Filter
} from "lucide-react";

export default function AdvancedReports({ onClose }) {
  const { API_URL, getAuthHeaders } = useAuth();
  const [loading, setLoading] = useState(true);
  const [summaryReport, setSummaryReport] = useState(null);
  const [approvalReport, setApprovalReport] = useState(null);
  const [supplierReport, setSupplierReport] = useState(null);
  const [priceVarianceReport, setPriceVarianceReport] = useState(null);  // New state for price variance
  
  // Filter options data
  const [projects, setProjects] = useState([]);
  const [engineers, setEngineers] = useState([]);
  const [supervisors, setSupervisors] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  
  // Active filters
  const [filters, setFilters] = useState({
    project_id: "",
    engineer_id: "",
    supervisor_id: "",
    supplier_id: "",
    start_date: "",
    end_date: "",
    item_name: ""  // New filter for item name
  });

  // Fetch filter options
  const fetchFilterOptions = useCallback(async () => {
    try {
      const [projectsRes, usersRes, suppliersRes] = await Promise.all([
        axios.get(`${API_URL}/projects`, getAuthHeaders()),
        axios.get(`${API_URL}/users/list`, getAuthHeaders()),
        axios.get(`${API_URL}/suppliers`, getAuthHeaders())
      ]);
      
      setProjects(projectsRes.data || []);
      setSuppliers(suppliersRes.data || []);
      
      // Filter users by role
      const users = usersRes.data || [];
      setEngineers(users.filter(u => u.role === "engineer"));
      setSupervisors(users.filter(u => u.role === "supervisor"));
    } catch (error) {
      console.error("Error fetching filter options:", error);
    }
  }, [API_URL, getAuthHeaders]);

  const fetchReports = useCallback(async () => {
    setLoading(true);
    try {
      // Build query params
      const params = new URLSearchParams();
      if (filters.project_id) params.append("project_id", filters.project_id);
      if (filters.engineer_id) params.append("engineer_id", filters.engineer_id);
      if (filters.supervisor_id) params.append("supervisor_id", filters.supervisor_id);
      if (filters.supplier_id) params.append("supplier_id", filters.supplier_id);
      if (filters.start_date) params.append("start_date", filters.start_date);
      if (filters.end_date) params.append("end_date", filters.end_date);
      if (filters.item_name) params.append("item_name", filters.item_name);
      
      const queryString = params.toString() ? `?${params.toString()}` : "";
      
      const [summaryRes, approvalRes, supplierRes, priceVarianceRes] = await Promise.all([
        axios.get(`${API_URL}/reports/advanced/summary${queryString}`, getAuthHeaders()),
        axios.get(`${API_URL}/reports/advanced/approval-analytics${queryString}`, getAuthHeaders()),
        axios.get(`${API_URL}/reports/advanced/supplier-performance${queryString}`, getAuthHeaders()),
        axios.get(`${API_URL}/reports/advanced/price-variance${queryString}`, getAuthHeaders())
      ]);
      
      setSummaryReport(summaryRes.data);
      setApprovalReport(approvalRes.data);
      setSupplierReport(supplierRes.data);
      setPriceVarianceReport(priceVarianceRes.data);
    } catch (error) {
      console.error("Error fetching reports:", error);
      toast.error("فشل في تحميل التقارير");
    } finally {
      setLoading(false);
    }
  }, [API_URL, getAuthHeaders, filters]);

  useEffect(() => {
    fetchFilterOptions();
  }, [fetchFilterOptions]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ar-SA', { 
      style: 'currency', 
      currency: 'SAR',
      maximumFractionDigits: 0 
    }).format(amount || 0);
  };

  const clearFilters = () => {
    setFilters({
      project_id: "",
      engineer_id: "",
      supervisor_id: "",
      supplier_id: "",
      start_date: "",
      end_date: ""
    });
  };

  // Export to Excel
  const exportToExcel = async (reportType) => {
    try {
      toast.info("جاري تصدير التقرير...");
      
      const params = new URLSearchParams();
      if (filters.project_id) params.append("project_id", filters.project_id);
      if (filters.engineer_id) params.append("engineer_id", filters.engineer_id);
      if (filters.supervisor_id) params.append("supervisor_id", filters.supervisor_id);
      if (filters.supplier_id) params.append("supplier_id", filters.supplier_id);
      params.append("format", "excel");
      
      const response = await axios.get(
        `${API_URL}/reports/advanced/${reportType}/export?${params.toString()}`,
        {
          ...getAuthHeaders(),
          responseType: 'blob'
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `تقرير_${reportType}_${new Date().toLocaleDateString('ar-SA')}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success("تم تصدير التقرير بنجاح");
    } catch (error) {
      console.error("Export error:", error);
      toast.error("فشل في تصدير التقرير");
    }
  };

  // Export to PDF
  const exportToPDF = (reportType) => {
    try {
      let content = "";
      const now = new Date().toLocaleString('ar-SA');
      
      // Get active filter names
      const activeFilters = [];
      if (filters.project_id) {
        const project = projects.find(p => p.id === filters.project_id);
        if (project) activeFilters.push(`المشروع: ${project.name}`);
      }
      if (filters.engineer_id) {
        const engineer = engineers.find(e => e.id === filters.engineer_id);
        if (engineer) activeFilters.push(`المهندس: ${engineer.name}`);
      }
      if (filters.supervisor_id) {
        const supervisor = supervisors.find(s => s.id === filters.supervisor_id);
        if (supervisor) activeFilters.push(`المشرف: ${supervisor.name}`);
      }
      if (filters.supplier_id) {
        const supplier = suppliers.find(s => s.id === filters.supplier_id);
        if (supplier) activeFilters.push(`المورد: ${supplier.name}`);
      }
      
      const filterText = activeFilters.length > 0 ? activeFilters.join(" | ") : "جميع البيانات";
      
      if (reportType === "summary" && summaryReport) {
        content = `
          <html dir="rtl">
          <head>
            <meta charset="UTF-8">
            <style>
              body { font-family: 'Segoe UI', Tahoma, sans-serif; padding: 20px; direction: rtl; margin-top: 50px; }
              h1 { color: #ea580c; border-bottom: 2px solid #ea580c; padding-bottom: 10px; }
              h2 { color: #334155; margin-top: 30px; }
              .filter-info { background: #f1f5f9; padding: 10px; border-radius: 8px; margin-bottom: 20px; }
              .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
              .stat-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; text-align: center; }
              .stat-value { font-size: 24px; font-weight: bold; color: #ea580c; }
              .stat-label { font-size: 12px; color: #64748b; }
              table { width: 100%; border-collapse: collapse; margin-top: 15px; }
              th, td { border: 1px solid #e2e8f0; padding: 10px; text-align: right; }
              th { background: #f1f5f9; font-weight: bold; }
              .footer { margin-top: 30px; text-align: center; color: #94a3b8; font-size: 12px; }
              .btn-container { position: fixed; top: 0; left: 0; right: 0; background: linear-gradient(to bottom, rgba(255,255,255,0.98) 0%, rgba(255,255,255,0.9) 70%, transparent 100%); padding: 15px; z-index: 999; display: flex; gap: 10px; }
              .print-btn { background: #ea580c; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; }
              .print-btn:hover { background: #c2410c; }
              .close-btn { background: #64748b; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; }
              .close-btn:hover { background: #475569; }
              @media print { .btn-container { display: none !important; } body { margin-top: 0; } }
            </style>
          </head>
          <body>
            <div class="btn-container">
              <button class="print-btn" onclick="window.print()">🖨️ طباعة / حفظ PDF</button>
              <button class="close-btn" onclick="window.close()">✕ إغلاق</button>
            </div>
            <h1>📊 الملخص التنفيذي</h1>
            <div class="filter-info">
              <strong>الفلاتر:</strong> ${filterText}<br>
              <strong>تاريخ التقرير:</strong> ${now}
            </div>
            
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-value">${summaryReport.summary.total_requests}</div>
                <div class="stat-label">إجمالي الطلبات</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${summaryReport.summary.total_orders}</div>
                <div class="stat-label">أوامر الشراء</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${formatCurrency(summaryReport.summary.total_spending)}</div>
                <div class="stat-label">إجمالي المصروفات</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${summaryReport.summary.approved_orders}</div>
                <div class="stat-label">معتمدة</div>
              </div>
            </div>
            
            <h2>🏢 أكثر المشاريع إنفاقاً</h2>
            <table>
              <tr><th>#</th><th>المشروع</th><th>المبلغ</th></tr>
              ${summaryReport.top_projects?.map((p, i) => `<tr><td>${i+1}</td><td>${p.name}</td><td>${formatCurrency(p.amount)}</td></tr>`).join('') || '<tr><td colspan="3">لا توجد بيانات</td></tr>'}
            </table>
            
            <h2>🚚 أكثر الموردين تعاملاً</h2>
            <table>
              <tr><th>#</th><th>المورد</th><th>عدد الطلبات</th><th>المبلغ</th></tr>
              ${summaryReport.top_suppliers?.map((s, i) => `<tr><td>${i+1}</td><td>${s.name}</td><td>${s.orders}</td><td>${formatCurrency(s.amount)}</td></tr>`).join('') || '<tr><td colspan="4">لا توجد بيانات</td></tr>'}
            </table>
            
            <h2>📁 المصروفات حسب التصنيف</h2>
            <table>
              <tr><th>التصنيف</th><th>المبلغ</th></tr>
              ${summaryReport.spending_by_category?.map(c => `<tr><td>${c.name}</td><td>${formatCurrency(c.amount)}</td></tr>`).join('') || '<tr><td colspan="2">لا توجد بيانات</td></tr>'}
            </table>
            
            <div class="footer">تم إنشاء هذا التقرير بواسطة نظام إدارة طلبات المواد</div>
          </body>
          </html>
        `;
      } else if (reportType === "approvals" && approvalReport) {
        content = `
          <html dir="rtl">
          <head>
            <meta charset="UTF-8">
            <style>
              body { font-family: 'Segoe UI', Tahoma, sans-serif; padding: 20px; direction: rtl; margin-top: 50px; }
              h1 { color: #ea580c; border-bottom: 2px solid #ea580c; padding-bottom: 10px; }
              h2 { color: #334155; margin-top: 30px; }
              .filter-info { background: #f1f5f9; padding: 10px; border-radius: 8px; margin-bottom: 20px; }
              .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
              .stat-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; text-align: center; }
              .stat-value { font-size: 24px; font-weight: bold; }
              .btn-container { position: fixed; top: 0; left: 0; right: 0; background: linear-gradient(to bottom, rgba(255,255,255,0.98) 0%, rgba(255,255,255,0.9) 70%, transparent 100%); padding: 15px; z-index: 999; display: flex; gap: 10px; }
              .print-btn { background: #ea580c; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; }
              .print-btn:hover { background: #c2410c; }
              .close-btn { background: #64748b; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; }
              .close-btn:hover { background: #475569; }
              @media print { .btn-container { display: none !important; } body { margin-top: 0; } }
              .stat-label { font-size: 12px; color: #64748b; }
              .green { color: #16a34a; }
              .red { color: #dc2626; }
              .yellow { color: #ca8a04; }
              table { width: 100%; border-collapse: collapse; margin-top: 15px; }
              th, td { border: 1px solid #e2e8f0; padding: 10px; text-align: right; }
              th { background: #f1f5f9; font-weight: bold; }
              .footer { margin-top: 30px; text-align: center; color: #94a3b8; font-size: 12px; }
            </style>
          </head>
          <body>
            <div class="btn-container">
              <button class="print-btn" onclick="window.print()">🖨️ طباعة / حفظ PDF</button>
              <button class="close-btn" onclick="window.close()">✕ إغلاق</button>
            </div>
            <h1>✅ تحليل الاعتمادات</h1>
            <div class="filter-info">
              <strong>الفلاتر:</strong> ${filterText}<br>
              <strong>تاريخ التقرير:</strong> ${now}
            </div>
            
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-value">${approvalReport.summary.total_requests}</div>
                <div class="stat-label">إجمالي الطلبات</div>
              </div>
              <div class="stat-card">
                <div class="stat-value green">${approvalReport.summary.approved}</div>
                <div class="stat-label">معتمدة (${approvalReport.summary.approval_rate}%)</div>
              </div>
              <div class="stat-card">
                <div class="stat-value red">${approvalReport.summary.rejected}</div>
                <div class="stat-label">مرفوضة (${approvalReport.summary.rejection_rate}%)</div>
              </div>
              <div class="stat-card">
                <div class="stat-value yellow">${approvalReport.summary.pending}</div>
                <div class="stat-label">معلقة</div>
              </div>
            </div>
            
            <h2>👷 حسب المهندس</h2>
            <table>
              <tr><th>المهندس</th><th>الإجمالي</th><th>معتمدة</th><th>مرفوضة</th><th>معلقة</th></tr>
              ${approvalReport.by_engineer?.map(e => `<tr><td>${e.name}</td><td>${e.total}</td><td class="green">${e.approved}</td><td class="red">${e.rejected}</td><td class="yellow">${e.pending}</td></tr>`).join('') || '<tr><td colspan="5">لا توجد بيانات</td></tr>'}
            </table>
            
            <h2>👨‍💼 حسب المشرف</h2>
            <table>
              <tr><th>المشرف</th><th>الإجمالي</th><th>معتمدة</th><th>مرفوضة</th><th>معلقة</th></tr>
              ${approvalReport.by_supervisor?.map(s => `<tr><td>${s.name}</td><td>${s.total}</td><td class="green">${s.approved}</td><td class="red">${s.rejected}</td><td class="yellow">${s.pending}</td></tr>`).join('') || '<tr><td colspan="5">لا توجد بيانات</td></tr>'}
            </table>
            
            <h2>🏢 حسب المشروع</h2>
            <table>
              <tr><th>المشروع</th><th>الإجمالي</th><th>معتمدة</th><th>مرفوضة</th><th>معلقة</th></tr>
              ${approvalReport.by_project?.map(p => `<tr><td>${p.name}</td><td>${p.total}</td><td class="green">${p.approved}</td><td class="red">${p.rejected}</td><td class="yellow">${p.pending}</td></tr>`).join('') || '<tr><td colspan="5">لا توجد بيانات</td></tr>'}
            </table>
            
            <div class="footer">تم إنشاء هذا التقرير بواسطة نظام إدارة طلبات المواد</div>
          </body>
          </html>
        `;
      } else if (reportType === "suppliers" && supplierReport) {
        content = `
          <html dir="rtl">
          <head>
            <meta charset="UTF-8">
            <style>
              body { font-family: 'Segoe UI', Tahoma, sans-serif; padding: 20px; direction: rtl; margin-top: 50px; }
              h1 { color: #ea580c; border-bottom: 2px solid #ea580c; padding-bottom: 10px; }
              .filter-info { background: #f1f5f9; padding: 10px; border-radius: 8px; margin-bottom: 20px; }
              .stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }
              .stat-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; text-align: center; }
              .stat-value { font-size: 24px; font-weight: bold; color: #ea580c; }
              .stat-label { font-size: 12px; color: #64748b; }
              table { width: 100%; border-collapse: collapse; margin-top: 15px; }
              th, td { border: 1px solid #e2e8f0; padding: 10px; text-align: right; }
              th { background: #f1f5f9; font-weight: bold; }
              .footer { margin-top: 30px; text-align: center; color: #94a3b8; font-size: 12px; }
              .btn-container { position: fixed; top: 0; left: 0; right: 0; background: linear-gradient(to bottom, rgba(255,255,255,0.98) 0%, rgba(255,255,255,0.9) 70%, transparent 100%); padding: 15px; z-index: 999; display: flex; gap: 10px; }
              .print-btn { background: #ea580c; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; }
              .print-btn:hover { background: #c2410c; }
              .close-btn { background: #64748b; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; }
              .close-btn:hover { background: #475569; }
              @media print { .btn-container { display: none !important; } body { margin-top: 0; } }
            </style>
          </head>
          <body>
            <div class="btn-container">
              <button class="print-btn" onclick="window.print()">🖨️ طباعة / حفظ PDF</button>
              <button class="close-btn" onclick="window.close()">✕ إغلاق</button>
            </div>
            <h1>🚚 تقرير أداء الموردين</h1>
            <div class="filter-info">
              <strong>الفلاتر:</strong> ${filterText}<br>
              <strong>تاريخ التقرير:</strong> ${now}
            </div>
            
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-value">${supplierReport.summary.total_suppliers}</div>
                <div class="stat-label">عدد الموردين</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${supplierReport.summary.total_orders}</div>
                <div class="stat-label">إجمالي الطلبات</div>
              </div>
              <div class="stat-card">
                <div class="stat-value">${formatCurrency(supplierReport.summary.total_spending)}</div>
                <div class="stat-label">إجمالي المشتريات</div>
              </div>
            </div>
            
            <h2>📋 تفاصيل الموردين</h2>
            <table>
              <tr>
                <th>المورد</th>
                <th>جهة الاتصال</th>
                <th>الطلبات</th>
                <th>المكتملة</th>
                <th>نسبة الإكمال</th>
                <th>إجمالي المشتريات</th>
                <th>متوسط الطلب</th>
              </tr>
              ${supplierReport.suppliers?.map(s => `
                <tr>
                  <td>${s.supplier_name}</td>
                  <td>${s.contact_person || '-'}</td>
                  <td>${s.total_orders}</td>
                  <td>${s.completed_orders}</td>
                  <td>${s.completion_rate}%</td>
                  <td>${formatCurrency(s.total_amount)}</td>
                  <td>${formatCurrency(s.avg_order_value)}</td>
                </tr>
              `).join('') || '<tr><td colspan="7">لا توجد بيانات</td></tr>'}
            </table>
            
            <div class="footer">تم إنشاء هذا التقرير بواسطة نظام إدارة طلبات المواد</div>
          </body>
          </html>
        `;
      }
      
      const printWindow = window.open('', '_blank');
      printWindow.document.write(content);
      printWindow.document.close();
      printWindow.print();
      
      toast.success("تم فتح نافذة الطباعة");
    } catch (error) {
      console.error("PDF export error:", error);
      toast.error("فشل في تصدير التقرير");
    }
  };

  const hasActiveFilters = Object.values(filters).some(v => v !== "");

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-8 w-8 animate-spin text-orange-500" />
        <span className="mr-3 text-slate-600">جاري تحميل التقارير...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6" dir="rtl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <BarChart3 className="h-7 w-7 text-orange-500" />
            التقارير المتقدمة
          </h2>
          <p className="text-slate-500 mt-1">تحليلات شاملة للمشاريع والمصروفات</p>
        </div>
        <Button variant="outline" onClick={fetchReports} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ml-2 ${loading ? 'animate-spin' : ''}`} />
          تحديث
        </Button>
      </div>

      {/* Filters Section */}
      <Card className="bg-slate-50 border-slate-200">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Filter className="h-5 w-5 text-slate-600" />
            <span className="font-medium text-slate-700">الفلاتر</span>
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters} className="text-red-500 hover:text-red-700 mr-auto">
                <XCircle className="h-4 w-4 ml-1" /> مسح الفلاتر
              </Button>
            )}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Project Filter */}
            <div>
              <Label className="text-xs text-slate-600">المشروع</Label>
              <select
                value={filters.project_id}
                onChange={(e) => setFilters(prev => ({ ...prev, project_id: e.target.value }))}
                className="w-full h-9 border rounded-lg bg-white px-2 text-sm"
              >
                <option value="">الكل</option>
                {projects.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            
            {/* Engineer Filter */}
            <div>
              <Label className="text-xs text-slate-600">المهندس</Label>
              <select
                value={filters.engineer_id}
                onChange={(e) => setFilters(prev => ({ ...prev, engineer_id: e.target.value }))}
                className="w-full h-9 border rounded-lg bg-white px-2 text-sm"
              >
                <option value="">الكل</option>
                {engineers.map(e => (
                  <option key={e.id} value={e.id}>{e.name}</option>
                ))}
              </select>
            </div>
            
            {/* Supervisor Filter */}
            <div>
              <Label className="text-xs text-slate-600">المشرف</Label>
              <select
                value={filters.supervisor_id}
                onChange={(e) => setFilters(prev => ({ ...prev, supervisor_id: e.target.value }))}
                className="w-full h-9 border rounded-lg bg-white px-2 text-sm"
              >
                <option value="">الكل</option>
                {supervisors.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            
            {/* Supplier Filter */}
            <div>
              <Label className="text-xs text-slate-600">المورد</Label>
              <select
                value={filters.supplier_id}
                onChange={(e) => setFilters(prev => ({ ...prev, supplier_id: e.target.value }))}
                className="w-full h-9 border rounded-lg bg-white px-2 text-sm"
              >
                <option value="">الكل</option>
                {suppliers.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            
            {/* Item Name Filter */}
            <div>
              <Label className="text-xs text-slate-600">اسم الصنف</Label>
              <input
                type="text"
                value={filters.item_name}
                onChange={(e) => setFilters(prev => ({ ...prev, item_name: e.target.value }))}
                placeholder="بحث عن صنف..."
                className="w-full h-9 border rounded-lg bg-white px-2 text-sm"
              />
            </div>
            
            {/* Start Date */}
            <div>
              <Label className="text-xs text-slate-600">من تاريخ</Label>
              <input
                type="date"
                value={filters.start_date}
                onChange={(e) => setFilters(prev => ({ ...prev, start_date: e.target.value }))}
                className="w-full h-9 border rounded-lg bg-white px-2 text-sm"
              />
            </div>
            
            {/* End Date */}
            <div>
              <Label className="text-xs text-slate-600">إلى تاريخ</Label>
              <input
                type="date"
                value={filters.end_date}
                onChange={(e) => setFilters(prev => ({ ...prev, end_date: e.target.value }))}
                className="w-full h-9 border rounded-lg bg-white px-2 text-sm"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="summary" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="summary" className="gap-2">
            <PieChart className="h-4 w-4" /> الملخص التنفيذي
          </TabsTrigger>
          <TabsTrigger value="approvals" className="gap-2">
            <CheckCircle2 className="h-4 w-4" /> تحليل الاعتمادات
          </TabsTrigger>
          <TabsTrigger value="suppliers" className="gap-2">
            <Truck className="h-4 w-4" /> أداء الموردين
          </TabsTrigger>
          <TabsTrigger value="price-variance" className="gap-2">
            <TrendingUp className="h-4 w-4" /> اختلاف الأسعار
          </TabsTrigger>
        </TabsList>

        {/* Summary Tab */}
        <TabsContent value="summary" className="space-y-4">
          {summaryReport && (
            <>
              {/* Export Buttons */}
              <div className="flex justify-end gap-2">
                <Button variant="outline" size="sm" onClick={() => exportToPDF("summary")}>
                  <FileText className="h-4 w-4 ml-1" /> تصدير PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => exportToExcel("summary")}>
                  <FileSpreadsheet className="h-4 w-4 ml-1" /> تصدير Excel
                </Button>
              </div>
              
              {/* Key Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="border-r-4 border-blue-500">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <Package className="h-8 w-8 text-blue-500" />
                      <div>
                        <p className="text-xs text-slate-500">إجمالي الطلبات</p>
                        <p className="text-2xl font-bold">{summaryReport.summary.total_requests}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card className="border-r-4 border-green-500">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="h-8 w-8 text-green-500" />
                      <div>
                        <p className="text-xs text-slate-500">أوامر الشراء</p>
                        <p className="text-2xl font-bold">{summaryReport.summary.total_orders}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card className="border-r-4 border-orange-500">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <DollarSign className="h-8 w-8 text-orange-500" />
                      <div>
                        <p className="text-xs text-slate-500">إجمالي المصروفات</p>
                        <p className="text-xl font-bold">{formatCurrency(summaryReport.summary.total_spending)}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
                
                <Card className="border-r-4 border-purple-500">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <TrendingUp className="h-8 w-8 text-purple-500" />
                      <div>
                        <p className="text-xs text-slate-500">معتمدة</p>
                        <p className="text-2xl font-bold text-green-600">{summaryReport.summary.approved_orders}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Monthly Spending Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Calendar className="h-5 w-5" />
                    المصروفات الشهرية (آخر 6 أشهر)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {summaryReport.monthly_spending?.map((month, idx) => {
                      const maxAmount = Math.max(...summaryReport.monthly_spending.map(m => m.amount)) || 1;
                      const percentage = (month.amount / maxAmount) * 100;
                      return (
                        <div key={idx} className="flex items-center gap-3">
                          <span className="w-24 text-sm text-slate-600">{month.month}</span>
                          <div className="flex-1 bg-slate-100 rounded-full h-6 overflow-hidden">
                            <div 
                              className="bg-gradient-to-l from-orange-400 to-orange-600 h-full rounded-full transition-all duration-500 flex items-center justify-end px-2"
                              style={{ width: `${Math.max(percentage, 5)}%` }}
                            >
                              {percentage > 20 && (
                                <span className="text-xs text-white font-medium">
                                  {formatCurrency(month.amount)}
                                </span>
                              )}
                            </div>
                          </div>
                          {percentage <= 20 && (
                            <span className="text-sm text-slate-600 w-28 text-left">
                              {formatCurrency(month.amount)}
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Top Projects & Suppliers */}
              <div className="grid md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Building2 className="h-5 w-5" />
                      أكثر المشاريع إنفاقاً
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {summaryReport.top_projects?.length > 0 ? (
                      <div className="space-y-3">
                        {summaryReport.top_projects.map((project, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                            <div className="flex items-center gap-3">
                              <span className="w-6 h-6 bg-orange-100 text-orange-600 rounded-full flex items-center justify-center text-sm font-bold">
                                {idx + 1}
                              </span>
                              <span className="font-medium">{project.name}</span>
                            </div>
                            <Badge variant="outline" className="text-green-600">
                              {formatCurrency(project.amount)}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-center text-slate-500 py-4">لا توجد بيانات</p>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Truck className="h-5 w-5" />
                      أكثر الموردين تعاملاً
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {summaryReport.top_suppliers?.length > 0 ? (
                      <div className="space-y-3">
                        {summaryReport.top_suppliers.map((supplier, idx) => (
                          <div key={idx} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                            <div className="flex items-center gap-3">
                              <span className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-bold">
                                {idx + 1}
                              </span>
                              <div>
                                <span className="font-medium block">{supplier.name}</span>
                                <span className="text-xs text-slate-500">{supplier.orders} طلب</span>
                              </div>
                            </div>
                            <Badge variant="outline" className="text-green-600">
                              {formatCurrency(supplier.amount)}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-center text-slate-500 py-4">لا توجد بيانات</p>
                    )}
                  </CardContent>
                </Card>
              </div>

              {/* Spending by Category */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <PieChart className="h-5 w-5" />
                    المصروفات حسب التصنيف
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {summaryReport.spending_by_category?.length > 0 ? (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                      {summaryReport.spending_by_category.map((cat, idx) => (
                        <div key={idx} className="p-3 bg-gradient-to-br from-slate-50 to-slate-100 rounded-lg border">
                          <p className="font-medium text-slate-700">{cat.name}</p>
                          <p className="text-lg font-bold text-orange-600">{formatCurrency(cat.amount)}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-slate-500 py-4">لا توجد بيانات</p>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        {/* Approvals Tab */}
        <TabsContent value="approvals" className="space-y-4">
          {approvalReport && (
            <>
              {/* Export Buttons */}
              <div className="flex justify-end gap-2">
                <Button variant="outline" size="sm" onClick={() => exportToPDF("approvals")}>
                  <FileText className="h-4 w-4 ml-1" /> تصدير PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => exportToExcel("approval-analytics")}>
                  <FileSpreadsheet className="h-4 w-4 ml-1" /> تصدير Excel
                </Button>
              </div>
              
              {/* Approval Summary */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="border-r-4 border-blue-500">
                  <CardContent className="p-4 text-center">
                    <p className="text-3xl font-bold">{approvalReport.summary.total_requests}</p>
                    <p className="text-sm text-slate-500">إجمالي الطلبات</p>
                  </CardContent>
                </Card>
                <Card className="border-r-4 border-green-500">
                  <CardContent className="p-4 text-center">
                    <p className="text-3xl font-bold text-green-600">{approvalReport.summary.approved}</p>
                    <p className="text-sm text-slate-500">معتمدة</p>
                    <Badge className="mt-1 bg-green-100 text-green-700">{approvalReport.summary.approval_rate}%</Badge>
                  </CardContent>
                </Card>
                <Card className="border-r-4 border-red-500">
                  <CardContent className="p-4 text-center">
                    <p className="text-3xl font-bold text-red-600">{approvalReport.summary.rejected}</p>
                    <p className="text-sm text-slate-500">مرفوضة</p>
                    <Badge className="mt-1 bg-red-100 text-red-700">{approvalReport.summary.rejection_rate}%</Badge>
                  </CardContent>
                </Card>
                <Card className="border-r-4 border-yellow-500">
                  <CardContent className="p-4 text-center">
                    <p className="text-3xl font-bold text-yellow-600">{approvalReport.summary.pending}</p>
                    <p className="text-sm text-slate-500">معلقة</p>
                  </CardContent>
                </Card>
              </div>

              {/* By Engineer */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5" />
                    حسب المهندس
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {approvalReport.by_engineer?.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-4 py-2 text-right">المهندس</th>
                            <th className="px-4 py-2 text-center">الإجمالي</th>
                            <th className="px-4 py-2 text-center">معتمدة</th>
                            <th className="px-4 py-2 text-center">مرفوضة</th>
                            <th className="px-4 py-2 text-center">معلقة</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {approvalReport.by_engineer.map((item, idx) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="px-4 py-3 font-medium">{item.name}</td>
                              <td className="px-4 py-3 text-center">{item.total}</td>
                              <td className="px-4 py-3 text-center text-green-600">{item.approved}</td>
                              <td className="px-4 py-3 text-center text-red-600">{item.rejected}</td>
                              <td className="px-4 py-3 text-center text-yellow-600">{item.pending}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-center text-slate-500 py-4">لا توجد بيانات</p>
                  )}
                </CardContent>
              </Card>

              {/* By Supervisor */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Users className="h-5 w-5" />
                    حسب المشرف
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {approvalReport.by_supervisor?.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-4 py-2 text-right">المشرف</th>
                            <th className="px-4 py-2 text-center">الإجمالي</th>
                            <th className="px-4 py-2 text-center">معتمدة</th>
                            <th className="px-4 py-2 text-center">مرفوضة</th>
                            <th className="px-4 py-2 text-center">معلقة</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {approvalReport.by_supervisor.map((item, idx) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="px-4 py-3 font-medium">{item.name}</td>
                              <td className="px-4 py-3 text-center">{item.total}</td>
                              <td className="px-4 py-3 text-center text-green-600">{item.approved}</td>
                              <td className="px-4 py-3 text-center text-red-600">{item.rejected}</td>
                              <td className="px-4 py-3 text-center text-yellow-600">{item.pending}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-center text-slate-500 py-4">لا توجد بيانات</p>
                  )}
                </CardContent>
              </Card>

              {/* By Project */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Building2 className="h-5 w-5" />
                    حسب المشروع
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {approvalReport.by_project?.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-4 py-2 text-right">المشروع</th>
                            <th className="px-4 py-2 text-center">الإجمالي</th>
                            <th className="px-4 py-2 text-center">معتمدة</th>
                            <th className="px-4 py-2 text-center">مرفوضة</th>
                            <th className="px-4 py-2 text-center">معلقة</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {approvalReport.by_project.map((item, idx) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="px-4 py-3 font-medium">{item.name}</td>
                              <td className="px-4 py-3 text-center">{item.total}</td>
                              <td className="px-4 py-3 text-center text-green-600">{item.approved}</td>
                              <td className="px-4 py-3 text-center text-red-600">{item.rejected}</td>
                              <td className="px-4 py-3 text-center text-yellow-600">{item.pending}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-center text-slate-500 py-4">لا توجد بيانات</p>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        {/* Suppliers Tab */}
        <TabsContent value="suppliers" className="space-y-4">
          {supplierReport && (
            <>
              {/* Export Buttons */}
              <div className="flex justify-end gap-2">
                <Button variant="outline" size="sm" onClick={() => exportToPDF("suppliers")}>
                  <FileText className="h-4 w-4 ml-1" /> تصدير PDF
                </Button>
                <Button variant="outline" size="sm" onClick={() => exportToExcel("supplier-performance")}>
                  <FileSpreadsheet className="h-4 w-4 ml-1" /> تصدير Excel
                </Button>
              </div>
              
              {/* Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="border-r-4 border-blue-500">
                  <CardContent className="p-4 text-center">
                    <Truck className="h-8 w-8 mx-auto text-blue-500 mb-2" />
                    <p className="text-3xl font-bold">{supplierReport.summary.total_suppliers}</p>
                    <p className="text-sm text-slate-500">عدد الموردين</p>
                  </CardContent>
                </Card>
                <Card className="border-r-4 border-green-500">
                  <CardContent className="p-4 text-center">
                    <Package className="h-8 w-8 mx-auto text-green-500 mb-2" />
                    <p className="text-3xl font-bold">{supplierReport.summary.total_orders}</p>
                    <p className="text-sm text-slate-500">إجمالي الطلبات</p>
                  </CardContent>
                </Card>
                <Card className="border-r-4 border-orange-500">
                  <CardContent className="p-4 text-center">
                    <DollarSign className="h-8 w-8 mx-auto text-orange-500 mb-2" />
                    <p className="text-xl font-bold">{formatCurrency(supplierReport.summary.total_spending)}</p>
                    <p className="text-sm text-slate-500">إجمالي المشتريات</p>
                  </CardContent>
                </Card>
                <Card className="border-r-4 border-purple-500">
                  <CardContent className="p-4 text-center">
                    <Clock className="h-8 w-8 mx-auto text-purple-500 mb-2" />
                    <p className="text-3xl font-bold">{supplierReport.summary.avg_on_time_rate || 0}%</p>
                    <p className="text-sm text-slate-500">متوسط الالتزام</p>
                  </CardContent>
                </Card>
              </div>

              {/* Suppliers Table with Items */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Truck className="h-5 w-5" />
                    تفاصيل أداء الموردين
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {supplierReport.suppliers?.length > 0 ? (
                    <div className="space-y-6">
                      {supplierReport.suppliers.map((supplier, idx) => (
                        <div key={idx} className="border rounded-lg p-4 bg-slate-50/50">
                          {/* Supplier Header */}
                          <div className="flex items-start justify-between mb-4">
                            <div>
                              <h3 className="text-lg font-bold text-slate-800">{supplier.supplier_name}</h3>
                              <div className="flex gap-4 text-sm text-slate-500 mt-1">
                                {supplier.contact_person && <span>👤 {supplier.contact_person}</span>}
                                {supplier.phone && <span>📞 {supplier.phone}</span>}
                                {supplier.email && <span>✉️ {supplier.email}</span>}
                              </div>
                            </div>
                            <div className="text-left">
                              <p className="text-lg font-bold text-green-600">{formatCurrency(supplier.total_amount)}</p>
                              <p className="text-xs text-slate-500">إجمالي المشتريات</p>
                            </div>
                          </div>
                          
                          {/* Performance Stats */}
                          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
                            <div className="bg-white rounded p-2 text-center border">
                              <p className="text-xl font-bold text-blue-600">{supplier.total_orders}</p>
                              <p className="text-xs text-slate-500">أوامر الشراء</p>
                            </div>
                            <div className="bg-white rounded p-2 text-center border">
                              <p className="text-xl font-bold text-green-600">{supplier.completed_orders}</p>
                              <p className="text-xs text-slate-500">مكتملة</p>
                            </div>
                            <div className="bg-white rounded p-2 text-center border">
                              <p className="text-xl font-bold text-emerald-600">{supplier.on_time_deliveries || 0}</p>
                              <p className="text-xs text-slate-500">في الوقت</p>
                            </div>
                            <div className="bg-white rounded p-2 text-center border">
                              <p className="text-xl font-bold text-red-600">{supplier.late_deliveries || 0}</p>
                              <p className="text-xs text-slate-500">متأخرة</p>
                            </div>
                            <div className="bg-white rounded p-2 text-center border">
                              <Badge className={`text-lg ${supplier.on_time_rate >= 80 ? 'bg-green-100 text-green-700' : supplier.on_time_rate >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                                {supplier.on_time_rate || 0}%
                              </Badge>
                              <p className="text-xs text-slate-500 mt-1">نسبة الالتزام</p>
                            </div>
                          </div>
                          
                          {/* Items Table */}
                          {supplier.items && supplier.items.length > 0 && (
                            <div className="mt-4">
                              <h4 className="font-medium text-sm text-slate-700 mb-2 flex items-center gap-1">
                                <Package className="h-4 w-4" />
                                الأصناف المرتبطة ({supplier.total_items || supplier.items.length})
                              </h4>
                              <div className="overflow-x-auto">
                                <table className="w-full text-xs border rounded">
                                  <thead className="bg-slate-100">
                                    <tr>
                                      <th className="px-2 py-2 text-right">الصنف</th>
                                      <th className="px-2 py-2 text-center">الوحدة</th>
                                      <th className="px-2 py-2 text-center">الكمية</th>
                                      <th className="px-2 py-2 text-center">عدد الطلبات</th>
                                      <th className="px-2 py-2 text-left">أقل سعر</th>
                                      <th className="px-2 py-2 text-left">أعلى سعر</th>
                                      <th className="px-2 py-2 text-left">متوسط السعر</th>
                                      <th className="px-2 py-2 text-left">الإجمالي</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y bg-white">
                                    {supplier.items.slice(0, 10).map((item, itemIdx) => (
                                      <tr key={itemIdx} className="hover:bg-slate-50">
                                        <td className="px-2 py-2 font-medium">{item.name}</td>
                                        <td className="px-2 py-2 text-center text-slate-500">{item.unit}</td>
                                        <td className="px-2 py-2 text-center">{item.total_quantity}</td>
                                        <td className="px-2 py-2 text-center">{item.order_count}</td>
                                        <td className="px-2 py-2 text-left text-green-600">{formatCurrency(item.min_price)}</td>
                                        <td className="px-2 py-2 text-left text-red-600">{formatCurrency(item.max_price)}</td>
                                        <td className="px-2 py-2 text-left text-blue-600">{formatCurrency(item.avg_price)}</td>
                                        <td className="px-2 py-2 text-left font-bold">{formatCurrency(item.total_price)}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                              {supplier.items.length > 10 && (
                                <p className="text-xs text-slate-500 mt-2 text-center">
                                  + {supplier.items.length - 10} صنف آخر
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-slate-500 py-8">لا توجد بيانات موردين</p>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
