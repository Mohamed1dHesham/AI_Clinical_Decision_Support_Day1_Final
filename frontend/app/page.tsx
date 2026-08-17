"use client";

import { FormEvent, useState } from "react";

type Metadata = {
  document_name: string;
  section: string;
  page_number: number;
  chunk_id: string;
  token_count?: number;
};

type Result = {
  rank: number;
  similarity: number;
  text: string;
  metadata: Metadata;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search(event?: FormEvent) {
    event?.preventDefault();
    if (!question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 4 }),
      });
      if (!res.ok) throw new Error("request failed");
      const data = await res.json();
      setResults(data.results ?? []);
    } catch {
      setError("Could not reach the retrieval API. Start the FastAPI backend and build the index first.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <header className="hero">
        <div className="eyebrow">AI Clinical Decision Support · Day 1/2</div>
        <h1>Hypertension Evidence Search</h1>
        <p>Retrieve traceable evidence from the two approved NICE hypertension documents.</p>
      </header>

      <section className="notice">
        <strong>Educational prototype.</strong> This system retrieves evidence only. It does not diagnose, prescribe, or replace a qualified healthcare professional.
      </section>

      <form className="searchBox" onSubmit={search}>
        <label htmlFor="question">Clinical question</label>
        <textarea
          id="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Example: How is hypertension confirmed using ambulatory blood pressure monitoring?"
          maxLength={1000}
        />
        <div className="actions">
          <span>{question.length}/1000</span>
          <button type="submit" disabled={loading || question.trim().length < 3}>
            {loading ? "Searching…" : "Search Evidence"}
          </button>
        </div>
      </form>

      {error && <div className="error">{error}</div>}

      <section className="evidence">
        <div className="sectionTitle">
          <div>
            <span className="eyebrow">Retrieval layer</span>
            <h2>Retrieved Evidence</h2>
          </div>
          {results.length > 0 && <span className="count">Top {results.length}</span>}
        </div>

        {results.length === 0 ? (
          <div className="empty">Ask a question to see ranked evidence with document, section, page, similarity and chunk ID.</div>
        ) : (
          results.map((result) => (
            <article className="card" key={result.metadata.chunk_id}>
              <div className="cardTop">
                <span className="rank">#{result.rank}</span>
                <span>Similarity {result.similarity.toFixed(3)}</span>
                <span>Page {result.metadata.page_number}</span>
              </div>
              <h3>{result.metadata.section}</h3>
              <div className="source">{result.metadata.document_name}</div>
              <p>{result.text}</p>
              <div className="chunk">Chunk ID · {result.metadata.chunk_id}</div>
            </article>
          ))
        )}
      </section>

      <footer>Source-grounded retrieval prototype · Adult hypertension scope · NICE documents</footer>
    </main>
  );
}
