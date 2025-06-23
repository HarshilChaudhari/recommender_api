import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Cookies from 'js-cookie';
import { fetchWithAuth } from '../utils/api';

export default function HomePage() {
  const [popular, setPopular] = useState([]);
  const router = useRouter();

  useEffect(() => {
    const token = Cookies.get('token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/popular`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(setPopular)
      .catch(() => {
        alert('Failed to load popular movies');
        router.push('/login');
      });
  }, []);

  const handleLogout = () => {
    Cookies.remove('token');
    router.push('/login');
  };

  return (
    <div>
      <h2>Popular Movies</h2>
      <ul>
        {popular.map((movie, index) => (
          <li key={index}>
            <strong>{movie.title}</strong> – {movie.genres.join(', ')}
          </li>
        ))}
      </ul>
      <button onClick={handleLogout}>Logout</button>
    </div>
  );
}

