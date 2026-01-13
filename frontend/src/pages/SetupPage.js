import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import axios from "axios";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Package, Mail, Lock, User, ArrowLeft, Loader2, CheckCircle, Settings } from "lucide-react";

const SetupPage = () => {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const [setupRequired, setSetupRequired] = useState(false);
  const { login: authLogin, API_URL } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    checkSetupRequired();
  }, []);

  const checkSetupRequired = async () => {
    try {
      const res = await axios.get(`${API_URL}/setup/check`);
      setSetupRequired(res.data.setup_required);
      if (!res.data.setup_required) {
        // Setup already done, redirect to login
        toast.info("تم إعداد النظام مسبقاً");
        navigate("/login");
      }
    } catch (error) {
      toast.error("فشل في التحقق من حالة النظام");
    } finally {
      setChecking(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!name || !email || !password || !confirmPassword) {
      toast.error("الرجاء إكمال جميع البيانات");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("كلمات المرور غير متطابقة");
      return;
    }

    if (password.length < 6) {
      toast.error("كلمة المرور يجب أن تكون 6 أحرف على الأقل");
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/setup/first-admin`, {
        name,
        email,
        password
      });
      
      // Login with the returned token
      localStorage.setItem("token", res.data.access_token);
      localStorage.setItem("user", JSON.stringify(res.data.user));
      
      toast.success("تم إعداد النظام بنجاح! مرحباً بك كمدير نظام");
      window.location.href = "/system-admin";
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في إعداد النظام");
    } finally {
      setLoading(false);
    }
  };

  if (checking) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-orange-900 to-slate-900 flex items-center justify-center p-4">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-orange-500 animate-spin mx-auto mb-4" />
          <p className="text-white">جاري التحقق من حالة النظام...</p>
        </div>
      </div>
    );
  }

  if (!setupRequired) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-orange-900 to-slate-900 flex flex-col items-center justify-center p-4" dir="rtl">
      {/* Logo */}
      <div className="mb-6 text-center">
        <div className="w-16 h-16 bg-orange-600 rounded-xl flex items-center justify-center mx-auto mb-4 shadow-lg">
          <Settings className="w-10 h-10 text-white" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">إعداد نظام إدارة طلبات المواد</h1>
        <p className="text-slate-300 text-sm">قم بإنشاء حساب مدير المشتريات الأول</p>
      </div>

      <Card className="w-full max-w-md shadow-2xl">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">إنشاء حساب المدير</CardTitle>
          <CardDescription>
            هذا الحساب سيكون لديه صلاحيات كاملة لإدارة النظام والمستخدمين
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">الاسم الكامل</Label>
              <div className="relative">
                <Input
                  id="name"
                  type="text"
                  placeholder="أدخل اسمك الكامل"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="pr-10"
                />
                <User className="w-5 h-5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">البريد الإلكتروني</Label>
              <div className="relative">
                <Input
                  id="email"
                  type="email"
                  placeholder="example@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pr-10"
                />
                <Mail className="w-5 h-5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">كلمة المرور</Label>
              <div className="relative">
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pr-10"
                />
                <Lock className="w-5 h-5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">تأكيد كلمة المرور</Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="pr-10"
                />
                <CheckCircle className="w-5 h-5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              </div>
            </div>

            <Button type="submit" className="w-full bg-orange-600 hover:bg-orange-700" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 ml-2 animate-spin" />
                  جاري الإعداد...
                </>
              ) : (
                <>
                  <Settings className="w-4 h-4 ml-2" />
                  إعداد النظام
                </>
              )}
            </Button>
          </form>

          <div className="mt-6 p-3 bg-orange-50 rounded-lg border border-orange-200">
            <p className="text-sm text-orange-800 text-center">
              💡 بعد إنشاء هذا الحساب، ستتمكن من إضافة المستخدمين الآخرين من لوحة التحكم
            </p>
          </div>
        </CardContent>
      </Card>

      <p className="mt-4 text-slate-400 text-sm">
        لديك حساب بالفعل؟{" "}
        <button 
          onClick={() => navigate("/login")}
          className="text-orange-400 hover:text-orange-300"
        >
          سجل دخول
        </button>
      </p>
    </div>
  );
};

export default SetupPage;
