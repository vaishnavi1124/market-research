// // src/lib/api.ts
// import axios from "axios";

// const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// export const api = axios.create({
//   baseURL: API_BASE,
//   withCredentials: true,
// });

// let isRefreshing = false;
// let refreshPromise: Promise<any> | null = null;

// api.interceptors.response.use(
//   (res) => res,
//   async (error) => {
//     const original: any = error.config;
//     const status = error?.response?.status;

//     if (status === 401 && !original._retry) {
//       original._retry = true;

//       if (!isRefreshing) {
//         isRefreshing = true;
//         refreshPromise = api.post("/auth/refresh").finally(() => {
//           isRefreshing = false;
//           refreshPromise = null;
//         });
//       }

//       try {
//         await refreshPromise;
//         return api(original);
//       } catch {
//         // refresh failed -> let it fall through
//       }
//     }
//     return Promise.reject(error);
//   }
// );

// // src/lib/api.ts
// import axios from "axios";

// /**
//  * IMPORTANT: Keep the API host identical to the page host to avoid cookie issues.
//  * This prevents the classic localhost vs 127.0.0.1 mismatch.
//  */
// const resolveAPIBase = () => {
//   const env = (import.meta.env.VITE_API_URL || "").trim();
//   if (env) return env; // e.g., "http://127.0.0.1:8000" or "http://localhost:8000"
//   const host = window.location.hostname; // matches the tab's host
//   return `http://${host}:8000`;
// };

// export const api = axios.create({
//   baseURL: resolveAPIBase(),
//   withCredentials: true, // send/receive HttpOnly cookies
// });

// // ---- Global 401 -> silent refresh, then retry once ----
// let isRefreshing = false;
// let refreshPromise: Promise<any> | null = null;

// api.interceptors.response.use(
//   (res) => res,
//   async (error) => {
//     const original: any = error.config;
//     const status = error?.response?.status;

//     if (status === 401 && !original?._retry) {
//       original._retry = true;

//       if (!isRefreshing) {
//         isRefreshing = true;
//         refreshPromise = api.post("/auth/refresh").finally(() => {
//           isRefreshing = false;
//           refreshPromise = null;
//         });
//       }

//       try {
//         await refreshPromise;
//         return api(original);
//       } catch {
//         // refresh failed; bubble up
//       }
//     }
//     return Promise.reject(error);
//   }
// );


// // src/lib/api.ts
// import axios from "axios";

// export const api = axios.create({
//   baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000",
//   withCredentials: true,
// });

// // Attach interceptor to catch 401 and logout
// api.interceptors.response.use(
//   (res) => res,
//   (err) => {
//     if (err.response?.status === 401) {
//       // Clear session marker
//       localStorage.removeItem("authed");
//       // Optional: redirect to login
//       window.location.href = "/";
//     }
//     return Promise.reject(err);
//   }
// );


// src/lib/api.ts
import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000",
  withCredentials: true,
});


export async function safeGet<T = unknown>(url: string) {
  try {
    const res = await api.get<T>(url);
    return { ok: true as const, data: res.data as T };
  } catch (e: any) {
    return { ok: false as const, error: e };
  }
}

export async function safePost<T = unknown>(url: string, body?: any) {
  try {
    const res = await api.post<T>(url, body);
    return { ok: true as const, data: res.data as T };
  } catch (e: any) {
    return { ok: false as const, error: e };
  }
}
