import { useState } from 'react';
import { useRouter } from 'next/router';
import Cookies from 'js-cookie';
import Link from 'next/link';

export default function LoginPage() {
  const [user_id, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const router = useRouter();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id, password })
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail);
      }

      const data = await res.json();
      Cookies.set('token', data.token);
      router.push('/home');
    } catch (err) {
      alert('Login failed: ' + err + user_id + password);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '400px', margin: 'auto' }}>
      <h2>Login</h2>
      <form onSubmit={handleLogin}>
        <input
          type="text"
          placeholder="Username"
          value={user_id}
          onChange={(e) => setUserId(e.target.value)}
          required
          style={{ display: 'block', marginBottom: '1rem', width: '100%' }}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={{ display: 'block', marginBottom: '1rem', width: '100%' }}
        />
        <button type="submit" style={{ width: '100%' }}>Login</button>
      </form>

      <p style={{ marginTop: '1rem' }}>
        Don't have an account? <Link href="/signup">Sign up</Link>
      </p>
    </div>
  );
}

