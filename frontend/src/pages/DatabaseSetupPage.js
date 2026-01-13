import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { 
  Database, Server, Cloud, CheckCircle2, XCircle, 
  Loader2, RefreshCw, Eye, EyeOff, Settings, ArrowLeft,
  User, Mail, Lock
} from 'lucide-react';

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

export default function DatabaseSetupPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // 1: choose type, 2: enter details, 3: admin user, 4: success
  const [dbType, setDbType] = useState(''); // 'local' or 'cloud'
  const [testing, setTesting] = useState(false);
  const [configuring, setConfiguring] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showAdminPassword, setShowAdminPassword] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState('');
  
  const [config, setConfig] = useState({
    host: '',
    port: 5432,
    database: '',
    username: '',
    password: '',
    ssl_mode: 'require'
  });

  const [adminUser, setAdminUser] = useState({
    name: 'مدير النظام',
    email: '',
    password: ''
  });

  useEffect(() => {
    // Load cloud presets
    axios.get(`${API_BASE}/api/setup/presets`)
      .then(res => setPresets(res.data.presets || []))
      .catch(() => {});
  }, []);

  const handlePresetChange = (presetName) => {
    setSelectedPreset(presetName);
    const preset = presets.find(p => p.name === presetName);
    if (preset) {
      setConfig(prev => ({
        ...prev,
        host: preset.host,
        port: preset.port,
        ssl_mode: preset.ssl_mode
      }));
    }
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
        toast.error(response.data.message);
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: error.response?.data?.detail || 'فشل في الاتصال'
      });
      toast.error('فشل في الاتصال');
    } finally {
      setTesting(false);
    }
  };

  const configureDatabase = async () => {
    setConfiguring(true);
    
    try {
      const response = await axios.post(`${API_BASE}/api/setup/complete-setup`, {
        database: {
          db_type: dbType,
          ...config
        },
        admin_user: adminUser.email ? adminUser : null
      });
      
      if (response.data.success) {
        toast.success('تم إعداد النظام بنجاح!');
        setStep(4);
        
        // Reload after 3 seconds
        setTimeout(() => {
          window.location.href = '/login';
        }, 3000);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'فشل في إعداد قاعدة البيانات');
    } finally {
      setConfiguring(false);
    }
  };

  // Step 1: Choose database type
  if (step === 1) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4" dir="rtl">
        <div className="w-full max-w-2xl">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-orange-500/20 rounded-2xl mb-4">
              <Database className="w-10 h-10 text-orange-500" />
            </div>
            <h1 className="text-3xl font-bold text-white mb-2">إعداد قاعدة البيانات</h1>
            <p className="text-slate-400">اختر طريقة تخزين البيانات المناسبة لك</p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-4">
            {/* Local Option */}
            <Card 
              data-testid="db-type-local"
              className={`cursor-pointer transition-all hover:border-orange-500 ${dbType === 'local' ? 'border-orange-500 bg-orange-500/10' : 'bg-slate-800/50 border-slate-700'}`}
              onClick={() => setDbType('local')}
            >
              <CardContent className="p-6 text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-500/20 rounded-xl mb-4">
                  <Server className="w-8 h-8 text-blue-500" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">خادم محلي</h3>
                <p className="text-slate-400 text-sm mb-4">
                  تثبيت PostgreSQL على نفس الخادم
                </p>
                <ul className="text-right text-sm text-slate-300 space-y-2">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                    <span>تحكم كامل بالبيانات</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                    <span>لا حاجة لاتصال إنترنت</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                    <span>أداء أسرع</span>
                  </li>
                </ul>
              </CardContent>
            </Card>
            
            {/* Cloud Option */}
            <Card 
              data-testid="db-type-cloud"
              className={`cursor-pointer transition-all hover:border-orange-500 ${dbType === 'cloud' ? 'border-orange-500 bg-orange-500/10' : 'bg-slate-800/50 border-slate-700'}`}
              onClick={() => setDbType('cloud')}
            >
              <CardContent className="p-6 text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-500/20 rounded-xl mb-4">
                  <Cloud className="w-8 h-8 text-purple-500" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">قاعدة بيانات سحابية</h3>
                <p className="text-slate-400 text-sm mb-4">
                  الاتصال بخدمة سحابية خارجية
                </p>
                <ul className="text-right text-sm text-slate-300 space-y-2">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                    <span>نسخ احتياطي تلقائي</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                    <span>قابلية توسع عالية</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                    <span>صيانة أقل</span>
                  </li>
                </ul>
              </CardContent>
            </Card>
          </div>
          
          <div className="mt-6 text-center">
            <Button 
              onClick={() => setStep(2)} 
              disabled={!dbType}
              className="bg-orange-600 hover:bg-orange-700 px-8"
            >
              التالي
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Step 2: Enter connection details
  if (step === 2) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4" dir="rtl">
        <div className="w-full max-w-xl">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" onClick={() => setStep(1)} className="text-slate-400">
                  <ArrowLeft className="w-4 h-4" />
                </Button>
                <div>
                  <CardTitle className="text-white flex items-center gap-2">
                    {dbType === 'local' ? <Server className="w-5 h-5" /> : <Cloud className="w-5 h-5" />}
                    {dbType === 'local' ? 'إعداد الخادم المحلي' : 'إعداد القاعدة السحابية'}
                  </CardTitle>
                  <CardDescription>أدخل بيانات الاتصال بقاعدة البيانات</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Cloud Presets */}
              {dbType === 'cloud' && presets.length > 0 && (
                <div>
                  <Label className="text-slate-300">اختر مزود الخدمة</Label>
                  <select
                    value={selectedPreset}
                    onChange={(e) => handlePresetChange(e.target.value)}
                    className="w-full h-10 bg-slate-700 border-slate-600 text-white rounded-lg px-3 mt-1"
                  >
                    <option value="">-- اختر --</option>
                    {presets.filter(p => p.name !== 'Local PostgreSQL').map(preset => (
                      <option key={preset.name} value={preset.name}>{preset.name}</option>
                    ))}
                  </select>
                </div>
              )}
              
              {/* Host */}
              <div>
                <Label className="text-slate-300">عنوان الخادم (Host)</Label>
                <Input
                  value={config.host}
                  onChange={(e) => setConfig(prev => ({ ...prev, host: e.target.value }))}
                  placeholder={dbType === 'local' ? 'localhost' : 'db.example.com'}
                  className="bg-slate-700 border-slate-600 text-white mt-1"
                />
              </div>
              
              {/* Port */}
              <div>
                <Label className="text-slate-300">المنفذ (Port)</Label>
                <Input
                  type="number"
                  value={config.port}
                  onChange={(e) => setConfig(prev => ({ ...prev, port: parseInt(e.target.value) || 5432 }))}
                  placeholder="5432"
                  className="bg-slate-700 border-slate-600 text-white mt-1"
                />
              </div>
              
              {/* Database Name */}
              <div>
                <Label className="text-slate-300">اسم قاعدة البيانات</Label>
                <Input
                  value={config.database}
                  onChange={(e) => setConfig(prev => ({ ...prev, database: e.target.value }))}
                  placeholder="material_requests"
                  className="bg-slate-700 border-slate-600 text-white mt-1"
                />
              </div>
              
              {/* Username */}
              <div>
                <Label className="text-slate-300">اسم المستخدم</Label>
                <Input
                  value={config.username}
                  onChange={(e) => setConfig(prev => ({ ...prev, username: e.target.value }))}
                  placeholder="postgres"
                  className="bg-slate-700 border-slate-600 text-white mt-1"
                />
              </div>
              
              {/* Password */}
              <div>
                <Label className="text-slate-300">كلمة المرور</Label>
                <div className="relative">
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    value={config.password}
                    onChange={(e) => setConfig(prev => ({ ...prev, password: e.target.value }))}
                    className="bg-slate-700 border-slate-600 text-white mt-1 pl-10"
                  />
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
                <select
                  value={config.ssl_mode}
                  onChange={(e) => setConfig(prev => ({ ...prev, ssl_mode: e.target.value }))}
                  className="w-full h-10 bg-slate-700 border-slate-600 text-white rounded-lg px-3 mt-1"
                >
                  <option value="require">مطلوب (للسحابة)</option>
                  <option value="disable">معطل (للمحلي)</option>
                </select>
              </div>
              
              {/* Test Result */}
              {testResult && (
                <div className={`p-4 rounded-lg ${testResult.success ? 'bg-green-500/20 border border-green-500' : 'bg-red-500/20 border border-red-500'}`}>
                  <div className="flex items-center gap-2">
                    {testResult.success ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-500" />
                    )}
                    <span className={testResult.success ? 'text-green-400' : 'text-red-400'}>
                      {testResult.message}
                    </span>
                  </div>
                </div>
              )}
              
              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <Button
                  variant="outline"
                  onClick={testConnection}
                  disabled={testing || !config.host || !config.database || !config.username}
                  className="flex-1"
                >
                  {testing ? (
                    <Loader2 className="w-4 h-4 animate-spin ml-2" />
                  ) : (
                    <RefreshCw className="w-4 h-4 ml-2" />
                  )}
                  اختبار الاتصال
                </Button>
                
                <Button
                  onClick={() => setStep(3)}
                  disabled={!testResult?.success}
                  className="flex-1 bg-orange-600 hover:bg-orange-700"
                >
                  التالي
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Step 3: Create Admin User
  if (step === 3) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4" dir="rtl">
        <div className="w-full max-w-xl">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" onClick={() => setStep(2)} className="text-slate-400">
                  <ArrowLeft className="w-4 h-4" />
                </Button>
                <div>
                  <CardTitle className="text-white flex items-center gap-2">
                    <User className="w-5 h-5" />
                    إنشاء حساب مدير النظام
                  </CardTitle>
                  <CardDescription>أنشئ حساب المسؤول الأول للنظام</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Admin Name */}
              <div>
                <Label className="text-slate-300">الاسم</Label>
                <div className="relative">
                  <Input
                    value={adminUser.name}
                    onChange={(e) => setAdminUser(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="مدير النظام"
                    className="bg-slate-700 border-slate-600 text-white mt-1 pr-10"
                  />
                  <User className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                </div>
              </div>
              
              {/* Admin Email */}
              <div>
                <Label className="text-slate-300">البريد الإلكتروني</Label>
                <div className="relative">
                  <Input
                    type="email"
                    value={adminUser.email}
                    onChange={(e) => setAdminUser(prev => ({ ...prev, email: e.target.value }))}
                    placeholder="admin@company.com"
                    className="bg-slate-700 border-slate-600 text-white mt-1 pr-10"
                  />
                  <Mail className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                </div>
              </div>
              
              {/* Admin Password */}
              <div>
                <Label className="text-slate-300">كلمة المرور</Label>
                <div className="relative">
                  <Input
                    type={showAdminPassword ? 'text' : 'password'}
                    value={adminUser.password}
                    onChange={(e) => setAdminUser(prev => ({ ...prev, password: e.target.value }))}
                    placeholder="••••••••"
                    className="bg-slate-700 border-slate-600 text-white mt-1 px-10"
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
              
              {/* Summary */}
              <div className="p-4 bg-slate-700/50 rounded-lg">
                <h4 className="text-sm font-medium text-white mb-2">ملخص الإعداد:</h4>
                <div className="text-sm text-slate-400 space-y-1">
                  <p>• نوع القاعدة: {dbType === 'local' ? 'خادم محلي' : 'سحابية'}</p>
                  <p>• الخادم: {config.host}:{config.port}</p>
                  <p>• قاعدة البيانات: {config.database}</p>
                  <p>• المسؤول: {adminUser.email || '(لم يتم تحديده)'}</p>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <Button
                  variant="outline"
                  onClick={() => {
                    setAdminUser({ name: '', email: '', password: '' });
                    configureDatabase();
                  }}
                  disabled={configuring}
                  className="flex-1"
                >
                  تخطي (بدون مسؤول)
                </Button>
                
                <Button
                  onClick={configureDatabase}
                  disabled={configuring || !adminUser.email || adminUser.password.length < 6}
                  className="flex-1 bg-orange-600 hover:bg-orange-700"
                >
                  {configuring ? (
                    <Loader2 className="w-4 h-4 animate-spin ml-2" />
                  ) : (
                    <Settings className="w-4 h-4 ml-2" />
                  )}
                  إكمال الإعداد
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Step 4: Success
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4" dir="rtl">
      <Card className="bg-slate-800/50 border-slate-700 max-w-md w-full text-center">
        <CardContent className="p-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-green-500/20 rounded-full mb-6">
            <CheckCircle2 className="w-10 h-10 text-green-500" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">تم الإعداد بنجاح!</h2>
          <p className="text-slate-400 mb-6">
            تم إعداد قاعدة البيانات وإنشاء جميع الجداول المطلوبة.
            {adminUser.email && (
              <>
                <br />
                <span className="text-green-400">تم إنشاء حساب المسؤول: {adminUser.email}</span>
              </>
            )}
            <br />
            <br />
            جاري إعادة التوجيه إلى صفحة تسجيل الدخول...
          </p>
          <Loader2 className="w-6 h-6 animate-spin mx-auto text-orange-500" />
        </CardContent>
      </Card>
    </div>
  );
}
