import { DsmApiClient } from "../src/index";

const client = new DsmApiClient("http://localhost:8000");
const documents = await client.documents({ limit: 10, category: "FULL" });
console.log(documents.map((doc) => doc.name));

const result = await client.search({ query: "transtorno de pânico", use_vector: false, use_fts: true });
console.log(result.results[0]);
