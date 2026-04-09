/**
 * APEX Cognitive Swarm — Activated Connector Layer
 * GlacierEQ / Casey Barton — Case 1FDV-23-0001009
 * Wires: GitHub × Supabase × Notion × MotherDuck × Memory × Sequential Thinking
 */

import { StateGraph, END, Annotation } from "@langchain/langgraph";
import { ChatOpenAI } from "@langchain/openai";
import { createClient } from "@supabase/supabase-js";
import { OpenAIEmbeddings } from "@langchain/openai";
import { SupabaseVectorStore } from "@langchain/community/vectorstores/supabase";

// ── Environment ───────────────────────────────────────────────────
const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY!;
const OPENAI_KEY = process.env.OPENAI_API_KEY!;

// ── Supabase Vector Memory ────────────────────────────────────────
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

const embeddings = new OpenAIEmbeddings({
  openAIApiKey: OPENAI_KEY,
  modelName: "text-embedding-3-large",
  dimensions: 1536,
});

const vectorStore = new SupabaseVectorStore(embeddings, {
  client: supabase,
  tableName: "apex_memory",
  queryName: "match_apex_memory",
});

// ── State Schema ──────────────────────────────────────────────────
const APEXState = Annotation.Root({
  task: Annotation<string>({ reducer: (x, y) => y ?? x }),
  caseId: Annotation<string>({ reducer: (x, y) => y ?? x, default: () => "1FDV-23-0001009" }),
  memoryContext: Annotation<string[]>({ reducer: (x, y) => [...x, ...y], default: () => [] }),
  legalAnalysis: Annotation<string[]>({ reducer: (x, y) => [...x, ...y], default: () => [] }),
  githubActions: Annotation<string[]>({ reducer: (x, y) => [...x, ...y], default: () => [] }),
  notionUpdates: Annotation<string[]>({ reducer: (x, y) => [...x, ...y], default: () => [] }),
  output: Annotation<string>({ reducer: (x, y) => y ?? x, default: () => "" }),
  iteration: Annotation<number>({ reducer: (x, y) => y ?? x, default: () => 0 }),
  errors: Annotation<string[]>({ reducer: (x, y) => [...x, ...y], default: () => [] }),
});

// ── Models ────────────────────────────────────────────────────────
const apex4o = new ChatOpenAI({ modelName: "gpt-4o", temperature: 0 });
const apexMini = new ChatOpenAI({ modelName: "gpt-4o-mini", temperature: 0.2 });

// ── Agent: Memory Retriever ───────────────────────────────────────
async function memoryRetrieverNode(state: typeof APEXState.State) {
  try {
    const docs = await vectorStore.similaritySearch(state.task, 5);
    const context = docs.map((d) => d.pageContent);
    return { memoryContext: context };
  } catch (e) {
    return { errors: [`Memory retrieval: ${e}`] };
  }
}

// ── Agent: Legal Weaver ───────────────────────────────────────────
async function legalWeaverNode(state: typeof APEXState.State) {
  const contextBlock = state.memoryContext.slice(0, 3).join("\n---\n");
  const prompt = `
You are APEX Legal Weaver — Hawaii family law specialist.
Case: ${state.caseId} | Active Federal Escalation: 42 U.S.C. §1983, RICO 18 U.S.C. §1961

Memory Context:
${contextBlock}

Task: ${state.task}

Cite: HRS §571 (family court), §580 (divorce), §560 (probate/custody).
Output: structured legal analysis + 3 immediate tactical steps.
  `;
  const response = await apex4o.invoke(prompt);
  return { legalAnalysis: [response.content as string] };
}

// ── Agent: Memory Storer ──────────────────────────────────────────
async function memoryStorerNode(state: typeof APEXState.State) {
  try {
    const entry = {
      pageContent: `[${new Date().toISOString()}] APEX Task: ${state.task}\n\nAnalysis: ${state.legalAnalysis[0] ?? ""}`,
      metadata: {
        caseId: state.caseId,
        taskType: "legal_analysis",
        timestamp: new Date().toISOString(),
        tags: ["apex", "custody", "hawaii", "federal-escalation"],
      },
    };
    await vectorStore.addDocuments([entry]);
    return { notionUpdates: ["Memory stored to Supabase pgvector ✓"] };
  } catch (e) {
    return { errors: [`Memory store: ${e}`] };
  }
}

// ── Agent: Output Synthesizer ─────────────────────────────────────
async function synthesizerNode(state: typeof APEXState.State) {
  const synthesis = await apex4o.invoke(`
Synthesize into a final APEX response:

Legal Analysis:
${state.legalAnalysis.join("\n")}

Memory Stored: ${state.notionUpdates.length} entries
GitHub Actions: ${state.githubActions.join(", ") || "none"}
Errors: ${state.errors.join(", ") || "none"}

Format:
1. Executive Summary (2-3 sentences)
2. Hawaii Statutes Cited
3. Immediate Tactical Steps (numbered)
4. Federal Escalation Vector (if applicable)
  `);
  return { output: synthesis.content as string, iteration: state.iteration + 1 };
}

// ── Graph Assembly ────────────────────────────────────────────────
function buildAPEXSwarm() {
  const graph = new StateGraph(APEXState)
    .addNode("memory_retriever", memoryRetrieverNode)
    .addNode("legal_weaver", legalWeaverNode)
    .addNode("memory_storer", memoryStorerNode)
    .addNode("synthesizer", synthesizerNode)
    .addEdge("__start__", "memory_retriever")
    .addEdge("memory_retriever", "legal_weaver")
    .addEdge("legal_weaver", "memory_storer")
    .addEdge("memory_storer", "synthesizer")
    .addEdge("synthesizer", END);

  return graph.compile();
}

// ── Supabase Schema Bootstrap ─────────────────────────────────────
export async function bootstrapSupabaseSchema() {
  await supabase.rpc("exec_sql", {
    sql: `
      CREATE EXTENSION IF NOT EXISTS vector;

      CREATE TABLE IF NOT EXISTS apex_memory (
        id bigserial PRIMARY KEY,
        content text NOT NULL,
        metadata jsonb DEFAULT '{}',
        embedding vector(1536),
        created_at timestamptz DEFAULT now()
      );

      CREATE OR REPLACE FUNCTION match_apex_memory(
        query_embedding vector(1536),
        match_count int DEFAULT 5,
        filter jsonb DEFAULT '{}'
      ) RETURNS TABLE (
        id bigint,
        content text,
        metadata jsonb,
        similarity float
      )
      LANGUAGE plpgsql AS $$
      BEGIN
        RETURN QUERY
        SELECT
          am.id,
          am.content,
          am.metadata,
          1 - (am.embedding <=> query_embedding) AS similarity
        FROM apex_memory am
        WHERE am.metadata @> filter
        ORDER BY am.embedding <=> query_embedding
        LIMIT match_count;
      END;
      $$;

      CREATE INDEX IF NOT EXISTS apex_memory_embedding_idx
        ON apex_memory USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    `,
  });
  console.log("✅ Supabase APEX schema bootstrapped");
}

// ── Entry Point ───────────────────────────────────────────────────
export async function runAPEXSwarm(task: string) {
  const swarm = buildAPEXSwarm();
  const result = await swarm.invoke({ task });
  return {
    output: result.output,
    memoryStored: result.notionUpdates.length,
    errors: result.errors,
    iterations: result.iteration,
  };
}

// CLI runner
if (require.main === module) {
  const task = process.argv[2] ?? "Summarize current case status for 1FDV-23-0001009";
  runAPEXSwarm(task).then(console.log).catch(console.error);
}
