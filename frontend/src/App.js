import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import SetupPage from "./pages/SetupPage";
import SupervisorDashboard from "./pages/SupervisorDashboard";
import EngineerDashboard from "./pages/EngineerDashboard";
import ProcurementDashboard from "./pages/ProcurementDashboard";
import PrinterDashboard from "./pages/PrinterDashboard";
import DeliveryTrackerDashboard from "./pages/DeliveryTrackerDashboard";
import GeneralManagerDashboard from "./pages/GeneralManagerDashboard";
import SystemAdminDashboard from "./pages/SystemAdminDashboard";
import { AuthProvider, useAuth } from "./context/AuthContext";
import "./App.css";

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-orange-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-slate-600 font-medium">جاري التحميل...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Redirect to appropriate dashboard based on role
    if (user.role === "system_admin") return <Navigate to="/system-admin" replace />;
    if (user.role === "supervisor") return <Navigate to="/supervisor" replace />;
    if (user.role === "engineer") return <Navigate to="/engineer" replace />;
    if (user.role === "procurement_manager") return <Navigate to="/procurement" replace />;
    if (user.role === "printer") return <Navigate to="/printer" replace />;
    if (user.role === "delivery_tracker") return <Navigate to="/delivery-tracker" replace />;
    if (user.role === "general_manager") return <Navigate to="/general-manager" replace />;
    return <Navigate to="/login" replace />;
  }

  return children;
};

const PublicRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-12 h-12 border-4 border-orange-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (user) {
    if (user.role === "system_admin") return <Navigate to="/system-admin" replace />;
    if (user.role === "supervisor") return <Navigate to="/supervisor" replace />;
    if (user.role === "engineer") return <Navigate to="/engineer" replace />;
    if (user.role === "procurement_manager") return <Navigate to="/procurement" replace />;
    if (user.role === "printer") return <Navigate to="/printer" replace />;
    if (user.role === "delivery_tracker") return <Navigate to="/delivery-tracker" replace />;
    if (user.role === "general_manager") return <Navigate to="/general-manager" replace />;
  }

  return children;
};

function App() {
  return (
    <AuthProvider>
      <div className="App" dir="rtl" lang="ar">
        <Toaster 
          position="top-center" 
          richColors 
          closeButton
          toastOptions={{
            style: {
              fontFamily: 'Cairo, sans-serif',
              direction: 'rtl'
            }
          }}
        />
        <BrowserRouter>
          <Routes>
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <LoginPage />
                </PublicRoute>
              }
            />
            <Route
              path="/register"
              element={
                <PublicRoute>
                  <RegisterPage />
                </PublicRoute>
              }
            />
            <Route
              path="/setup"
              element={<SetupPage />}
            />
            <Route
              path="/supervisor"
              element={
                <ProtectedRoute allowedRoles={["supervisor"]}>
                  <SupervisorDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/engineer"
              element={
                <ProtectedRoute allowedRoles={["engineer"]}>
                  <EngineerDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/procurement"
              element={
                <ProtectedRoute allowedRoles={["procurement_manager"]}>
                  <ProcurementDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/printer"
              element={
                <ProtectedRoute allowedRoles={["printer"]}>
                  <PrinterDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/delivery-tracker"
              element={
                <ProtectedRoute allowedRoles={["delivery_tracker"]}>
                  <DeliveryTrackerDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/general-manager"
              element={
                <ProtectedRoute allowedRoles={["general_manager"]}>
                  <GeneralManagerDashboard />
                </ProtectedRoute>
              }
            />
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </div>
    </AuthProvider>
  );
}

export default App;
