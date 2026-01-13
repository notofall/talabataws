import { useState, useEffect } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { 
  BarChart3, TrendingUp, Users, Package, DollarSign, 
  RefreshCw, Calendar, Building2, Truck, CheckCircle2, 
  XCircle, Clock, AlertTriangle, PieChart
} from "lucide-react";

export default function AdvancedReports({ onClose }) {
  const { API_URL, getAuthHeaders } = useAuth();
  const [loading, setLoading] = useState(true);
  const [summaryReport, setSummaryReport] = useState(null);
  const [approvalReport, setApprovalReport] = useState(null);
  const [supplierReport, setSupplierReport] = useState(null);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const [summaryRes, approvalRes, supplierRes] = await Promise.all([
        axios.get(`${API_URL}/reports/advanced/summary`, getAuthHeaders()),
        axios.get(`${API_URL}/reports/advanced/approval-analytics`, getAuthHeaders()),
        axios.get(`${API_URL}/reports/advanced/supplier-performance`, getAuthHeaders())
      ]);
      
      setSummaryReport(summaryRes.data);
      setApprovalReport(approvalRes.data);
      setSupplierReport(supplierRes.data);
    } catch (error) {
      console.error("Error fetching reports:", error);
      toast.error("فشل في تحميل التقارير");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ar-SA', { 
      style: 'currency', 
      currency: 'SAR',
      maximumFractionDigits: 0 
    }).format(amount || 0);
  };

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
        </TabsList>

        {/* Summary Tab */}
        <TabsContent value="summary" className="space-y-4">
          {summaryReport && (
            <>
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
              {/* Summary Cards */}
              <div className="grid grid-cols-3 gap-4">
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
              </div>

              {/* Suppliers Table */}
              <Card>
                <CardHeader>
                  <CardTitle>تفاصيل أداء الموردين</CardTitle>
                </CardHeader>
                <CardContent>
                  {supplierReport.suppliers?.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="px-4 py-3 text-right">المورد</th>
                            <th className="px-4 py-3 text-right">جهة الاتصال</th>
                            <th className="px-4 py-3 text-center">الطلبات</th>
                            <th className="px-4 py-3 text-center">المكتملة</th>
                            <th className="px-4 py-3 text-center">نسبة الإكمال</th>
                            <th className="px-4 py-3 text-left">إجمالي المشتريات</th>
                            <th className="px-4 py-3 text-left">متوسط الطلب</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {supplierReport.suppliers.map((supplier, idx) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="px-4 py-3">
                                <div className="font-medium">{supplier.supplier_name}</div>
                                <div className="text-xs text-slate-500">{supplier.phone}</div>
                              </td>
                              <td className="px-4 py-3 text-slate-600">{supplier.contact_person || "-"}</td>
                              <td className="px-4 py-3 text-center font-medium">{supplier.total_orders}</td>
                              <td className="px-4 py-3 text-center text-green-600">{supplier.completed_orders}</td>
                              <td className="px-4 py-3 text-center">
                                <Badge className={`${supplier.completion_rate >= 80 ? 'bg-green-100 text-green-700' : supplier.completion_rate >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}`}>
                                  {supplier.completion_rate}%
                                </Badge>
                              </td>
                              <td className="px-4 py-3 text-left font-bold text-green-600">
                                {formatCurrency(supplier.total_amount)}
                              </td>
                              <td className="px-4 py-3 text-left text-slate-600">
                                {formatCurrency(supplier.avg_order_value)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
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
