import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Package, Mail, Lock, User, Briefcase, ArrowLeft } from "lucide-react";

const RegisterPage = () => {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();

  const roles = [
    { value: "supervisor", label: "مشرف موقع", icon: "👷" },
    { value: "engineer", label: "مهندس", icon: "👨‍💼" },
    { value: "procurement_manager", label: "مدير مشتريات", icon: "📋" },
    { value: "printer", label: "موظف طباعة", icon: "🖨️" },
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name || !email || !password || !role) {
      toast.error("الرجاء إكمال جميع البيانات");
      return;
    }

    if (password.length < 6) {
      toast.error("كلمة المرور يجب أن تكون 6 أحرف على الأقل");
      return;
    }

    setLoading(true);
    try {
      await register(name, email, password, role);
      toast.success("تم إنشاء الحساب بنجاح");
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل إنشاء الحساب");
    } finally {
      setLoading(false);
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
            <p className="text-slate-500">أنشئ حسابك الجديد</p>
          </div>

          <Card className="border-slate-200 shadow-lg">
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-2xl font-bold text-center">إنشاء حساب</CardTitle>
              <CardDescription className="text-center">
                أدخل بياناتك لإنشاء حساب جديد
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name" className="text-slate-700 font-medium">
                    الاسم الكامل
                  </Label>
                  <div className="relative">
                    <User className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <Input
                      id="name"
                      type="text"
                      placeholder="أحمد محمد"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="pr-10 h-12 text-right"
                      data-testid="register-name-input"
                    />
                  </div>
                </div>

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
                      data-testid="register-email-input"
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
                      data-testid="register-password-input"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="role" className="text-slate-700 font-medium">
                    الدور الوظيفي
                  </Label>
                  <div className="relative">
                    <Briefcase className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400 z-10 pointer-events-none" />
                    <Select value={role} onValueChange={setRole}>
                      <SelectTrigger 
                        className="h-12 pr-10 text-right" 
                        data-testid="register-role-select"
                      >
                        <SelectValue placeholder="اختر دورك الوظيفي" />
                      </SelectTrigger>
                      <SelectContent>
                        {roles.map((r) => (
                          <SelectItem 
                            key={r.value} 
                            value={r.value}
                            data-testid={`role-option-${r.value}`}
                          >
                            <span className="flex items-center gap-2">
                              <span>{r.icon}</span>
                              <span>{r.label}</span>
                            </span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full h-12 bg-orange-600 hover:bg-orange-700 text-white font-bold text-lg transition-all active:scale-[0.98]"
                  disabled={loading}
                  data-testid="register-submit-btn"
                >
                  {loading ? (
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>جاري الإنشاء...</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <ArrowLeft className="w-5 h-5" />
                      <span>إنشاء حساب</span>
                    </div>
                  )}
                </Button>
              </form>

              <div className="mt-6 text-center">
                <p className="text-slate-600">
                  لديك حساب بالفعل؟{" "}
                  <Link
                    to="/login"
                    className="text-orange-600 hover:text-orange-700 font-semibold hover:underline"
                    data-testid="login-link"
                  >
                    سجل دخول
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
          <h2 className="text-4xl font-bold mb-4">انضم إلى فريقنا</h2>
          <p className="text-xl text-slate-200 max-w-md">
            سجل الآن وابدأ في إدارة طلبات المواد بكفاءة عالية
          </p>
          <div className="mt-8 space-y-4 text-right">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-orange-600 flex items-center justify-center text-lg">
                👷
              </div>
              <span className="text-lg">مشرف موقع - إنشاء طلبات المواد</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-orange-600 flex items-center justify-center text-lg">
                👨‍💼
              </div>
              <span className="text-lg">مهندس - اعتماد الطلبات</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-orange-600 flex items-center justify-center text-lg">
                📋
              </div>
              <span className="text-lg">مدير مشتريات - إصدار أوامر الشراء</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
