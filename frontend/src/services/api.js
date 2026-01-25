const API_BASE_URL = "http://127.0.0.1:8000";

/**
 * Helper to get the JWT token from storage.
 * Production-ready RAG apps require this for every authenticated request.
 */
const getAuthHeader = () => {
    const token = localStorage.getItem("token"); 
    return token ? { "Authorization": `Bearer ${token}` } : {};
};

/**
 * Sends a search query to the backend.
 * Returns both the AI summary and raw source matches.
 */
export const searchNotes = async (query) => {
    try {
        const response = await fetch(`${API_BASE_URL}/search`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...getAuthHeader()
            },
            body: JSON.stringify({ query })
        });

        const data = await response.json();

        if (!response.ok) {
            // If the session is invalid or expired, clear token and refresh
            if (response.status === 401) {
                localStorage.removeItem("token");
                window.location.reload(); 
            }
            throw new Error(data.detail || "Search failed");
        }

        return data; // Returns { ai_answer, matches }
    } catch (error) {
        console.error("API Error (Search):", error);
        throw error;
    }
};

/**
 * Uploads a file for AI processing.
 * Chunks, embeds, and stores the file in the FAISS index.
 */
export const uploadFile = async (file) => {
    try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(`${API_BASE_URL}/upload`, {
            method: "POST",
            headers: {
                // IMPORTANT: Browser automatically sets Content-Type boundary for FormData
                ...getAuthHeader()
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Upload failed");
        }

        return data;
    } catch (error) {
        console.error("API Error (Upload):", error);
        throw error;
    }
};

/**
 * Fetches the list of files currently indexed for the user.
 */
export const getMyFiles = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/my-files`, {
            method: "GET",
            headers: {
                ...getAuthHeader()
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Failed to fetch files");
        }

        return data.files || [];
    } catch (error) {
        console.error("API Error (GetFiles):", error);
        return [];
    }
};