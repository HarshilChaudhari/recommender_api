import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

// Import local CSS module
import styles from './signup.module.css'; // Make sure this path is correct

export default function SignupPage() {
  const [user_id, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(''); // State for error messages
  const [success, setSuccess] = useState(''); // State for success messages
  const [loading, setLoading] = useState(false); // State for loading
  const router = useRouter();

  const handleSignup = async (e) => {
    e.preventDefault();
    setError(''); // Clear previous errors
    setSuccess(''); // Clear previous success messages
    setLoading(true); // Set loading state

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id, password })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Signup failed. Please try again.');
      }

      setSuccess('Signup successful! Redirecting to login...');
      // Optionally clear form fields after successful signup
      setUserId('');
      setPassword('');
      
      // Redirect after a short delay to allow success message to be seen
      setTimeout(() => {
        router.push('/login');
      }, 1500); // Redirect after 1.5 seconds
      
    } catch (err) {
      setError(err.message || 'An unexpected error occurred during signup.');
    } finally {
      setLoading(false); // Clear loading state
    }
  };

  return (
    <div className={styles.signupContainer}>
      <h2>Sign Up</h2>
      <form onSubmit={handleSignup} className={styles.signupForm}>
        {error && <p className={styles.errorMessage}>{error}</p>} {/* Display error message */}
        {success && <p className={styles.successMessage}>{success}</p>} {/* Display success message */}
        
        <div className={styles.inputGroup}>
          <input
            type="text"
            placeholder="Choose a Username"
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
            placeholder="Create a Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className={styles.inputField}
            aria-label="Password"
          />
        </div>
        <button 
          type="submit" 
          className={styles.signupButton} 
          disabled={loading} // Disable button when loading
        >
          {loading ? 'Signing up...' : 'Sign Up'}
        </button>
      </form>

      <p className={styles.loginText}>
        Already have an account? {' '}
        <Link href="/login" className={styles.loginLink}>
          Login here
        </Link>
      </p>
    </div>
  );
}
