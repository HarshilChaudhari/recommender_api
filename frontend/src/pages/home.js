import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Cookies from 'js-cookie';
import { fetchWithAuth } from '../utils/api';
import { jwtDecode } from 'jwt-decode';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState('all');
  const [allMovies, setAllMovies] = useState([]);
  const [likedMovies, setLikedMovies] = useState([]);
  const [recommendedMovies, setRecommendedMovies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const router = useRouter();

  useEffect(() => {
    const token = Cookies.get('token');
    if (!token) {
      router.push('/login');
      return;
    }

    if (searchQuery) return; // Don't fetch normal data if searching

    setLoading(true);
    setError('');
    let fetchFn;
    if (activeTab === 'all') {
      fetchFn = () => fetchWithAuth(`/movies?page=${page}`);
    } else if (activeTab === 'liked') {
      fetchFn = () => fetchWithAuth('/liked');
    } else if (activeTab === 'recommended') {
      fetchFn = () => fetchWithAuth('/recommend');
    }

    fetchFn()
      .then(data => {
        if (activeTab === 'all') setAllMovies(data.movies || []);
        if (activeTab === 'liked') setLikedMovies(data);
        if (activeTab === 'recommended') setRecommendedMovies(data);
        setLoading(false);
      })
      .catch(e => {
        setError('Failed to load movies');
        setLoading(false);
      });
  }, [activeTab, page, router, searchQuery]);

  const handleLogout = () => {
    Cookies.remove('token');
    router.push('/login');
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError('');
    try {
      const results = await fetchWithAuth(
        `/search?query=${encodeURIComponent(searchQuery)}&scope=${activeTab}`
      );
      setSearchResults(results);
    } catch (e) {
      setError('Search failed');
    }
    setLoading(false);
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults(null);
  };

  const getUserIdFromToken = () => {
    const token = Cookies.get('token');
    if (!token) return null;
    try {
      const decoded = jwtDecode(token);
      return decoded.user_id;
    } catch {
      return null;
    }
  };

  const handleDislike = async (movie) => {
    setLoading(true);
    setError('');
    try {
      const user_id = getUserIdFromToken();
      await fetchWithAuth('/dislike', {
        method: 'POST',
        body: JSON.stringify({ user_id, movie_title: movie.title, tmdb_id: movie.tmdb_id }),
      });
      // Refresh liked movies after disliking
      const updatedLiked = await fetchWithAuth('/liked');
      setLikedMovies(updatedLiked);
      // Optionally, refresh recommendations as well
      if (activeTab === 'recommended') {
        const updatedRecommended = await fetchWithAuth('/recommend');
        setRecommendedMovies(updatedRecommended);
      }
    } catch (e) {
      setError('Failed to dislike movie');
    }
    setLoading(false);
  };

  const handleLike = async (movie) => {
    setLoading(true);
    setError('');
    try {
      const user_id = getUserIdFromToken();
      await fetchWithAuth('/like', {
        method: 'POST',
        body: JSON.stringify({ user_id, movie_title: movie.title, tmdb_id: movie.tmdb_id }),
      });
      // Refresh liked movies after liking
      const updatedLiked = await fetchWithAuth('/liked');
      setLikedMovies(updatedLiked);
      // Optionally, refresh recommendations as well
      if (activeTab === 'recommended') {
        const updatedRecommended = await fetchWithAuth('/recommend');
        setRecommendedMovies(updatedRecommended);
      }
    } catch (e) {
      setError('Failed to like movie');
    }
    setLoading(false);
  };

  // Choose which list to display
  let displayList = [];
  if (searchResults !== null) {
    displayList = searchResults;
  } else if (activeTab === 'all') {
    displayList = allMovies;
  } else if (activeTab === 'liked') {
    displayList = likedMovies;
  } else if (activeTab === 'recommended') {
    displayList = recommendedMovies;
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
        <button onClick={() => { setActiveTab('all'); setPage(1); handleClearSearch(); }} style={{ fontWeight: activeTab === 'all' ? 'bold' : 'normal' }}>
          All Movies
        </button>
        <button onClick={() => { setActiveTab('liked'); handleClearSearch(); }} style={{ fontWeight: activeTab === 'liked' ? 'bold' : 'normal' }}>
          Liked Movies
        </button>
        <button onClick={() => { setActiveTab('recommended'); handleClearSearch(); }} style={{ fontWeight: activeTab === 'recommended' ? 'bold' : 'normal' }}>
          Recommended Movies
        </button>
        <button onClick={handleLogout} style={{ marginLeft: 'auto' }}>Logout</button>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} style={{ marginBottom: '1rem' }}>
        <input
          type="text"
          placeholder={`Search in ${activeTab}...`}
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          style={{ width: '60%', marginRight: '1rem' }}
        />
        <button type="submit">Search</button>
        {searchResults !== null && (
          <button type="button" onClick={handleClearSearch} style={{ marginLeft: '1rem' }}>
            Clear Search
          </button>
        )}
      </form>

      {loading && <div>Loading...</div>}
      {error && <div style={{ color: 'red' }}>{error}</div>}

        {activeTab === 'liked' ? (
          <div>
            <h2>Liked Movies</h2>
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {displayList.map((movie, idx) => (
                <li key={idx} style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center' }}>
                  <img
                    src={`https://image.tmdb.org/t/p/w200${movie.poster_path}`}
                    alt={movie.title}
                    style={{ width: '100px', marginRight: '1rem', borderRadius: '8px' }}
                  />
                  <div>
                    <strong>{movie.title}</strong> – {movie.genres.join(', ')}
                  <div><em>Release Date:</em> {movie.release_date}</div>
                  <div style={{ maxWidth: '400px' }}>{movie.overview}</div>
                  {activeTab === 'recommended' && movie.score !== undefined && (
                    <div>Score: {movie.score.toFixed(3)}</div>
                  )}
                    <div>
                      <button onClick={() => handleDislike(movie)} style={{ marginTop: '0.5rem' }}>
                        Dislike
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ) : (

        <ul style={{ listStyle: 'none', padding: 0 }}>
          {displayList.map((movie, idx) => (
            <li key={idx} style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center' }}>
              <img
                src={`https://image.tmdb.org/t/p/w200${movie.poster_path}`}
                alt={movie.title}
                style={{ width: '100px', marginRight: '1rem', borderRadius: '8px' }}
              />
              <div>
                <strong>{movie.title}</strong> – {movie.genres.join(', ')}
              <div><em>Release Date:</em> {movie.release_date}</div>
              <div style={{ maxWidth: '400px' }}>{movie.overview}</div>
              {activeTab === 'recommended' && movie.score !== undefined && (
                <div>Score: {movie.score.toFixed(3)}</div>
              )}
                
                {(activeTab === 'all' || activeTab === 'recommended') && (
                  <div>
                    <button onClick={() => handleLike(movie)} style={{ marginTop: '0.5rem' }}>
                      Like
                    </button>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>

      )}

      {/* Pagination for All Movies */}
      {activeTab === 'all' && searchResults === null && (
        <div>
          <button onClick={() => setPage(page => Math.max(1, page - 1))} disabled={page === 1}>Previous</button>
          <span> Page {page} </span>
          <button onClick={() => setPage(page => page + 1)}>Next</button>
        </div>
      )}
    </div>
  );
}

