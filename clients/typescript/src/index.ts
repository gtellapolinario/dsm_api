export type DsmDocumentListItem = {
  id: string;
  version_id: string;
  item_id: string;
  chapter_id: string;
  chapter_name: string;
  name: string;
  category: "FULL" | "SHORT";
  estrutura_diagnostica: string;
  ui_mode: string;
  render_structured_interview: boolean;
  has_formal_severity: boolean;
  severity_type: string;
  active: boolean;
};

export type DsmSearchRequest = {
  query: string;
  version_id?: string;
  chapter_id?: string;
  item_id?: string;
  category?: string;
  chunk_types?: string[];
  top_k?: number;
  use_vector?: boolean;
  use_fts?: boolean;
  allow_fallback?: boolean;
};

export type DsmSearchResultItem = {
  chunk_id: string;
  document_item_id: string;
  document_name?: string | null;
  chapter_id: string;
  chunk_type: string;
  chunk_title?: string | null;
  chunk_text: string;
  vector_score?: number | null;
  text_score?: number | null;
  hybrid_score: number;
  metadata: Record<string, unknown>;
};

export type DsmSearchResult = {
  query: string;
  version_id: string;
  results: DsmSearchResultItem[];
};

export class DsmApiClient {
  constructor(private readonly baseUrl: string, private readonly adminToken?: string) {}

  async documents(params: Record<string, string | number | boolean | undefined> = {}): Promise<DsmDocumentListItem[]> {
    const url = new URL("/api/dsm/documents", this.baseUrl);
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
    return this.getJson(url);
  }

  async search(request: DsmSearchRequest): Promise<DsmSearchResult> {
    return this.postJson(new URL("/api/dsm/search", this.baseUrl), request);
  }

  async activateVersion(versionId: string): Promise<unknown> {
    return this.postJson(new URL(`/api/dsm/versions/${versionId}/activate`, this.baseUrl), {});
  }

  private async getJson<T>(url: URL): Promise<T> {
    const response = await fetch(url, { headers: this.headers() });
    if (!response.ok) throw new Error(`DSM API error ${response.status}: ${await response.text()}`);
    return response.json() as Promise<T>;
  }

  private async postJson<T>(url: URL, body: unknown): Promise<T> {
    const response = await fetch(url, { method: "POST", headers: this.headers(true), body: JSON.stringify(body) });
    if (!response.ok) throw new Error(`DSM API error ${response.status}: ${await response.text()}`);
    return response.json() as Promise<T>;
  }

  private headers(json = false): HeadersInit {
    return {
      ...(json ? { "content-type": "application/json" } : {}),
      ...(this.adminToken ? { "x-admin-token": this.adminToken } : {})
    };
  }
}
