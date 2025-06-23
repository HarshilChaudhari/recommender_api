import Cookies from 'js-cookie';

export async function fetchWithAuth(path, options = {}) {
  const token = Cookies.get('token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'API request failed');
  }

  return res.json();
}

