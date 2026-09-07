import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { NotificationProvider } from './context/NotificationContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Report from './pages/Report';
import Verify from './pages/Verify';
import './index.css';

function ProtectedRoute({ children }) {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-white/10 p-2 mx-auto mb-4 border border-white/20 animate-pulse">
            <img src="/logo-icon.png" alt="Loading..." className="w-full h-full object-contain" />
          </div>
          <p className="text-slate-300 font-medium text-sm">Verifying PlagiaScan session...</p>
        </div>
      </div>
    );
  }

  return token ? children : <Navigate to="/" replace />;
}

function PublicAuthRoute({ children }) {
  const { token, loading } = useAuth();
  if (loading) return null;
  return token ? <Navigate to="/dashboard" replace /> : children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <PublicAuthRoute>
            <Login />
          </PublicAuthRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/report/:scanId"
        element={
          <ProtectedRoute>
            <Report />
          </ProtectedRoute>
        }
      />
      <Route path="/verify/:scanId" element={<Verify />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <NotificationProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </NotificationProvider>
    </Router>
  );
}

export default App;
