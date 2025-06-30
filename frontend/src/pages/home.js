import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Cookies from 'js-cookie';
import { fetchWithAuth } from '../utils/api';
import { jwtDecode } from 'jwt-decode';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState('all');
  const [allMovies, setAllMovies] = useState([]);
  const [likedMovies, setLikedMovies] = useState([]);
  const [dislikedMovies, setDislikedMovies] = useState([]);
  const [recommendedMovies, setRecommendedMovies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const router = useRouter();

  const pageSize = 20;

  const getUserIdFromToken = () => {
    const token = Cookies.get('token');
    if (!token) return null;
    try {
      return jwtDecode(token).user_id;
    } catch {
      return null;
    }
  };

  const refreshAllData = async () => {
    const [liked, disliked, recommended] = await Promise.all([
      fetchWithAuth(`/liked?page=1&page_size=1000`),
      fetchWithAuth(`/disliked?page=1&page_size=1000`),
      fetchWithAuth(`/recommend?page=1&page_size=${pageSize}`)
    ]);
    setLikedMovies(liked.movies || []);
    setDislikedMovies(disliked.movies || []);
    setRecommendedMovies(recommended.movies || []);
  };

  useEffect(() => {
    const token = Cookies.get('token');
    if (!token) {
      router.push('/login');
      return;
    }

    if (searchQuery) return;

    const fetchData = async () => {
      setLoading(true);
      setError('');
      try {
        await refreshAllData(); // Fetch liked/disliked first
        let fetchUrl = '';
        if (activeTab === 'all') fetchUrl = `/movies?page=${page}`;
        else if (activeTab === 'liked') fetchUrl = `/liked?page=${page}&page_size=${pageSize}`;
        else if (activeTab === 'recommended') fetchUrl = `/recommend?page=${page}&page_size=${pageSize}`;
        else if (activeTab === 'disliked') fetchUrl = `/disliked?page=${page}&page_size=${pageSize}`;

        const data = await fetchWithAuth(fetchUrl);
        if (activeTab === 'all') setAllMovies(data.movies || []);
        if (activeTab === 'liked') setLikedMovies(data.movies || []);
        if (activeTab === 'recommended') setRecommendedMovies(data.movies || []);
        if (activeTab === 'disliked') setDislikedMovies(data.movies || []);
      } catch {
        setError('Failed to load movies');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
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
      const results = await fetchWithAuth(`/search?query=${encodeURIComponent(searchQuery)}&scope=${activeTab}`);
      setSearchResults(results);
    } catch {
      setError('Search failed');
    }
    setLoading(false);
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults(null);
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
      await refreshAllData();
    } catch {
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
      await refreshAllData();
    } catch {
      setError('Failed to like movie');
    }
    setLoading(false);
  };

  const handleUndoDislike = async (movie) => {
    setLoading(true);
    setError('');
    try {
      const user_id = getUserIdFromToken();
      await fetchWithAuth('/undislike', {
        method: 'POST',
        body: JSON.stringify({ user_id, movie_title: movie.title, tmdb_id: movie.tmdb_id }),
      });
      await refreshAllData();
    } catch {
      setError('Failed to undo dislike');
    }
    setLoading(false);
  };

  const getDisplayList = () => {
    if (searchResults !== null) return searchResults;
    if (activeTab === 'all') return allMovies;
    if (activeTab === 'liked') return likedMovies;
    if (activeTab === 'recommended') return recommendedMovies;
    if (activeTab === 'disliked') return dislikedMovies;
    return [];
  };

  const isLiked = (tmdb_id) => likedMovies.some(m => m.tmdb_id === tmdb_id);
  const isDisliked = (tmdb_id) => dislikedMovies.some(m => m.tmdb_id === tmdb_id);

  return (
    <div>
      {/* Navigation */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
        {['all', 'liked', 'recommended', 'disliked'].map(tab => (
          <button
            key={tab}
            onClick={() => { setActiveTab(tab); setPage(1); handleClearSearch(); }}
            style={{ fontWeight: activeTab === tab ? 'bold' : 'normal' }}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)} Movies
          </button>
        ))}
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
        {searchResults && (
          <button type="button" onClick={handleClearSearch} style={{ marginLeft: '1rem' }}>
            Clear
          </button>
        )}
      </form>

      {loading && <div>Loading...</div>}
      {error && <div style={{ color: 'red' }}>{error}</div>}

      <ul style={{ listStyle: 'none', padding: 0 }}>
        {getDisplayList().map((movie, idx) => (
          <li key={idx} style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center' }}>
            <img
              src={`https://image.tmdb.org/t/p/w200${movie.poster_path}`}
              alt={movie.title}
              style={{ width: '100px', marginRight: '1rem', borderRadius: '8px' }}
            />
            <div>
              <strong>{movie.title}</strong> – {movie.genres.join(', ')}
              <div><em>Release:</em> {movie.release_date}</div>
              <div style={{ maxWidth: '400px' }}>{movie.overview}</div>
              {movie.score !== undefined && <div>Score: {movie.score.toFixed(3)}</div>}

              <div style={{ marginTop: '0.5rem' }}>
                {activeTab === 'disliked' ? (
                  <button onClick={() => handleUndoDislike(movie)}>Undo Dislike</button>
                ) : (
                  <>
                    {isLiked(movie.tmdb_id) && (
                      <span style={{ marginRight: '0.5rem', color: 'green' }}>✔ Liked</span>
                    )}
                    {!isLiked(movie.tmdb_id) && (
                      <button onClick={() => handleLike(movie)} style={{ marginRight: '0.5rem' }}>
                        Like
                      </button>
                    )}

                    {isDisliked(movie.tmdb_id) ? (
                      <span style={{ color: 'red' }}>✖ Disliked</span>
                    ) : (
                      <button onClick={() => handleDislike(movie)}>Dislike</button>
                    )}
                  </>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>

      {/* Pagination */}
      {searchResults === null && (
        <div>
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>Previous</button>
          <span> Page {page} </span>
          <button onClick={() => setPage(p => p + 1)}>Next</button>
        </div>
      )}
    </div>
  );
}

