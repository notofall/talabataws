import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Package, Mail, Lock, ArrowLeft, KeyRound } from "lucide-react";
import axios from "axios";

// Changed to PostgreSQL APIs
const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api/pg`;

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [forgotDialogOpen, setForgotDialogOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("الرجاء إدخال البريد الإلكتروني وكلمة المرور");
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      toast.success("تم تسجيل الدخول بنجاح");
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل تسجيل الدخول");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    if (!forgotEmail) {
      toast.error("الرجاء إدخال البريد الإلكتروني");
      return;
    }

    setForgotLoading(true);
    try {
      const response = await axios.post(`${API_URL}/auth/forgot-password`, { email: forgotEmail });
      toast.success(response.data.message);
      if (response.data.temp_password) {
        toast.info(`كلمة المرور الجديدة: ${response.data.temp_password}`, { duration: 10000 });
      }
      setForgotDialogOpen(false);
      setForgotEmail("");
    } catch (error) {
      toast.error(error.response?.data?.detail || "حدث خطأ أثناء استعادة كلمة المرور");
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Right Side - Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-slate-50">
        <div className="w-full max-w-md animate-fadeIn">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-600 rounded-sm mb-4">
              <Package className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">نظام إدارة طلبات المواد</h1>
            <p className="text-slate-500">قم بتسجيل الدخول للمتابعة</p>
          </div>

          <Card className="border-slate-200 shadow-lg">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-2xl font-bold text-center">تسجيل الدخول</CardTitle>
              <CardDescription className="text-center">
                أدخل بياناتك للوصول إلى حسابك
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email" className="text-slate-700 font-medium">
                    البريد الإلكتروني
                  </Label>
                  <div className="relative">
                    <Mail className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <Input
                      id="email"
                      type="email"
                      placeholder="example@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="pr-10 h-12 text-right"
                      data-testid="login-email-input"
                      dir="ltr"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password" className="text-slate-700 font-medium">
                    كلمة المرور
                  </Label>
                  <div className="relative">
                    <Lock className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <Input
                      id="password"
                      type="password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="pr-10 h-12"
                      data-testid="login-password-input"
                    />
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => setForgotDialogOpen(true)}
                    className="text-sm text-orange-600 hover:text-orange-700 hover:underline"
                  >
                    نسيت كلمة المرور؟
                  </button>
                </div>

                <Button
                  type="submit"
                  className="w-full h-12 bg-orange-600 hover:bg-orange-700 text-white font-bold text-lg transition-all active:scale-[0.98]"
                  disabled={loading}
                  data-testid="login-submit-btn"
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>جاري الدخول...</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <ArrowLeft className="w-5 h-5" />
                      <span>دخول</span>
                    </div>
                  )}
                </Button>
              </form>

              <div className="mt-6 text-center">
                <p className="text-slate-600">
                  ليس لديك حساب؟{" "}
                  <Link
                    to="/register"
                    className="text-orange-600 hover:text-orange-700 font-semibold hover:underline"
                    data-testid="register-link"
                  >
                    سجل الآن
                  </Link>
                </p>
              </div>
            </CardContent>
          </Card>
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
          <h2 className="text-4xl font-bold mb-4">إدارة طلبات المواد</h2>
          <p className="text-xl text-slate-200 max-w-md">
            نظام متكامل لإدارة طلبات المواد وأوامر الشراء بين المشرفين والمهندسين ومدير المشتريات
          </p>
          <div className="mt-8 grid grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-3xl font-bold text-orange-500">10+</div>
              <div className="text-slate-300">مشرف</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-orange-500">6+</div>
              <div className="text-slate-300">مهندس</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-orange-500">∞</div>
              <div className="text-slate-300">طلبات</div>
            </div>
          </div>
        </div>
      </div>

      {/* Forgot Password Dialog */}
      <Dialog open={forgotDialogOpen} onOpenChange={setForgotDialogOpen}>
        <DialogContent className="w-[95vw] max-w-md p-6" dir="rtl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl">
              <KeyRound className="w-5 h-5 text-orange-600" />
              استعادة كلمة المرور
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleForgotPassword} className="space-y-4 mt-4">
            <p className="text-sm text-slate-600">
              أدخل بريدك الإلكتروني وسنرسل لك كلمة مرور جديدة
            </p>
            <div className="space-y-2">
              <Label htmlFor="forgot-email" className="text-slate-700 font-medium">
                البريد الإلكتروني
              </Label>
              <div className="relative">
                <Mail className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  id="forgot-email"
                  type="email"
                  placeholder="example@company.com"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  className="pr-10 h-12"
                  dir="ltr"
                />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <Button
                type="submit"
                className="flex-1 h-11 bg-orange-600 hover:bg-orange-700"
                disabled={forgotLoading}
              >
                {forgotLoading ? "جاري الإرسال..." : "إرسال كلمة المرور"}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="h-11"
                onClick={() => setForgotDialogOpen(false)}
              >
                إلغاء
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default LoginPage;
