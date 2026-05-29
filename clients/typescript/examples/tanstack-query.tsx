import { useQuery } from "@tanstack/react-query";
import { DsmApiClient } from "../src/index";

const client = new DsmApiClient("http://localhost:8000");

export function useDsmSearch(query: string) {
  return useQuery({
    queryKey: ["dsm-search", query],
    enabled: query.length > 2,
    queryFn: () => client.search({ query, use_vector: false, use_fts: true, top_k: 8 })
  });
}
