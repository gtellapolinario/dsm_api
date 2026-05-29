import { useEffect, useState } from "react";
import { DsmApiClient, type DsmDocumentListItem } from "../src/index";

const client = new DsmApiClient("http://localhost:8000");

export function useDsmDocuments() {
  const [documents, setDocuments] = useState<DsmDocumentListItem[]>([]);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    client.documents({ limit: 50 }).then(setDocuments).catch(setError);
  }, []);

  return { documents, error };
}
