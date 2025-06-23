import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

export default function SignupPage() {
  const [user_id, setUserId] = useState('');
  const [password, setPassword] = useState('');
  const router = useRouter();

  const handleSignup = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id, password })
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail);
      }

      alert('Signup successful!');
      router.push('/login');
    } catch (err) {
      alert('Signup failed: ' + err.message);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '400px', margin: 'auto' }}>
      <h2>Signup</h2>
      <form onSubmit={handleSignup}>
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
        <button type="submit" style={{ width: '100%' }}>Signup</button>
      </form>

      <p style={{ marginTop: '1rem' }}>
        Already have an account? <Link href="/login">Login here</Link>
      </p>
    </div>
  );
}

