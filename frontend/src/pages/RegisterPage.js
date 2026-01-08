import { Link, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Package, ArrowLeft, UserPlus, Shield, Info, AlertCircle } from "lucide-react";

const RegisterPage = () => {
  const navigate = useNavigate();

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
            <p className="text-slate-500">إنشاء حساب جديد</p>
          </div>

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

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-slate-500 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm text-slate-700 font-medium mb-1">هل أنت المسؤول الأول؟</p>
                    <p className="text-sm text-slate-600">
                      إذا كان هذا نظام جديد ولم يتم إعداده بعد، يمكنك إنشاء حساب المدير الأول.
                    </p>
                    <Button 
                      variant="link" 
                      className="p-0 h-auto text-orange-600 text-sm mt-1"
                      onClick={() => navigate("/setup")}
                    >
                      الذهاب لصفحة الإعداد →
                    </Button>
                  </div>
                </div>
              </div>

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
