import Cookies from 'js-cookie';

export async function fetchWithAuth(path, options = {}) {
  const token = Cookies.get('token');
  const headers = {
    'Content-Type': 'application/json',
    "ngrok-skip-browser-warning": "true",
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
    let errorDetail = 'API request failed';
    try {
      // Attempt to parse the response as JSON
      const errorData = await res.json();
      // Use 'detail' property if available, otherwise stringify the whole object
      errorDetail = errorData.detail || JSON.stringify(errorData);
    } catch (e) {
      // If JSON parsing fails, get the response as plain text
      errorDetail = await res.text();
      // If text is also empty, use the status text or a generic message
      if (!errorDetail) {
          errorDetail = res.statusText || `Error ${res.status}`;
      }
    }
    // Throw a more informative error
    throw new Error(`Error: ${res.status} - ${errorDetail}`);
  }

  // If the response is OK, always try to parse it as JSON
  return res.json();
}
