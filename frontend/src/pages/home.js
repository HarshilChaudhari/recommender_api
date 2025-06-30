import { useEffect, useState, useCallback, useRef } from 'react'; // Import useRef for potential future use, though not strictly needed for this debounce logic
import { useRouter } from 'next/router';
import Cookies from 'js-cookie';

import styles from './home.module.css';

import { fetchWithAuth } from '../utils/api';
import { jwtDecode } from 'jwt-decode';

// --- Constants ---
const PAGE_SIZE = 10;
const INITIAL_PAGE = 1;
const PAGE_RANGE = 2; // Number of pages to show around the current page
const SEARCH_DEBOUNCE_DELAY = 500; // milliseconds - wait this long after typing stops before searching
const MIN_SEARCH_LENGTH = 2; // Minimum characters required for a search query

// --- Helper Functions ---

const getUserIdFromToken = () => {
    const token = Cookies.get('token');
    if (!token) return null;
    try {
        return jwtDecode(token).user_id;
    } catch (error) {
        console.error("Error decoding token:", error);
        return null;
    }
};

/**
 * Fetches data for a specific movie category.
 * @param {string} endpoint - The API endpoint (e.g., '/movies', '/liked').
 * @param {number} page - The current page number.
 * @param {number} pageSize - The number of items per page.
 * @param {string} [query=''] - Search query (optional).
 * @param {string} [scope='all'] - Search scope (optional).
 * @returns {Promise<{movies: Array, total_results: number, total_pages: number}>} A promise that resolves to an object with movies, total_results, and total_pages.
 */
const fetchMoviesByCategory = async (endpoint, page, pageSize = PAGE_SIZE, query = '', scope = 'all') => {
    try {
        let url = `${endpoint}?page=${page}&page_size=${pageSize}`;
        if (endpoint === '/search' && query) {
            url += `&query=${encodeURIComponent(query)}&scope=${encodeURIComponent(scope)}`;
        }
        const data = await fetchWithAuth(url);

        const movies = data.movies || [];
        const total_results = data.total_results || 0;
        const total_pages = data.total_pages || 1;

        return { movies, total_results, total_pages };
    } catch (error) {
        console.error(`Failed to fetch ${endpoint}:`, error);
        // Attempt to parse a more specific error message from the API response
        let errorMessage = `Failed to load ${endpoint.substring(1)} movies.`;
        if (error.message && error.message.includes('Error: 400 -')) {
            errorMessage = error.message.split('Error: 400 - ')[1] || errorMessage;
        } else {
            errorMessage = error.message || errorMessage;
        }
        throw new Error(errorMessage);
    }
};


const handleMovieAction = async (actionEndpoint, movie) => {
    const user_id = getUserIdFromToken();
    if (!user_id) throw new Error("User not authenticated.");

    await fetchWithAuth(actionEndpoint, {
        method: 'POST',
        body: JSON.stringify({ user_id, movie_title: movie.title, tmdb_id: movie.tmdb_id }),
    });
};

// --- Custom Hooks ---

const useMovieLists = () => {
    const [allMovies, setAllMovies] = useState([]);
    const [likedMovies, setLikedMovies] = useState([]);
    const [dislikedMovies, setDislikedMovies] = useState([]);
    const [recommendedMovies, setRecommendedMovies] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const getMoviesByTab = useCallback((tab) => {
        switch (tab) {
            case 'all':
                return allMovies;
            case 'liked':
                return likedMovies;
            case 'recommended':
                return recommendedMovies;
            case 'disliked':
                return dislikedMovies;
            default:
                return [];
        }
    }, [allMovies, likedMovies, recommendedMovies, dislikedMovies]);

    return {
        allMovies,
        likedMovies,
        dislikedMovies,
        recommendedMovies,
        loading,
        setLoading,
        error,
        setError,
        setLikedMovies,
        setDislikedMovies,
        setRecommendedMovies,
        setAllMovies,
        getMoviesByTab,
    };
};

