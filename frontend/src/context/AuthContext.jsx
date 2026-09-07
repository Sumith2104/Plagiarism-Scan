import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI } from '../api';
import { useNotification } from './NotificationContext';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const notify = useNotification();

  const fetchCurrentUser = useCallback(async () => {
    const savedToken = localStorage.getItem('token');
    if (!savedToken) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const response = await authAPI.getMe();
      setUser(response.data);
    } catch (err) {
      console.warn('Session expired or invalid token:', err);
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  const login = async (email, password) => {
    try {
      const response = await authAPI.login(email, password);
      const accessToken = response.data.access_token;
      localStorage.setItem('token', accessToken);
      setToken(accessToken);

      // Fetch user profile immediately
      try {
        const meRes = await authAPI.getMe();
        setUser(meRes.data);
        notify.success(
          'Welcome to PlagiaScan!',
          `Signed in as ${meRes.data.full_name || meRes.data.email}`
        );
      } catch {
        setUser({ email });
        notify.success('Welcome!', 'Authentication successful.');
      }

      return response.data;
    } catch (err) {
      const detail = err.response?.data?.detail || 'Authentication failed. Please check your credentials.';
      notify.error('Sign In Failed', detail);
      throw err;
    }
  };

  const register = async (email, password, fullName) => {
    try {
      const response = await authAPI.register(email, password, fullName);
      if (response.data?.access_token) {
        // Auto-login with received token
        const accessToken = response.data.access_token;
        localStorage.setItem('token', accessToken);
        setToken(accessToken);
        setUser({
          id: response.data.id,
          email: response.data.email,
          full_name: response.data.full_name || fullName,
          role: 'user',
        });
        notify.success(
          'Account Created!',
          `Welcome to PlagiaScan, ${fullName || email}! Your workspace is ready.`
        );
      } else {
        notify.success(
          'Registration Successful!',
          'Your account has been created. Please sign in.'
        );
      }
      return response.data;
    } catch (err) {
      const detail = err.response?.data?.detail || 'Registration failed. Please try again.';
      notify.error('Registration Failed', detail);
      throw err;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    notify.info('Logged Out', 'You have been safely signed out of your PlagiaScan session.');
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: Boolean(token && user),
    login,
    register,
    logout,
    refreshUser: fetchCurrentUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
