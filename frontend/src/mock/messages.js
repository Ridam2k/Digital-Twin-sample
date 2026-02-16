export const MOCK_MESSAGES = [
  {
    id: 1,
    role: 'user',
    text: 'Can you walk me through how your RAG retrieval pipeline handles ambiguous queries?',
  },
  {
    id: 2,
    role: 'twin',
    text: `When the router can't clearly classify a query as technical or non-technical — scoring both anchors within roughly 0.05 of each other — it falls into an "ambiguous" branch. In that case the retriever queries all namespaces in parallel, merges results by cosine score, and returns the global top-K.\n\nThe key tradeoff is recall vs. noise: you get broader coverage but may pull in context from the wrong register. A future improvement would be a confidence threshold that triggers a clarifying question rather than a blind merge.`,
    citations: [
      { index: 1, doc_title: 'retriever.py', source_url: '', score: 0.91 },
      { index: 2, doc_title: 'router.py',    source_url: '', score: 0.87 },
    ],
    outOfScope: false,
  },
  {
    id: 3,
    role: 'user',
    text: 'What do you find genuinely hard about systems design work?',
  },
  {
    id: 4,
    role: 'twin',
    text: `The hardest part isn't the technical complexity — it's the irreversibility.\n\nYou can prototype a model architecture in a weekend and throw it away. You can't throw away a data model once three teams are writing against it. The decisions that cost the most are the quiet structural ones that don't feel like decisions at the time.`,
    citations: [],
    outOfScope: false,
  },
];