const useMovieSearch = () => {
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState(null); // null indicates no search performed yet
    const [searchTotalPages, setSearchTotalPages] = useState(1);
    const [searchPage, setSearchPage] = useState(INITIAL_PAGE);

    const handleSearch = useCallback(async (activeTab, setLoading, setError, queryToUse) => {
        // Frontend validation: if query is too short (and not empty)
        if (queryToUse.length > 0 && queryToUse.length < MIN_SEARCH_LENGTH) {
            setSearchResults(null); // Clear previous results
            setSearchTotalPages(1);
            setError(`Please type at least ${MIN_SEARCH_LENGTH} characters to search.`);
            return;
        }

        // If query is empty, clear search results and exit
        if (!queryToUse.trim()) {
            setSearchResults(null);
            setSearchTotalPages(1);
            setError(''); // Clear any previous search-related error
            return;
        }

        setLoading(true);
        setError(''); // Clear error before new search
        try {
            const results = await fetchMoviesByCategory(
                '/search',
                searchPage,
                PAGE_SIZE,
                queryToUse, // Use the debounced query
                activeTab // Pass the active tab for scoped search
            );
            setSearchResults(results.movies);
            setSearchTotalPages(results.total_pages);
        } catch (error) {
            setError(`Search failed: ${error.message || 'An unknown error occurred.'}`);
            console.error("Search error:", error);
        } finally {
            setLoading(false);
        }
    }, [searchPage]); // Dependency: searchPage for pagination within search results

    const handleClearSearch = useCallback(() => {
        setSearchQuery('');
        setSearchResults(null);
        setSearchTotalPages(1);
        setSearchPage(INITIAL_PAGE);
    }, []);

    return {
        searchQuery,
        setSearchQuery,
        searchResults,
        setSearchResults,
        searchTotalPages,
        setSearchTotalPages,
        searchPage,
        setSearchPage,
        handleSearch,
        handleClearSearch,
    };
};

// --- Movie Details Modal Component ---
const MovieDetailsModal = ({ movie, onClose }) => {
    if (!movie) return null;

    return (
        <div className={styles.modalOverlay} onClick={onClose}>
            <div className={styles.modalContent} onClick={e => e.stopPropagation()}>
                <button className={styles.modalCloseButton} onClick={onClose}>&times;</button>
                <img
                    src={movie.poster_path ? `https://image.tmdb.org/t/p/w300${movie.poster_path}` : 'https://via.placeholder.com/250x375?text=No+Poster'}
                    alt={movie.title}
                    className={styles.modalMoviePoster}
                />
                <div className={styles.modalMovieDetails}>
                    <h3>{movie.title}</h3>
                    <div><span className={styles.modalDetailsEm}>Genres:</span> {movie.genres?.join(', ') || 'N/A'}</div>
                    <div><span className={styles.modalDetailsEm}>Release Date:</span> {movie.release_date || 'N/A'}</div>
                    {movie.score !== undefined && <div><span className={styles.modalDetailsEm}>Recommendation Score:</span> {movie.score.toFixed(3)}</div>}
                    <p>{movie.overview || 'No overview available.'}</p>
                </div>
            </div>
        </div>
    );
};


