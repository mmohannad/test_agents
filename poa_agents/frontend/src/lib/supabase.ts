import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let _supabase: SupabaseClient | null = null;

function getSupabase(): SupabaseClient {
  if (!_supabase) {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    if (!supabaseUrl || !supabaseKey) {
      throw new Error(
        "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY environment variables"
      );
    }
    _supabase = createClient(supabaseUrl, supabaseKey);
  }
  return _supabase;
}

export interface ContextData {
  application_id: string;
  loaded_at: string;
  structured: {
    application: Record<string, unknown>;
    parties: Record<string, unknown>[];
    capacity_proofs: Record<string, unknown>[];
  };
  unstructured: {
    document_extractions: Record<string, unknown>[];
  };
}

/**
 * Load application context from Supabase.
 * Mirrors the same queries the condenser agent runs in:
 *   condenser_agent/project/supabase_client.py
 *   condenser_agent/project/acp.py lines 215-243
 */
export async function loadContext(applicationId: string): Promise<ContextData> {
  const supabase = getSupabase();
  console.log("[loadContext] Starting for application:", applicationId);

  // 1. Load application
  console.log("[loadContext] Querying applications table...");
  const { data: application, error: appErr } = await supabase
    .from("applications")
    .select("*")
    .eq("id", applicationId)
    .single();

  if (appErr || !application) {
    console.error("[loadContext] Application query failed:", JSON.stringify(appErr));
    const code = appErr?.code;
    // PGRST116 = .single() found 0 rows
    if (code === "PGRST116" || (!appErr?.message && !application)) {
      throw new Error(
        `Application not found: ${applicationId}. Check the ID and try again.`
      );
    }
    throw new Error(
      appErr?.message || `Application query failed for: ${applicationId}`
    );
  }
  console.log("[loadContext] Application loaded:", application.id);

  // 2. Load parties
  console.log("[loadContext] Querying parties table...");
  const { data: parties, error: partiesErr } = await supabase
    .from("parties")
    .select("*")
    .eq("application_id", applicationId);

  if (partiesErr) {
    console.error("[loadContext] Parties query failed:", partiesErr);
    throw new Error(`Failed to load parties: ${partiesErr.message}`);
  }
  console.log("[loadContext] Parties loaded:", (parties || []).length);

  // 3. Load capacity proofs for all parties
  const partyIds = (parties || []).map((p) => p.id as string);
  let capacityProofs: Record<string, unknown>[] = [];

  if (partyIds.length > 0) {
    console.log("[loadContext] Querying capacity_proofs for", partyIds.length, "parties...");
    const { data: proofs, error: proofsErr } = await supabase
      .from("capacity_proofs")
      .select("*")
      .in("party_id", partyIds);

    if (proofsErr) {
      console.warn("[loadContext] Capacity proofs query failed:", proofsErr);
    } else {
      capacityProofs = proofs || [];
      console.log("[loadContext] Capacity proofs loaded:", capacityProofs.length);
    }
  }

  // 4. Load document extractions (documents → document_extractions)
  console.log("[loadContext] Querying documents table...");
  const { data: documents, error: docsErr } = await supabase
    .from("documents")
    .select("id, file_name, attachment_type_code")
    .eq("application_id", applicationId);

  if (docsErr) {
    console.warn("[loadContext] Documents query failed:", docsErr);
  }

  let documentExtractions: Record<string, unknown>[] = [];

  if (!docsErr && documents && documents.length > 0) {
    const docIds = documents.map((d) => d.id as string);
    // Build lookup: document_id → { file_name, attachment_type_code }
    const docMeta: Record<string, { file_name: string; attachment_type_code: string }> = {};
    for (const d of documents) {
      docMeta[d.id as string] = {
        file_name: d.file_name as string,
        attachment_type_code: d.attachment_type_code as string,
      };
    }

    console.log("[loadContext] Querying document_extractions for", docIds.length, "documents...");
    const { data: extractions, error: extrErr } = await supabase
      .from("document_extractions")
      .select("*")
      .in("document_id", docIds);

    if (extrErr) {
      console.warn("[loadContext] Document extractions query failed:", extrErr);
    } else {
      // Merge document metadata into each extraction for display
      documentExtractions = (extractions || []).map((ext) => {
        const meta = docMeta[ext.document_id as string];
        return {
          ...ext,
          file_name: meta?.file_name ?? null,
          document_type_code: meta?.attachment_type_code ?? null,
        };
      });
      console.log("[loadContext] Document extractions loaded:", documentExtractions.length);
    }
  } else {
    console.log("[loadContext] No documents found, skipping extractions");
  }

  console.log("[loadContext] Context loaded successfully");

  return {
    application_id: applicationId,
    loaded_at: new Date().toISOString(),
    structured: {
      application: application as Record<string, unknown>,
      parties: (parties || []) as Record<string, unknown>[],
      capacity_proofs: capacityProofs,
    },
    unstructured: {
      document_extractions: documentExtractions,
    },
  };
}
