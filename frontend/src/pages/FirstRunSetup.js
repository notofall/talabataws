import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { 
  Database, Server, Cloud, CheckCircle2, XCircle, Container,
  Loader2, Eye, EyeOff, ArrowRight, ArrowLeft, Package,
  User, Mail, Lock, Wifi, Globe, HardDrive
} from 'lucide-react';

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

export default function FirstRunSetup() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [dbType, setDbType] = useState('');
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [showAdminPassword, setShowAdminPassword] = useState(false);

  const [config, setConfig] = useState({
    host: 'localhost',
    port: 5432,
    database: 'talabat_db',
    username: 'postgres',
    password: '',
    ssl_mode: 'disable'
  });

  const [adminUser, setAdminUser] = useState({
    name: 'مدير النظام',
    email: '',
    password: ''
  });

  // Check if setup is already complete
  useEffect(() => {
    axios.get(`${API_BASE}/api/setup/status`)
      .then(res => {
        if (res.data.is_configured && !res.data.needs_setup) {
          navigate('/login');
        }
      })
      .catch(() => {});
  }, [navigate]);

  const dbTypes = [
    {
      id: 'docker',
      name: 'Docker',
      nameAr: 'دوكر (الإعداد التلقائي)',
      description: 'قاعدة بيانات PostgreSQL داخل Docker',
      icon: Container,
      color: 'bg-blue-500',
      defaults: {
        host: 'postgres',
        port: 5432,
        database: 'talabat_db',
        username: 'admin',
        password: 'admin123',
        ssl_mode: 'disable'
      }
    },
    {
      id: 'local',
      name: 'Local PostgreSQL',
      nameAr: 'قاعدة بيانات محلية',
      description: 'PostgreSQL مثبت على جهازك',
      icon: HardDrive,
      color: 'bg-green-500',
      defaults: {
        host: 'localhost',
        port: 5432,
        database: 'talabat_db',
        username: 'postgres',
        password: '',
        ssl_mode: 'disable'
      }
    },
    {
      id: 'cloud',
      name: 'Cloud Database',
      nameAr: 'قاعدة بيانات سحابية',
      description: 'PlanetScale, Neon, Supabase, أو أي خدمة سحابية',
      icon: Cloud,
      color: 'bg-purple-500',
      defaults: {
        host: '',
        port: 5432,
        database: '',
        username: '',
        password: '',
        ssl_mode: 'require'
      }
    }
  ];

  const cloudPresets = [
    { name: 'PlanetScale', host: 'aws.connect.psdb.cloud', port: 5432, ssl_mode: 'require' },
    { name: 'Neon', host: 'ep-xxx.region.aws.neon.tech', port: 5432, ssl_mode: 'require' },
    { name: 'Supabase', host: 'db.xxx.supabase.co', port: 5432, ssl_mode: 'require' },
    { name: 'Railway', host: 'xxx.railway.app', port: 5432, ssl_mode: 'require' },
    { name: 'أخرى', host: '', port: 5432, ssl_mode: 'require' }
  ];

  const handleTypeSelect = (type) => {
    setDbType(type.id);
    setConfig(type.defaults);
    setTestResult(null);
    setStep(2);
  };

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);

    try {
      const response = await axios.post(`${API_BASE}/api/setup/test-connection`, {
        db_type: dbType,
        ...config
      });

      setTestResult(response.data);
      if (response.data.success) {
        toast.success('تم الاتصال بنجاح!');
      } else {
        toast.error(response.data.message || 'فشل الاتصال');
      }
    } catch (error) {
      const message = error.response?.data?.detail || 'فشل في الاتصال بقاعدة البيانات';
      setTestResult({ success: false, message });
      toast.error(message);
    } finally {
      setTesting(false);
    }
  };

  const handleSaveConfig = async () => {
    if (!adminUser.email || !adminUser.password) {
      toast.error('يرجى إدخال بيانات المدير');
      return;
    }

    if (adminUser.password.length < 6) {
      toast.error('كلمة المرور يجب أن تكون 6 أحرف على الأقل');
      return;
    }

    setSaving(true);

    try {
      const response = await axios.post(`${API_BASE}/api/setup/complete-setup`, {
        database: {
          db_type: dbType,
          ...config
        },
        admin_user: adminUser
      });

      if (response.data.success) {
        toast.success('تم إعداد النظام بنجاح!');
        
        // Save token if provided
        if (response.data.access_token) {
          localStorage.setItem('token', response.data.access_token);
          localStorage.setItem('user', JSON.stringify(response.data.user));
        }

        setStep(4);
        
        // Redirect after 2 seconds
        setTimeout(() => {
          window.location.href = '/';
        }, 2000);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'فشل في حفظ الإعدادات');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-orange-600 rounded-2xl mb-4 shadow-lg shadow-orange-600/30">
            <Package className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">نظام إدارة طلبات المواد</h1>
          <p className="text-slate-400">معالج الإعداد الأولي</p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center mb-8 gap-2">
          {[1, 2, 3, 4].map((s) => (
            <div key={s} className="flex items-center">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all ${
                step >= s 
                  ? 'bg-orange-600 text-white' 
                  : 'bg-slate-700 text-slate-400'
              }`}>
                {step > s ? <CheckCircle2 className="w-5 h-5" /> : s}
              </div>
              {s < 4 && (
                <div className={`w-12 h-1 mx-1 rounded ${
                  step > s ? 'bg-orange-600' : 'bg-slate-700'
                }`} />
              )}
            </div>
          ))}
        </div>

        {/* Step 1: Choose Database Type */}
        {step === 1 && (
          <Card className="border-slate-700 bg-slate-800/50 backdrop-blur">
            <CardHeader className="text-center">
              <CardTitle className="text-2xl text-white">اختر نوع قاعدة البيانات</CardTitle>
              <CardDescription className="text-slate-400">
                اختر طريقة الاتصال بقاعدة البيانات المناسبة لك
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {dbTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => handleTypeSelect(type)}
                  className="w-full p-4 rounded-xl border-2 border-slate-600 hover:border-orange-500 bg-slate-700/50 hover:bg-slate-700 transition-all group text-right"
                  data-testid={`db-type-${type.id}`}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-14 h-14 ${type.color} rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform`}>
                      <type.icon className="w-7 h-7 text-white" />
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-bold text-white">{type.nameAr}</h3>
                      <p className="text-sm text-slate-400">{type.description}</p>
                    </div>
                    <ArrowLeft className="w-5 h-5 text-slate-400 group-hover:text-orange-500 transition-colors" />
                  </div>
                </button>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Step 2: Database Configuration */}
        {step === 2 && (
          <Card className="border-slate-700 bg-slate-800/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setStep(1)}
                  className="text-slate-400 hover:text-white"
                >
                  <ArrowRight className="w-4 h-4" />
                </Button>
                <div>
                  <CardTitle className="text-xl text-white">إعدادات الاتصال</CardTitle>
                  <CardDescription className="text-slate-400">
                    {dbType === 'docker' ? 'إعدادات Docker جاهزة' : 'أدخل بيانات الاتصال'}
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Cloud Presets */}
              {dbType === 'cloud' && (
                <div>
                  <Label className="text-slate-300">مزود الخدمة السحابية</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {cloudPresets.map((preset) => (
                      <button
                        key={preset.name}
                        onClick={() => setConfig(prev => ({
                          ...prev,
                          host: preset.host,
                          port: preset.port,
                          ssl_mode: preset.ssl_mode
                        }))}
                        className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                          config.host === preset.host
                            ? 'bg-orange-600 text-white'
                            : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                        }`}
                      >
                        {preset.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Host */}
              <div>
                <Label className="text-slate-300">عنوان الخادم (Host)</Label>
                <div className="relative mt-1">
                  <Input
                    value={config.host}
                    onChange={(e) => setConfig(prev => ({ ...prev, host: e.target.value }))}
                    placeholder="localhost أو عنوان الخادم"
                    className="bg-slate-700 border-slate-600 text-white pr-10"
                    disabled={dbType === 'docker'}
                  />
                  <Server className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                </div>
              </div>

              {/* Port & Database */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-slate-300">المنفذ (Port)</Label>
                  <Input
                    type="number"
                    value={config.port}
                    onChange={(e) => setConfig(prev => ({ ...prev, port: parseInt(e.target.value) }))}
                    className="bg-slate-700 border-slate-600 text-white mt-1"
                    disabled={dbType === 'docker'}
                  />
                </div>
                <div>
                  <Label className="text-slate-300">اسم قاعدة البيانات</Label>
                  <Input
                    value={config.database}
                    onChange={(e) => setConfig(prev => ({ ...prev, database: e.target.value }))}
                    placeholder="talabat_db"
                    className="bg-slate-700 border-slate-600 text-white mt-1"
                    disabled={dbType === 'docker'}
                  />
                </div>
              </div>

              {/* Username */}
              <div>
                <Label className="text-slate-300">اسم المستخدم</Label>
                <div className="relative mt-1">
                  <Input
                    value={config.username}
                    onChange={(e) => setConfig(prev => ({ ...prev, username: e.target.value }))}
                    placeholder="postgres"
                    className="bg-slate-700 border-slate-600 text-white pr-10"
                    disabled={dbType === 'docker'}
                  />
                  <User className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                </div>
              </div>

              {/* Password */}
              <div>
                <Label className="text-slate-300">كلمة المرور</Label>
                <div className="relative mt-1">
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    value={config.password}
                    onChange={(e) => setConfig(prev => ({ ...prev, password: e.target.value }))}
                    placeholder="••••••••"
                    className="bg-slate-700 border-slate-600 text-white px-10"
                    disabled={dbType === 'docker'}
                  />
                  <Lock className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* SSL Mode */}
              <div>
                <Label className="text-slate-300">وضع SSL</Label>
                <div className="flex gap-3 mt-2">
                  <button
                    onClick={() => setConfig(prev => ({ ...prev, ssl_mode: 'disable' }))}
                    className={`flex-1 py-2 rounded-lg transition-all ${
                      config.ssl_mode === 'disable'
                        ? 'bg-orange-600 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                    disabled={dbType === 'docker'}
                  >
                    معطل (محلي)
                  </button>
                  <button
                    onClick={() => setConfig(prev => ({ ...prev, ssl_mode: 'require' }))}
                    className={`flex-1 py-2 rounded-lg transition-all ${
                      config.ssl_mode === 'require'
                        ? 'bg-orange-600 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                    disabled={dbType === 'docker'}
                  >
                    مفعل (سحابي)
                  </button>
                </div>
              </div>

              {/* Test Result */}
              {testResult && (
                <div className={`p-4 rounded-xl ${
                  testResult.success 
                    ? 'bg-green-500/20 border border-green-500/50' 
                    : 'bg-red-500/20 border border-red-500/50'
                }`}>
                  <div className="flex items-center gap-3">
                    {testResult.success ? (
                      <CheckCircle2 className="w-6 h-6 text-green-400" />
                    ) : (
                      <XCircle className="w-6 h-6 text-red-400" />
                    )}
                    <div>
                      <p className={`font-medium ${testResult.success ? 'text-green-400' : 'text-red-400'}`}>
                        {testResult.success ? 'تم الاتصال بنجاح!' : 'فشل الاتصال'}
                      </p>
                      {testResult.message && (
                        <p className="text-sm text-slate-400 mt-1">{testResult.message}</p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <Button
                  onClick={testConnection}
                  disabled={testing}
                  variant="outline"
                  className="flex-1 border-slate-600 text-slate-300 hover:bg-slate-700"
                  data-testid="test-connection-btn"
                >
                  {testing ? (
                    <Loader2 className="w-4 h-4 animate-spin ml-2" />
                  ) : (
                    <Wifi className="w-4 h-4 ml-2" />
                  )}
                  اختبار الاتصال
                </Button>
                <Button
                  onClick={() => setStep(3)}
                  disabled={!testResult?.success && dbType !== 'docker'}
                  className="flex-1 bg-orange-600 hover:bg-orange-700"
                  data-testid="next-step-btn"
                >
                  التالي
                  <ArrowLeft className="w-4 h-4 mr-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Admin User */}
        {step === 3 && (
          <Card className="border-slate-700 bg-slate-800/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setStep(2)}
                  className="text-slate-400 hover:text-white"
                >
                  <ArrowRight className="w-4 h-4" />
                </Button>
                <div>
                  <CardTitle className="text-xl text-white">إنشاء حساب المدير</CardTitle>
                  <CardDescription className="text-slate-400">
                    أنشئ حساب مدير النظام الأول
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Admin Name */}
              <div>
                <Label className="text-slate-300">الاسم</Label>
                <div className="relative mt-1">
                  <Input
                    value={adminUser.name}
                    onChange={(e) => setAdminUser(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="مدير النظام"
                    className="bg-slate-700 border-slate-600 text-white pr-10"
                    data-testid="admin-name-input"
                  />
                  <User className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                </div>
              </div>

              {/* Admin Email */}
              <div>
                <Label className="text-slate-300">البريد الإلكتروني</Label>
                <div className="relative mt-1">
                  <Input
                    type="email"
                    value={adminUser.email}
                    onChange={(e) => setAdminUser(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="admin@company.com"
                    className="bg-slate-700 border-slate-600 text-white pr-10"
                    data-testid="admin-email-input"
                  />
                  <Mail className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                </div>
              </div>

              {/* Admin Password */}
              <div>
                <Label className="text-slate-300">كلمة المرور</Label>
                <div className="relative mt-1">
                  <Input
                    type={showAdminPassword ? 'text' : 'password'}
                    value={adminUser.password}
                    onChange={(e) => setAdminUser(prev => ({ ...prev, password: e.target.value }))}
                    placeholder="••••••••"
                    className="bg-slate-700 border-slate-600 text-white px-10"
                    data-testid="admin-password-input"
                  />
                  <Lock className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <button
                    type="button"
                    onClick={() => setShowAdminPassword(!showAdminPassword)}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
                  >
                    {showAdminPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-xs text-slate-500 mt-1">يجب أن تكون 6 أحرف على الأقل</p>
              </div>

              {/* Save Button */}
              <Button
                onClick={handleSaveConfig}
                disabled={saving || !adminUser.email || !adminUser.password}
                className="w-full h-12 bg-orange-600 hover:bg-orange-700 text-lg mt-4"
                data-testid="save-setup-btn"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin ml-2" />
                    جاري الحفظ...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-5 h-5 ml-2" />
                    إكمال الإعداد
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Step 4: Success */}
        {step === 4 && (
          <Card className="border-slate-700 bg-slate-800/50 backdrop-blur">
            <CardContent className="py-12 text-center">
              <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle2 className="w-10 h-10 text-green-400" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">تم الإعداد بنجاح!</h2>
              <p className="text-slate-400 mb-6">جاري تحويلك للصفحة الرئيسية...</p>
              <Loader2 className="w-8 h-8 animate-spin text-orange-500 mx-auto" />
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