export default function HomePage() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('all');
    const [page, setPage] = useState(INITIAL_PAGE);
    const [totalPages, setTotalPages] = useState(1);

    const [selectedMovie, setSelectedMovie] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const {
        allMovies,
        likedMovies,
        dislikedMovies,
        recommendedMovies,
        loading,
        setLoading,
        error,
        setError,
        setLikedMovies,
        setDislikedMovies,
        setRecommendedMovies,
        setAllMovies,
        getMoviesByTab,
    } = useMovieLists();

    const {
        searchQuery,
        setSearchQuery,
        searchResults,
        setSearchResults,
        searchTotalPages,
        setSearchTotalPages,
        searchPage,
        setSearchPage,
        handleSearch, // This is the debounced search handler
        handleClearSearch,
    } = useMovieSearch();

    // Helper to get current list and its total pages
    const getCurrentDisplayData = useCallback(() => {
        if (searchResults !== null) { // If searchResults is not null, we are in search mode
            return { movies: searchResults, totalPages: searchTotalPages };
        }
        // Otherwise, display movies based on the active tab
        return { movies: getMoviesByTab(activeTab), totalPages: totalPages };
    }, [searchResults, searchTotalPages, getMoviesByTab, activeTab, totalPages]);


    // Fetches liked and disliked movies for immediate display (used for `isLiked`/`isDisliked` checks)
    const refreshAllData = useCallback(async () => {
        setLoading(true);
        setError('');
        try {
            const [likedResponse, dislikedResponse] = await Promise.all([
                fetchMoviesByCategory('/liked', INITIAL_PAGE, 1000), // Fetch all liked for quick lookup
                fetchMoviesByCategory('/disliked', INITIAL_PAGE, 1000), // Fetch all disliked for quick lookup
            ]);
            setLikedMovies(likedResponse.movies);
            setDislikedMovies(dislikedResponse.movies);
        } catch (err) {
            setError(err.message || 'Failed to refresh movie data.');
        } finally {
            setLoading(false);
        }
    }, [setLoading, setError, setLikedMovies, setDislikedMovies]);

    // --- Main Data Fetching Effect (Triggers on tab/page change OR initial load, NOT directly on search query change) ---
    useEffect(() => {
        const token = Cookies.get('token');
        if (!token) {
            router.push('/login');
            return;
        }

        const fetchData = async () => {
            setLoading(true);
            setError(''); // Clear error before new fetch

            try {
                // Always refresh liked/disliked data regardless of active tab or search
                await refreshAllData();

                // If there's an active search query (and it's valid for search), don't fetch by tab
                // The debounced useEffect will handle searching.
                if (searchQuery.trim().length >= MIN_SEARCH_LENGTH) {
                    // Do nothing here, the debounced search useEffect will trigger `handleSearch`
                    // and update searchResults. We just ensure `loading` is set correctly.
                    setLoading(false);
                    return;
                } else if (searchQuery.length > 0 && searchQuery.length < MIN_SEARCH_LENGTH) {
                    // If search query is present but too short, don't fetch anything by tab
                    // and show the specific error.
                    setLoading(false);
                    setError(`Please type at least ${MIN_SEARCH_LENGTH} characters to search.`);
                    return;
                } else {
                    // If no search query, or query is empty (cleared search), fetch by active tab
                    let fetchUrl = '';
                    if (activeTab === 'all') fetchUrl = `/movies`;
                    else if (activeTab === 'liked') fetchUrl = `/liked`;
                    else if (activeTab === 'recommended') fetchUrl = `/recommend`;
                    else if (activeTab === 'disliked') fetchUrl = `/disliked`;

                    const data = await fetchMoviesByCategory(fetchUrl, page, PAGE_SIZE);
                    if (activeTab === 'all') {
                        setAllMovies(data.movies);
                    } else if (activeTab === 'liked') {
                        setLikedMovies(data.movies);
                    } else if (activeTab === 'recommended') {
                        setRecommendedMovies(data.movies);
                    } else if (activeTab === 'disliked') {
                        setDislikedMovies(data.movies);
                    }
                    setTotalPages(data.total_pages);
                }

            } catch (err) {
                setError(err.message || 'Failed to load movies.');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [
        activeTab,
        page,
        router,
        searchQuery, // This dependency causes `fetchData` to re-run when searchQuery changes
                     // but the logic inside now correctly distinguishes between search-driven and tab-driven fetches.
        searchPage,
        refreshAllData,
        setLoading,
        setError,
        setAllMovies,
        setLikedMovies,
        setRecommendedMovies,
        setDislikedMovies,
        setSearchResults,
        setSearchTotalPages,
        totalPages
    ]);


    // --- Debouncing Effect for Search Query ---
    useEffect(() => {
        // No debounce needed on initial render if searchQuery is empty.
        // It should only start debouncing if searchQuery actually changes from empty, or changes to a new value.
        // We use a timeout to delay the `handleSearch` call.
        const handler = setTimeout(() => {
            // Only trigger search if query meets min length OR is empty (to clear results)
            if (searchQuery.length >= MIN_SEARCH_LENGTH || searchQuery.length === 0) {
                // Pass `searchQuery` directly to `handleSearch` to ensure it uses the latest debounced value.
                handleSearch(activeTab, setLoading, setError, searchQuery);
            } else {
                // If query is present but too short, provide immediate feedback
                setSearchResults(null); // Clear any previous search results
                setError(`Please type at least ${MIN_SEARCH_LENGTH} characters to search.`);
            }
        }, SEARCH_DEBOUNCE_DELAY);

        // Cleanup function: This is crucial. If `searchQuery` changes again before `SEARCH_DEBOUNCE_DELAY`
        // passes, the previous timeout is cleared, preventing stale requests.
        return () => {
            clearTimeout(handler);
        };
    }, [searchQuery, activeTab, handleSearch, setLoading, setError, setSearchResults]); // Dependencies for debounce


    // Define isLiked and isDisliked inside HomePage where likedMovies and dislikedMovies are accessible
    const isLiked = useCallback((tmdb_id) => likedMovies.some(m => m.tmdb_id === tmdb_id), [likedMovies]);
    const isDisliked = useCallback((tmdb_id) => dislikedMovies.some(m => m.tmdb_id === tmdb_id), [dislikedMovies]);

    // Handlers for movie actions (like/dislike/undo)
    const handleMovieActionAndRefresh = useCallback(async (actionEndpoint, movie) => {
        setLoading(true);
        setError('');
        try {
            await handleMovieAction(actionEndpoint, movie);
            await refreshAllData(); // Refresh all lists after action

            // After action, intelligently re-fetch or re-search based on current state
            if (searchQuery.trim().length >= MIN_SEARCH_LENGTH) {
                // If we're in search mode with a valid query, re-run the search
                // Use the debounced `handleSearch` to ensure proper state updates.
                await handleSearch(activeTab, setLoading, setError, searchQuery);
            } else {
                // Otherwise, re-fetch the current active tab's movies
                const currentTabEndpoint =
                    activeTab === 'all' ? '/movies' :
                        activeTab === 'liked' ? '/liked' :
                            activeTab === 'recommended' ? '/recommend' :
                                '/disliked';

                const data = await fetchMoviesByCategory(currentTabEndpoint, page, PAGE_SIZE);
                if (activeTab === 'all') setAllMovies(data.movies);
                else if (activeTab === 'liked') setLikedMovies(data.movies);
                else if (activeTab === 'recommended') setRecommendedMovies(data.movies);
                else if (activeTab === 'disliked') setDislikedMovies(data.movies);
                setTotalPages(data.total_pages);
            }

        } catch (err) {
            setError(err.message || `Failed to perform action: ${actionEndpoint}`);
        } finally {
            setLoading(false);
        }
    }, [setLoading, setError, refreshAllData, activeTab, page, setAllMovies, setLikedMovies, setRecommendedMovies, setDislikedMovies, setTotalPages, searchQuery, handleSearch]);


    const handleLike = useCallback((movie) => handleMovieActionAndRefresh('/like', movie), [handleMovieActionAndRefresh]);
    const handleDislike = useCallback((movie) => handleMovieActionAndRefresh('/dislike', movie), [handleMovieActionAndRefresh]);
    const handleUndoDislike = useCallback((movie) => handleMovieActionAndRefresh('/undislike', movie), [handleMovieActionAndRefresh]);

    const handleLogout = useCallback(() => {
        Cookies.remove('token');
        router.push('/login');
    }, [router]);

    const handleMovieClick = (movie) => {
        setSelectedMovie(movie);
        setIsModalOpen(true);
    };

    const handleCloseModal = () => {
        setIsModalOpen(false);
        setSelectedMovie(null);
    };

    const displayData = getCurrentDisplayData();
    const currentMovies = displayData.movies;
    const currentTotalPages = displayData.totalPages;
    // Determine the current page state variable (either `searchPage` or `page`)
    const currentPage = searchResults !== null ? searchPage : page;

    // --- Pagination Logic ---
    const renderPaginationButtons = () => {
        const buttons = [];
        // Use the correct setState for pagination based on whether we are in search mode
        const paginationSetPage = searchResults !== null ? setSearchPage : setPage;

        const startPage = Math.max(INITIAL_PAGE, currentPage - PAGE_RANGE);
        const endPage = Math.min(currentTotalPages, currentPage + PAGE_RANGE);

        if (startPage > INITIAL_PAGE) {
            buttons.push(
                <button
                    key={INITIAL_PAGE}
                    className={styles.paginationButton}
                    onClick={() => paginationSetPage(INITIAL_PAGE)}
                >
                    {INITIAL_PAGE}
                </button>
            );
            if (startPage > INITIAL_PAGE + 1) {
                buttons.push(<span key="ellipsis-start" className={styles.pageEllipsis}>...</span>);
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            buttons.push(
                <button
                    key={i}
                    className={`${styles.paginationButton} ${i === currentPage ? styles.activePage : ''}`}
                    onClick={() => paginationSetPage(i)}
                >
                    {i}
                </button>
            );
        }

        if (endPage < currentTotalPages) {
            if (endPage < currentTotalPages - 1) {
                buttons.push(<span key="ellipsis-end" className={styles.pageEllipsis}>...</span>);
            }
            buttons.push(
                <button
                    key={currentTotalPages}
                    className={styles.paginationButton}
                    onClick={() => paginationSetPage(currentTotalPages)}
                >
                    {currentTotalPages}
                </button>
            );
        }

        return buttons;
    };


    return (
        <div className={styles.container}>
            <header className={styles.header}>
                <nav className={styles.navTabs}>
                    {['all', 'liked', 'recommended', 'disliked'].map(tab => (
                        <button
                            key={tab}
                            className={`${styles.navButton} ${activeTab === tab ? styles.active : ''}`}
                            onClick={() => {
                                setActiveTab(tab);
                                setPage(INITIAL_PAGE);
                                setSearchPage(INITIAL_PAGE);
                                handleClearSearch(); // Clear search results and query when switching tabs
                            }}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)} Movies
                        </button>
                    ))}
                </nav>
                <button onClick={handleLogout} className={styles.logoutButton}>
                    Logout
                </button>
            </header>

            <form onSubmit={(e) => { e.preventDefault(); /* Debouncing handles submission, or manual click below */ }} className={styles.searchForm}>
                <input
                    type="text"
                    placeholder={`Search in ${activeTab}...`}
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    className={styles.searchInput}
                />
                <button
                    type="submit"
                    className={styles.searchButton}
                    disabled={loading || (searchQuery.length > 0 && searchQuery.length < MIN_SEARCH_LENGTH)}
                    onClick={() => {
                        // Allow manual submission for queries that meet criteria, bypassing debounce
                        if (searchQuery.trim().length >= MIN_SEARCH_LENGTH) {
                            handleSearch(activeTab, setLoading, setError, searchQuery);
                        } else if (searchQuery.length === 0) {
                             // If search input is empty, manual click should just clear search
                            handleClearSearch();
                        } else {
                            setError(`Please type at least ${MIN_SEARCH_LENGTH} characters to search.`);
                            setSearchResults(null); // Clear previous search results if query is too short
                        }
                    }}
                >
                    Search
                </button>
                {/* Conditionally render Clear Search button only if there are search results or a query exists */}
                {(searchResults !== null || searchQuery.length > 0) && (
                    <button type="button" onClick={handleClearSearch} className={styles.clearSearchButton}>
                        Clear Search
                    </button>
                )}
            </form>

            {loading && <div className={styles.loadingMessage}>Loading...</div>}
            {error && <div className={styles.errorMessage}>{error}</div>}

            <ul className={styles.movieList}>
                {currentMovies.map((movie, idx) => (
                    <li key={movie.tmdb_id || idx} className={styles.movieItem} onClick={() => handleMovieClick(movie)}>
                        <img
                            src={movie.poster_path ? `https://image.tmdb.org/t/p/w200${movie.poster_path}` : 'https://via.placeholder.com/120x180?text=No+Poster'}
                            alt={movie.title}
                            className={styles.moviePoster}
                        />
                        <div className={styles.movieDetails}>
                            <strong>{movie.title}</strong>
                            <div><span className={styles.movieDetailsEm}>Genres:</span> {movie.genres?.join(', ') || 'N/A'}</div>
                            <div><span className={styles.movieDetailsEm}>Release:</span> {movie.release_date || 'N/A'}</div>
                            <p className={styles.movieOverview}>{movie.overview || 'No overview available.'}</p>
                            {movie.score !== undefined && <div className={styles.movieScore}>Score: {movie.score.toFixed(3)}</div>}

                            <div className={styles.movieActions} onClick={e => e.stopPropagation()}>
                                {activeTab === 'disliked' ? (
                                    <button onClick={() => handleUndoDislike(movie)} className={styles.actionButton}>Undo Dislike</button>
                                ) : (
                                    <>
                                        {isLiked(movie.tmdb_id) && (
                                            <span className={styles.statusLiked}>✔ Liked</span>
                                        )}
                                        {!isLiked(movie.tmdb_id) && (
                                            <button onClick={() => handleLike(movie)} className={styles.actionButton}>
                                                Like
                                            </button>
                                        )}

                                        {isDisliked(movie.tmdb_id) ? (
                                            <span className={styles.statusDisliked}>✖ Disliked</span>
                                        ) : (
                                            <button onClick={() => handleDislike(movie)} className={styles.actionButton}>Dislike</button>
                                        )}
                                    </>
                                )}
                            </div>
                        </div>
                    </li>
                ))}
                {currentMovies.length === 0 && !loading && !error && (
                    <div className={styles.loadingMessage}>No movies to display in this category.</div>
                )}
            </ul>

            {currentTotalPages > 1 && (
                <div className={styles.pagination}>
                    <button
                        onClick={() => (searchResults !== null ? setSearchPage(p => Math.max(INITIAL_PAGE, p - 1)) : setPage(p => Math.max(INITIAL_PAGE, p - 1)))}
                        disabled={currentPage === INITIAL_PAGE || loading}
                        className={styles.paginationButton}
                    >
                        Previous
                    </button>

                    {renderPaginationButtons()}

                    <button
                        onClick={() => (searchResults !== null ? setSearchPage(p => p + 1) : setPage(p => p + 1))}
                        disabled={currentPage === currentTotalPages || loading}
                        className={styles.paginationButton}
                    >
                        Next
                    </button>
                </div>
            )}

            <MovieDetailsModal movie={selectedMovie} onClose={handleCloseModal} />
        </div>
    );
}
