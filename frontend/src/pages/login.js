import { useState } from 'react';
import { useRouter } from 'next/router';
import Cookies from 'js-cookie';
import Link from 'next/link';

// Import local CSS module
import styles from './login.module.css'; // Make sure this path is correct

export default function LoginPage() {
  const [user_id, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(''); // State for error messages
  const [loading, setLoading] = useState(false); // State for loading
  const router = useRouter();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError(''); // Clear previous errors
    setLoading(true); // Set loading state

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id, password })
      });

      if (!res.ok) {
        const errorData = await res.json();
        // Use error.detail from FastAPI if available, otherwise generic message
        throw new Error(errorData.detail || 'Authentication failed. Please check your credentials.');
      }

      const data = await res.json();
      Cookies.set('token', data.token, { expires: 7 }); // Set cookie to expire in 7 days
      router.push('/home'); // Redirect on successful login
    } catch (err) {
      setError(err.message || 'An unexpected error occurred during login.');
    } finally {
      setLoading(false); // Clear loading state
    }
  };

  return (
    <div className={styles.loginContainer}>
      <h2>Login</h2>
      <form onSubmit={handleLogin} className={styles.loginForm}>
        {error && <p className={styles.errorMessage}>{error}</p>} {/* Display error message */}
        <div className={styles.inputGroup}>
          <input
            type="text"
            placeholder="Username"
            value={user_id}
            onChange={(e) => setUserId(e.target.value)}
            required
            className={styles.inputField}
            aria-label="Username"
          />
        </div>
        <div className={styles.inputGroup}>
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className={styles.inputField}
            aria-label="Password"
          />
        </div>
        <button 
          type="submit" 
          className={styles.loginButton} 
          disabled={loading} // Disable button when loading
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      <p className={styles.signupText}>
        Don't have an account? {' '}
        <Link href="/signup" className={styles.signupLink}>
          Sign up
        </Link>
      </p>
    </div>
  );
}
