import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Package, ArrowLeft, Shield, Info, AlertCircle, User, Mail, Lock, Eye, EyeOff, Loader2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

const RegisterPage = () => {
  const navigate = useNavigate();
  const [setupRequired, setSetupRequired] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAdminForm, setShowAdminForm] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  const [adminData, setAdminData] = useState({
    name: 'مدير النظام',
    email: '',
    password: ''
  });

  useEffect(() => {
    // Check if system needs first admin setup
    axios.get(`${API_BASE}/api/pg/setup/check`)
      .then(res => {
        setSetupRequired(res.data.setup_required);
        if (res.data.setup_required) {
          setShowAdminForm(true);
        }
      })
      .catch(() => setSetupRequired(false))
      .finally(() => setLoading(false));
  }, []);

  const handleCreateFirstAdmin = async (e) => {
    e.preventDefault();
    
    if (!adminData.email || !adminData.password || !adminData.name) {
      toast.error('يرجى ملء جميع الحقول');
      return;
    }
    
    if (adminData.password.length < 6) {
      toast.error('كلمة المرور يجب أن تكون 6 أحرف على الأقل');
      return;
    }

    setSubmitting(true);
    
    try {
      const response = await axios.post(`${API_BASE}/api/pg/setup/first-admin`, adminData);
      
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
        localStorage.setItem('user', JSON.stringify(response.data.user));
        
        toast.success('تم إنشاء حساب المدير بنجاح! مرحباً بك');
        
        setTimeout(() => {
          window.location.href = '/';
        }, 1500);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'فشل في إنشاء الحساب');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="w-8 h-8 animate-spin text-orange-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* Right Side - Content */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-md animate-fadeIn">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-600 rounded-sm mb-4">
              <Package className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">نظام إدارة طلبات المواد</h1>
            <p className="text-slate-500">{showAdminForm ? 'إنشاء حساب المدير الأول' : 'إنشاء حساب جديد'}</p>
          </div>

          {/* First Admin Setup Form */}
          {showAdminForm && setupRequired ? (
            <Card className="border-slate-200 shadow-lg">
              <CardHeader className="space-y-1 pb-4">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-2">
                  <CheckCircle2 className="w-8 h-8 text-green-600" />
                </div>
                <CardTitle className="text-xl font-bold text-center">مرحباً بك!</CardTitle>
                <CardDescription className="text-center">
                  هذا نظام جديد. قم بإنشاء حساب المدير الأول للبدء
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateFirstAdmin} className="space-y-4">
                  {/* Name */}
                  <div>
                    <Label className="text-slate-700">الاسم</Label>
                    <div className="relative mt-1">
                      <Input
                        data-testid="admin-name-input"
                        value={adminData.name}
                        onChange={(e) => setAdminData(prev => ({ ...prev, name: e.target.value }))}
                        placeholder="مدير النظام"
                        className="pr-10"
                      />
                      <User className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    </div>
                  </div>
                  
                  {/* Email */}
                  <div>
                    <Label className="text-slate-700">البريد الإلكتروني</Label>
                    <div className="relative mt-1">
                      <Input
                        data-testid="admin-email-input"
                        type="email"
                        value={adminData.email}
                        onChange={(e) => setAdminData(prev => ({ ...prev, email: e.target.value }))}
                        placeholder="admin@company.com"
                        className="pr-10"
                        required
                      />
                      <Mail className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    </div>
                  </div>
                  
                  {/* Password */}
                  <div>
                    <Label className="text-slate-700">كلمة المرور</Label>
                    <div className="relative mt-1">
                      <Input
                        data-testid="admin-password-input"
                        type={showPassword ? 'text' : 'password'}
                        value={adminData.password}
                        onChange={(e) => setAdminData(prev => ({ ...prev, password: e.target.value }))}
                        placeholder="••••••••"
                        className="px-10"
                        required
                      />
                      <Lock className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">يجب أن تكون 6 أحرف على الأقل</p>
                  </div>

                  <Button
                    data-testid="create-admin-btn"
                    type="submit"
                    disabled={submitting}
                    className="w-full h-12 bg-orange-600 hover:bg-orange-700 text-white font-bold text-lg transition-all"
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin ml-2" />
                        جاري الإنشاء...
                      </>
                    ) : (
                      'إنشاء حساب المدير'
                    )}
                  </Button>
                </form>

                <div className="mt-4 text-center">
                  <Button
                    variant="link"
                    className="text-slate-500 text-sm"
                    onClick={() => setShowAdminForm(false)}
                  >
                    لدي حساب بالفعل؟ العودة
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            /* Normal Register Page - Registration Protected */
            <Card className="border-slate-200 shadow-lg">
              <CardHeader className="space-y-1 pb-4">
                <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-2">
                  <Shield className="w-8 h-8 text-orange-600" />
                </div>
                <CardTitle className="text-xl font-bold text-center">التسجيل محمي</CardTitle>
                <CardDescription className="text-center">
                  لأسباب أمنية، لا يمكن التسجيل المباشر في النظام
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Info className="w-5 h-5 text-orange-600 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm text-orange-800 font-medium mb-1">كيفية الحصول على حساب:</p>
                      <ul className="text-sm text-orange-700 space-y-1 list-disc list-inside">
                        <li>تواصل مع مدير المشتريات في مؤسستك</li>
                        <li>سيقوم بإنشاء حسابك وتحديد دورك الوظيفي</li>
                        <li>ستحصل على بيانات الدخول عبر البريد</li>
                      </ul>
                    </div>
                  </div>
                </div>

                {setupRequired && (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="w-5 h-5 text-green-600 mt-0.5 shrink-0" />
                      <div>
                        <p className="text-sm text-green-800 font-medium mb-1">هل أنت المسؤول الأول؟</p>
                        <p className="text-sm text-green-700">
                          هذا نظام جديد! يمكنك إنشاء حساب المدير الأول الآن.
                        </p>
                        <Button 
                          variant="link" 
                          className="p-0 h-auto text-green-700 font-bold text-sm mt-1"
                          onClick={() => setShowAdminForm(true)}
                        >
                          إنشاء حساب المدير الأول →
                        </Button>
                      </div>
                    </div>
                  </div>
                )}

                <Button
                  onClick={() => navigate("/login")}
                  className="w-full h-12 bg-orange-600 hover:bg-orange-700 text-white font-bold text-lg transition-all"
                >
                  <ArrowLeft className="w-5 h-5 ml-2" />
                  العودة لتسجيل الدخول
                </Button>

                <div className="text-center">
                  <p className="text-sm text-slate-500">
                    لديك حساب؟{" "}
                    <Link
                      to="/login"
                      className="text-orange-600 hover:text-orange-700 font-semibold hover:underline"
                    >
                      سجل دخول
                    </Link>
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Left Side - Image */}
      <div
        className="hidden lg:flex flex-1 bg-cover bg-center relative"
        style={{
          backgroundImage:
            "url('https://images.unsplash.com/photo-1644411813513-ad77c1b77581?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwyfHxjb25zdHJ1Y3Rpb24lMjBzaXRlJTIwbW9kZXJuJTIwYXJjaGl0ZWN0dXJlfGVufDB8fHx8MTc2NjkxMzc2NHww&ixlib=rb-4.1.0&q=85')",
        }}
      >
        <div className="absolute inset-0 bg-slate-900/70"></div>
        <div className="relative z-10 flex flex-col items-center justify-center text-white p-12 text-center">
          <h2 className="text-4xl font-bold mb-4">نظام آمن ومنظم</h2>
          <p className="text-xl text-slate-200 max-w-md">
            يتم إدارة المستخدمين مركزياً بواسطة مدير المشتريات لضمان أمان النظام
          </p>
          <div className="mt-8 space-y-4 text-right">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-orange-600 flex items-center justify-center text-lg">
                🔒
              </div>
              <span className="text-lg">تحكم كامل في صلاحيات المستخدمين</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-orange-600 flex items-center justify-center text-lg">
                👥
              </div>
              <span className="text-lg">ربط المشرفين بالمشاريع والمهندسين</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-orange-600 flex items-center justify-center text-lg">
                ✅
              </div>
              <span className="text-lg">تفعيل وتعطيل الحسابات بسهولة</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
