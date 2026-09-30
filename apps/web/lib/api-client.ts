/**
 * Type-safe API client with unified error handling (Constitution 3.I, contracts/api.md).
 */

export interface ApiErrorDetail {
  code: string;
  message: string;
  field?: string | null;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export class ApiClientError extends Error {
  constructor(
    public readonly status: number,
    public readonly errorDetail: ApiErrorDetail,
  ) {
    super(errorDetail.message);
    this.name = "ApiClientError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail: ApiErrorDetail;
    try {
      const data = (await response.json()) as ApiErrorResponse | { detail?: string };
      if ("error" in data && data.error) {
        errorDetail = data.error;
      } else if ("detail" in data && typeof data.detail === "string") {
        errorDetail = {
          code: `HTTP_${response.status}`,
          message: data.detail,
          field: null,
        };
      } else {
        errorDetail = {
          code: `HTTP_${response.status}`,
          message: response.statusText || "Request failed",
          field: null,
        };
      }
    } catch {
      errorDetail = {
        code: `HTTP_${response.status}`,
        message: response.statusText || "Request failed",
        field: null,
      };
    }
    throw new ApiClientError(response.status, errorDetail);
  }

  // Handle empty responses
  const contentType = response.headers.get("content-type");
  if (!contentType || !contentType.includes("application/json")) {
    return (await response.text()) as unknown as T;
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  async get<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(path, {
      ...init,
      method: "GET",
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
    });
    return handleResponse<T>(response);
  },

  async post<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    const isFormData = body instanceof FormData;
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...(init?.headers as Record<string, string>),
    };
    if (!isFormData && body !== undefined) {
      headers["Content-Type"] = "application/json";
    }

    const response = await fetch(path, {
      ...init,
      method: "POST",
      headers,
      body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async put<T>(path: string, body?: unknown, init?: RequestInit): Promise<T> {
    const response = await fetch(path, {
      ...init,
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...init?.headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async delete<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(path, {
      ...init,
      method: "DELETE",
      headers: {
        Accept: "application/json",
        ...init?.headers,
      },
    });
    return handleResponse<T>(response);
  },

  async upload<T>(path: string, formData: FormData, init?: RequestInit): Promise<T> {
    return this.post<T>(path, formData, init);
  },
};
