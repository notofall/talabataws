import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Checkbox } from '../components/ui/checkbox';
import { 
  Users, Plus, Edit, Trash2, Key, UserCheck, UserX, Search, 
  RefreshCw, Shield, Briefcase, Building, Link2, X, Eye, EyeOff
} from 'lucide-react';

const roleLabels = {
  supervisor: { label: "مشرف موقع", icon: "👷", color: "bg-blue-100 text-blue-800" },
  engineer: { label: "مهندس", icon: "👨‍💼", color: "bg-green-100 text-green-800" },
  procurement_manager: { label: "مدير مشتريات", icon: "📋", color: "bg-orange-100 text-orange-800" },
  printer: { label: "موظف طباعة", icon: "🖨️", color: "bg-purple-100 text-purple-800" },
  delivery_tracker: { label: "متتبع التوريد", icon: "🚚", color: "bg-cyan-100 text-cyan-800" },
  general_manager: { label: "المدير العام", icon: "👔", color: "bg-red-100 text-red-800" },
  quantity_engineer: { label: "مهندس الكميات", icon: "📊", color: "bg-indigo-100 text-indigo-800" },
};

export default function UserManagement({ open, onOpenChange }) {
  const { getAuthHeaders, API_URL } = useAuth();
  const [users, setUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [engineers, setEngineers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  
  // Dialog states
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  
  // Form states
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    role: "",
    assigned_projects: [],
    assigned_engineers: []
  });
  const [newPassword, setNewPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      fetchData();
    }
  }, [open]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [usersRes, projectsRes] = await Promise.all([
        axios.get(`${API_URL}/admin/users`, getAuthHeaders()),
        axios.get(`${API_URL}/projects`, getAuthHeaders())
      ]);
      setUsers(usersRes.data);
      setProjects(projectsRes.data);
      setEngineers(usersRes.data.filter(u => u.role === "engineer"));
    } catch (error) {
      toast.error("فشل في تحميل البيانات");
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.name.toLowerCase().includes(search.toLowerCase()) ||
                         user.email.toLowerCase().includes(search.toLowerCase());
    const matchesRole = roleFilter === "all" || user.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  const handleAddUser = async () => {
    if (!formData.name || !formData.email || !formData.password || !formData.role) {
      toast.error("الرجاء إكمال جميع البيانات المطلوبة");
      return;
    }
    
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/admin/users`, formData, getAuthHeaders());
      toast.success("تم إضافة المستخدم بنجاح");
      setAddDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في إضافة المستخدم");
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateUser = async () => {
    if (!selectedUser) return;
    
    setSubmitting(true);
    try {
      await axios.put(`${API_URL}/admin/users/${selectedUser.id}`, {
        name: formData.name,
        email: formData.email,
        role: formData.role
      }, getAuthHeaders());
      toast.success("تم تحديث المستخدم بنجاح");
      setEditDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تحديث المستخدم");
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdateAssignments = async () => {
    if (!selectedUser) return;
    
    setSubmitting(true);
    try {
      await axios.put(`${API_URL}/admin/users/${selectedUser.id}`, {
        assigned_projects: formData.assigned_projects,
        assigned_engineers: formData.assigned_engineers
      }, getAuthHeaders());
      toast.success("تم تحديث الربط بنجاح");
      setAssignDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تحديث الربط");
    } finally {
      setSubmitting(false);
    }
  };

  const handleResetPassword = async () => {
    if (!selectedUser || !newPassword) return;
    
    if (newPassword.length < 6) {
      toast.error("كلمة المرور يجب أن تكون 6 أحرف على الأقل");
      return;
    }
    
    setSubmitting(true);
    try {
      await axios.post(`${API_URL}/admin/users/${selectedUser.id}/reset-password`, {
        new_password: newPassword
      }, getAuthHeaders());
      toast.success("تم إعادة تعيين كلمة المرور بنجاح");
      setResetPasswordDialogOpen(false);
      setNewPassword("");
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في إعادة تعيين كلمة المرور");
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (user) => {
    try {
      const res = await axios.put(`${API_URL}/admin/users/${user.id}/toggle-active`, {}, getAuthHeaders());
      toast.success(res.data.message);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في تغيير حالة الحساب");
    }
  };

  const handleDeleteUser = async (user) => {
    if (!confirm(`هل أنت متأكد من حذف المستخدم "${user.name}"؟`)) return;
    
    try {
      await axios.delete(`${API_URL}/admin/users/${user.id}`, getAuthHeaders());
      toast.success("تم حذف المستخدم بنجاح");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "فشل في حذف المستخدم");
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      email: "",
      password: "",
      role: "",
      assigned_projects: [],
      assigned_engineers: []
    });
    setSelectedUser(null);
  };

  const openEditDialog = (user) => {
    setSelectedUser(user);
    setFormData({
      name: user.name,
      email: user.email,
      password: "",
      role: user.role,
      assigned_projects: user.assigned_projects || [],
      assigned_engineers: user.assigned_engineers || []
    });
    setEditDialogOpen(true);
  };

  const openAssignDialog = (user) => {
    setSelectedUser(user);
    setFormData({
      ...formData,
      assigned_projects: user.assigned_projects || [],
      assigned_engineers: user.assigned_engineers || []
    });
    setAssignDialogOpen(true);
  };

  const openResetPasswordDialog = (user) => {
    setSelectedUser(user);
    setNewPassword("");
    setResetPasswordDialogOpen(true);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto" dir="rtl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="w-5 h-5 text-orange-600" />
            إدارة المستخدمين
          </DialogTitle>
        </DialogHeader>

        {/* Toolbar */}
        <div className="flex flex-wrap gap-2 mb-4">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="بحث بالاسم أو البريد..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pr-10"
              />
            </div>
          </div>
          <Select value={roleFilter} onValueChange={setRoleFilter}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="الدور" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">جميع الأدوار</SelectItem>
              {Object.entries(roleLabels).map(([value, { label, icon }]) => (
                <SelectItem key={value} value={value}>{icon} {label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button size="sm" className="bg-orange-600 hover:bg-orange-700" onClick={() => { resetForm(); setAddDialogOpen(true); }}>
            <Plus className="w-4 h-4 ml-1" />
            إضافة مستخدم
          </Button>
        </div>

        {/* Users Table */}
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="text-right p-3 font-medium">المستخدم</th>
                <th className="text-right p-3 font-medium hidden sm:table-cell">البريد</th>
                <th className="text-center p-3 font-medium">الدور</th>
                <th className="text-center p-3 font-medium">الحالة</th>
                <th className="text-center p-3 font-medium">الإجراءات</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {loading ? (
                <tr>
                  <td colSpan={5} className="text-center p-8 text-slate-500">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                    جاري التحميل...
                  </td>
                </tr>
              ) : filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center p-8 text-slate-500">
                    لا يوجد مستخدمين
                  </td>
                </tr>
              ) : (
                filteredUsers.map((user) => (
                  <tr key={user.id} className={!user.is_active ? "bg-red-50" : ""}>
                    <td className="p-3">
                      <div>
                        <p className="font-medium">{user.name}</p>
                        <p className="text-xs text-slate-500 sm:hidden">{user.email}</p>
                        {user.role === "supervisor" && user.assigned_project_names?.length > 0 && (
                          <p className="text-xs text-blue-600 mt-1">
                            📁 {user.assigned_project_names.slice(0, 2).join("، ")}
                            {user.assigned_project_names.length > 2 && ` +${user.assigned_project_names.length - 2}`}
                          </p>
                        )}
                      </div>
                    </td>
                    <td className="p-3 text-slate-600 hidden sm:table-cell">{user.email}</td>
                    <td className="p-3 text-center">
                      <Badge className={roleLabels[user.role]?.color || "bg-slate-100"}>
                        {roleLabels[user.role]?.icon} {roleLabels[user.role]?.label || user.role}
                      </Badge>
                    </td>
                    <td className="p-3 text-center">
                      {user.is_active !== false ? (
                        <Badge className="bg-green-100 text-green-800">نشط</Badge>
                      ) : (
                        <Badge className="bg-red-100 text-red-800">معطل</Badge>
                      )}
                    </td>
                    <td className="p-3">
                      <div className="flex gap-1 justify-center flex-wrap">
                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openEditDialog(user)} title="تعديل">
                          <Edit className="w-3.5 h-3.5" />
                        </Button>
                        {user.role === "supervisor" && (
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openAssignDialog(user)} title="ربط بمشاريع ومهندسين">
                            <Link2 className="w-3.5 h-3.5" />
                          </Button>
                        )}
                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openResetPasswordDialog(user)} title="إعادة تعيين كلمة المرور">
                          <Key className="w-3.5 h-3.5" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className={`h-7 w-7 p-0 ${user.is_active !== false ? 'text-red-600' : 'text-green-600'}`}
                          onClick={() => handleToggleActive(user)}
                          title={user.is_active !== false ? "تعطيل" : "تفعيل"}
                        >
                          {user.is_active !== false ? <UserX className="w-3.5 h-3.5" /> : <UserCheck className="w-3.5 h-3.5" />}
                        </Button>
                        <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-600" onClick={() => handleDeleteUser(user)} title="حذف">
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <p className="text-xs text-slate-500 mt-2">
          إجمالي المستخدمين: {filteredUsers.length} من {users.length}
        </p>
      </DialogContent>

      {/* Add User Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="max-w-md" dir="rtl">
          <DialogHeader>
            <DialogTitle>إضافة مستخدم جديد</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>الاسم الكامل *</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="أدخل الاسم"
              />
            </div>
            <div>
              <Label>البريد الإلكتروني *</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="example@company.com"
              />
            </div>
            <div>
              <Label>كلمة المرور *</Label>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <div>
              <Label>الدور الوظيفي *</Label>
              <Select value={formData.role} onValueChange={(v) => setFormData({ ...formData, role: v })}>
                <SelectTrigger>
                  <SelectValue placeholder="اختر الدور" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(roleLabels).map(([value, { label, icon }]) => (
                    <SelectItem key={value} value={value}>{icon} {label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2 pt-4">
              <Button onClick={handleAddUser} disabled={submitting} className="flex-1 bg-orange-600 hover:bg-orange-700">
                {submitting ? "جاري الإضافة..." : "إضافة"}
              </Button>
              <Button variant="outline" onClick={() => setAddDialogOpen(false)}>إلغاء</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-md" dir="rtl">
          <DialogHeader>
            <DialogTitle>تعديل المستخدم</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>الاسم الكامل</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div>
              <Label>البريد الإلكتروني</Label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              />
            </div>
            <div>
              <Label>الدور الوظيفي</Label>
              <Select value={formData.role} onValueChange={(v) => setFormData({ ...formData, role: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(roleLabels).map(([value, { label, icon }]) => (
                    <SelectItem key={value} value={value}>{icon} {label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2 pt-4">
              <Button onClick={handleUpdateUser} disabled={submitting} className="flex-1 bg-orange-600 hover:bg-orange-700">
                {submitting ? "جاري الحفظ..." : "حفظ التغييرات"}
              </Button>
              <Button variant="outline" onClick={() => setEditDialogOpen(false)}>إلغاء</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Assign Projects & Engineers Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="max-w-lg" dir="rtl">
          <DialogHeader>
            <DialogTitle>ربط المشرف بالمشاريع والمهندسين</DialogTitle>
          </DialogHeader>
          {selectedUser && (
            <div className="space-y-4">
              <div className="bg-slate-50 p-3 rounded-lg">
                <p className="font-medium">{selectedUser.name}</p>
                <p className="text-sm text-slate-500">{selectedUser.email}</p>
              </div>
              
              {/* Projects */}
              <div>
                <Label className="flex items-center gap-2 mb-2">
                  <Building className="w-4 h-4" />
                  المشاريع
                </Label>
                <div className="max-h-40 overflow-y-auto border rounded-lg p-2 space-y-2">
                  {projects.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center p-2">لا توجد مشاريع</p>
                  ) : (
                    projects.map((project) => (
                      <label key={project.id} className="flex items-center gap-2 p-2 hover:bg-slate-50 rounded cursor-pointer">
                        <Checkbox
                          checked={formData.assigned_projects.includes(project.id)}
                          onCheckedChange={(checked) => {
                            setFormData({
                              ...formData,
                              assigned_projects: checked
                                ? [...formData.assigned_projects, project.id]
                                : formData.assigned_projects.filter(id => id !== project.id)
                            });
                          }}
                        />
                        <span className="text-sm">{project.name}</span>
                      </label>
                    ))
                  )}
                </div>
              </div>

              {/* Engineers */}
              <div>
                <Label className="flex items-center gap-2 mb-2">
                  <Briefcase className="w-4 h-4" />
                  المهندسين
                </Label>
                <div className="max-h-40 overflow-y-auto border rounded-lg p-2 space-y-2">
                  {engineers.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center p-2">لا يوجد مهندسين</p>
                  ) : (
                    engineers.map((eng) => (
                      <label key={eng.id} className="flex items-center gap-2 p-2 hover:bg-slate-50 rounded cursor-pointer">
                        <Checkbox
                          checked={formData.assigned_engineers.includes(eng.id)}
                          onCheckedChange={(checked) => {
                            setFormData({
                              ...formData,
                              assigned_engineers: checked
                                ? [...formData.assigned_engineers, eng.id]
                                : formData.assigned_engineers.filter(id => id !== eng.id)
                            });
                          }}
                        />
                        <span className="text-sm">{eng.name}</span>
                      </label>
                    ))
                  )}
                </div>
              </div>

              <div className="flex gap-2 pt-4">
                <Button onClick={handleUpdateAssignments} disabled={submitting} className="flex-1 bg-orange-600 hover:bg-orange-700">
                  {submitting ? "جاري الحفظ..." : "حفظ الربط"}
                </Button>
                <Button variant="outline" onClick={() => setAssignDialogOpen(false)}>إلغاء</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={resetPasswordDialogOpen} onOpenChange={setResetPasswordDialogOpen}>
        <DialogContent className="max-w-sm" dir="rtl">
          <DialogHeader>
            <DialogTitle>إعادة تعيين كلمة المرور</DialogTitle>
          </DialogHeader>
          {selectedUser && (
            <div className="space-y-4">
              <div className="bg-slate-50 p-3 rounded-lg">
                <p className="font-medium">{selectedUser.name}</p>
                <p className="text-sm text-slate-500">{selectedUser.email}</p>
              </div>
              <div>
                <Label>كلمة المرور الجديدة</Label>
                <div className="relative">
                  <Input
                    type={showPassword ? "text" : "password"}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-xs text-slate-500 mt-1">يجب أن تكون 6 أحرف على الأقل</p>
              </div>
              <div className="flex gap-2 pt-2">
                <Button onClick={handleResetPassword} disabled={submitting} className="flex-1 bg-orange-600 hover:bg-orange-700">
                  {submitting ? "جاري التغيير..." : "تغيير كلمة المرور"}
                </Button>
                <Button variant="outline" onClick={() => setResetPasswordDialogOpen(false)}>إلغاء</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Dialog>
  );
}
