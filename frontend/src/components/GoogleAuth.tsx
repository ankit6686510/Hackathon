import React, { useEffect, useState, useCallback } from 'react';

declare global {
  interface Window {
    google: any;
    gapi: any;
  }
}

interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  given_name?: string;
  family_name?: string;
}

interface GoogleAuthProps {
  onLoginSuccess: (user: User, token: string) => void;
  onLogoutSuccess: () => void;
  user: User | null;
}

const GoogleAuth: React.FC<GoogleAuthProps> = ({
  onLoginSuccess,
  onLogoutSuccess,
  user
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isGoogleLoaded, setIsGoogleLoaded] = useState(false);

  // Get Google Client ID from Vite environment variables
  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || 'YOUR_GOOGLE_CLIENT_ID_HERE';

  // Load Google Identity Services
  useEffect(() => {
    const loadGoogleScript = () => {
      if (window.google) {
        setIsGoogleLoaded(true);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => {
        setIsGoogleLoaded(true);
      };
      script.onerror = () => {
        setError('Failed to load Google authentication');
      };
      document.head.appendChild(script);
    };

    loadGoogleScript();
  }, []);

  // Initialize Google Sign-In
  useEffect(() => {
    if (!isGoogleLoaded || !clientId || clientId === 'YOUR_GOOGLE_CLIENT_ID_HERE') {
      if (clientId === 'YOUR_GOOGLE_CLIENT_ID_HERE') {
        setError('Google Client ID not configured');
      }
      return;
    }

    try {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleCredentialResponse,
        auto_select: false,
        cancel_on_tap_outside: true,
      });

      // Render the sign-in button
      if (!user) {
        window.google.accounts.id.renderButton(
          document.getElementById('google-signin-button'),
          {
            theme: 'filled_blue',
            size: 'medium',
            text: 'signin',
            shape: 'circle',
            logo_alignment: 'center',
          }
        );
      }
    } catch (error) {
      console.error('Google Sign-In initialization error:', error);
      setError('Failed to initialize Google Sign-In');
    }
  }, [isGoogleLoaded, clientId, user]);

  const handleCredentialResponse = useCallback(async (response: any) => {
    setIsLoading(true);
    setError(null);

    try {
      // Send the Google token to our backend
      const backendResponse = await fetch('http://localhost:8000/api/v1/auth/google/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies
        body: JSON.stringify({
          token: response.credential
        }),
      });

      if (!backendResponse.ok) {
        const errorData = await backendResponse.json();
        throw new Error(errorData.error?.message || 'Login failed');
      }

      const data = await backendResponse.json();
      
      if (data.success && data.user) {
        onLoginSuccess(data.user, data.access_token);
      } else {
        throw new Error(data.message || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      setError(error instanceof Error ? error.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  }, [onLoginSuccess]);

  const handleLogout = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Call our backend logout endpoint
      const response = await fetch('http://localhost:8000/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'include', // Include cookies
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error?.message || 'Logout failed');
      }

      // Sign out from Google
      if (window.google?.accounts?.id) {
        window.google.accounts.id.disableAutoSelect();
      }

      onLogoutSuccess();
    } catch (error) {
      console.error('Logout error:', error);
      setError(error instanceof Error ? error.message : 'Logout failed');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isGoogleLoaded) {
    return (
      <div className="auth-container loading">
        <div className="loading-spinner"></div>
        <p>Loading authentication...</p>
      </div>
    );
  }

  if (clientId === 'YOUR_GOOGLE_CLIENT_ID_HERE') {
    return (
      <div className="auth-error">
        <p>⚠️ Google Client ID not configured</p>
        <p>Please set GOOGLE_CLIENT_ID in your environment</p>
      </div>
    );
  }

  if (user) {
    return (
      <div className="auth-container authenticated">
        <div className="user-info">
          {user.picture && (
            <img 
              src={user.picture} 
              alt={user.name}
              className="user-avatar"
            />
          )}
          <div className="user-details">
            <span className="user-name">{user.name}</span>
            <span className="user-email">{user.email}</span>
          </div>
        </div>
        
        <button
          onClick={handleLogout}
          disabled={isLoading}
          className="logout-button"
        >
          {isLoading ? "Signing out..." : "Sign Out"}
        </button>
        
        {error && (
          <div className="auth-error">
            <p>{error}</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="auth-container unauthenticated">
      <div className="login-prompt">
        <h3>🔐 Sign in to SherlockAI</h3>
        <p>Access your personalized payment issue intelligence</p>
      </div>
      
      <div className="google-signin-wrapper">
        <div id="google-signin-button" style={{ display: 'none' }}></div>
        <button 
          className="custom-google-signin"
          onClick={() => window.google?.accounts?.id?.prompt()}
          disabled={isLoading}
          title="Sign in with Google"
        >
          {isLoading ? (
            <div className="loading-spinner"></div>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
          )}
        </button>
        {isLoading && (
          <div className="signin-loading">
            <span>Signing in...</span>
          </div>
        )}
      </div>
      
      {error && (
        <div className="auth-error">
          <p>{error}</p>
        </div>
      )}
    </div>
  );
};

export default GoogleAuth;
