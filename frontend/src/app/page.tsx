"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { EligibilityInput } from "@/types/benefits";
import type { InsurancePlan } from "@/types/insurance";
import type {
  InsuranceUploadResult,
  MedicineAlternative,
  UnifiedSearchResponse,
} from "@/types/search";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const INITIAL_HOUSEHOLD: EligibilityInput = {
  annual_income: 28000,
  household_size: 2,
  state: "CA",
  age: 34,
  has_children: false,
  is_pregnant: false,
  has_disability: false,
  currently_insured: false,
  zip_code: "93721",
};

function toCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "-";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

function toPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatAltType(value: string): string {
  if (!value) {
    return "Alternative";
  }
  return value
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function AlternativeCard({ alternative }: { alternative: MedicineAlternative }) {
  return (
    <article className="bubble-card alt-card">
      <p className="pill soft">{formatAltType(alternative.alternative_type)}</p>
      <h4>{alternative.drug.brand_name}</h4>
      <p className="muted">
        {alternative.drug.generic_name} {alternative.drug.strength}
      </p>
      <p className="value small">Best known price: {toCurrency(alternative.estimated_lowest_price)}</p>
      <p className="meta">{alternative.reason}</p>
    </article>
  );
}

export default function Home() {
  const [query, setQuery] = useState("metformin");
  const [zipCode, setZipCode] = useState("93721");
  const [quantity, setQuantity] = useState(30);
  const [maxResults, setMaxResults] = useState(10);
  const [includeProviders, setIncludeProviders] = useState(false);

  const [household, setHousehold] = useState<EligibilityInput>(INITIAL_HOUSEHOLD);

  const [useInsuranceEstimate, setUseInsuranceEstimate] = useState(false);
  const [planMode, setPlanMode] = useState<"template" | "upload">("template");
  const [templates, setTemplates] = useState<InsurancePlan[]>([]);
  const [selectedTemplateIndex, setSelectedTemplateIndex] = useState(1);
  const [uploadText, setUploadText] = useState("");
  const [uploadPlanName, setUploadPlanName] = useState("");
  const [uploadResult, setUploadResult] = useState<InsuranceUploadResult | null>(null);
  const [isParsingUpload, setIsParsingUpload] = useState(false);
  const [deductibleProgress, setDeductibleProgress] = useState(0);
  const [oopProgress, setOopProgress] = useState(0);

  const [result, setResult] = useState<UnifiedSearchResponse | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    async function loadTemplates() {
      try {
        const response = await fetch(`${API_BASE}/insurance/templates`);
        if (!response.ok) {
          return;
        }
        const data: InsurancePlan[] = await response.json();
        setTemplates(data);
      } catch {
        // Keep insurance optional.
      }
    }

    loadTemplates();
  }, []);

  const activePlan: InsurancePlan | null = useMemo(() => {
    if (!useInsuranceEstimate) {
      return null;
    }
    if (planMode === "upload" && uploadResult) {
      return uploadResult.parsed_plan;
    }
    return templates[selectedTemplateIndex] ?? null;
  }, [planMode, selectedTemplateIndex, templates, uploadResult, useInsuranceEstimate]);

  async function handleParseUpload() {
    setErrorMessage(null);

    if (!uploadText.trim()) {
      setErrorMessage("Paste your plan text before parsing.");
      return;
    }

    setIsParsingUpload(true);
    try {
      const response = await fetch(`${API_BASE}/insurance/upload/parse`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          document_text: uploadText,
          plan_name_hint: uploadPlanName.trim() || undefined,
        }),
      });

      if (!response.ok) {
        throw new Error("Could not parse insurance document");
      }

      const data: InsuranceUploadResult = await response.json();
      setUploadResult(data);
      setPlanMode("upload");
      setUseInsuranceEstimate(true);
    } catch {
      setErrorMessage("Insurance parse failed. You can still run medicine-only search.");
    } finally {
      setIsParsingUpload(false);
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setIsSearching(true);

    try {
      const response = await fetch(`${API_BASE}/search/true-cost`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query,
          zip_code: zipCode,
          quantity,
          include_medicines: true,
          include_providers: includeProviders,
          max_results: maxResults,
          deductible_progress: deductibleProgress,
          oop_progress: oopProgress,
          household: {
            ...household,
            zip_code: zipCode,
            currently_insured: household.currently_insured || activePlan !== null,
          },
          insurance_plan: activePlan,
        }),
      });

      if (!response.ok) {
        throw new Error("Search failed");
      }

      const payload: UnifiedSearchResponse = await response.json();
      setResult(payload);
    } catch {
      setErrorMessage("Search failed. Check backend at http://localhost:8000.");
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="bubble-bg bubble-a" />
      <div className="bubble-bg bubble-b" />
      <div className="bubble-bg bubble-c" />

      <header className="hero bubble-card">
        <p className="eyebrow">CareCompare Medicine Search</p>
        <h1>Find the lowest true cost for each medicine and see smarter alternatives</h1>
        <p>
          Start with one medication. We compare local/online prices, suggest generic and
          therapeutic alternatives, and then layer in benefit programs.
        </p>
        <div className="chip-row">
          <button type="button" className="chip" onClick={() => setQuery("metformin")}>Metformin</button>
          <button type="button" className="chip" onClick={() => setQuery("atorvastatin")}>Atorvastatin</button>
          <button type="button" className="chip" onClick={() => setQuery("albuterol")}>Albuterol</button>
          <button type="button" className="chip" onClick={() => setQuery("levothyroxine")}>Levothyroxine</button>
        </div>
      </header>

      <main className="grid-layout">
        <section className="panel bubble-card">
          <h2>Medicine Search</h2>
          <form onSubmit={handleSearch} className="stack">
            <label>
              Medication name
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="metformin, insulin lispro, omeprazole"
                required
              />
            </label>

            <div className="row row-3">
              <label>
                ZIP code
                <input
                  value={zipCode}
                  onChange={(event) => setZipCode(event.target.value)}
                  placeholder="93721"
                  required
                />
              </label>
              <label>
                Quantity
                <input
                  type="number"
                  value={quantity}
                  min={1}
                  max={365}
                  onChange={(event) => setQuantity(Number(event.target.value) || 30)}
                />
              </label>
              <label>
                Max results
                <input
                  type="number"
                  value={maxResults}
                  min={1}
                  max={25}
                  onChange={(event) => setMaxResults(Number(event.target.value) || 10)}
                />
              </label>
            </div>

            <h3>Benefits Profile</h3>
            <div className="row row-4">
              <label>
                Annual income
                <input
                  type="number"
                  value={household.annual_income}
                  onChange={(event) =>
                    setHousehold((prev) => ({
                      ...prev,
                      annual_income: Number(event.target.value) || 0,
                    }))
                  }
                />
              </label>
              <label>
                Household size
                <input
                  type="number"
                  value={household.household_size}
                  min={1}
                  onChange={(event) =>
                    setHousehold((prev) => ({
                      ...prev,
                      household_size: Number(event.target.value) || 1,
                    }))
                  }
                />
              </label>
              <label>
                State
                <input
                  value={household.state}
                  onChange={(event) =>
                    setHousehold((prev) => ({
                      ...prev,
                      state: event.target.value.toUpperCase(),
                    }))
                  }
                />
              </label>
              <label>
                Age
                <input
                  type="number"
                  value={household.age}
                  min={0}
                  max={120}
                  onChange={(event) =>
                    setHousehold((prev) => ({
                      ...prev,
                      age: Number(event.target.value) || 0,
                    }))
                  }
                />
              </label>
            </div>

            <div className="row row-4 check-row">
              <label className="check">
                <input
                  type="checkbox"
                  checked={household.has_children}
                  onChange={(event) =>
                    setHousehold((prev) => ({ ...prev, has_children: event.target.checked }))
                  }
                />
                Has children
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={household.has_disability}
                  onChange={(event) =>
                    setHousehold((prev) => ({ ...prev, has_disability: event.target.checked }))
                  }
                />
                Disability
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={household.is_pregnant}
                  onChange={(event) =>
                    setHousehold((prev) => ({ ...prev, is_pregnant: event.target.checked }))
                  }
                />
                Pregnant
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={includeProviders}
                  onChange={(event) => setIncludeProviders(event.target.checked)}
                />
                Include provider fallback
              </label>
            </div>

            <details className="advanced-box">
              <summary>Advanced (optional insurance estimate)</summary>

              <label className="check">
                <input
                  type="checkbox"
                  checked={useInsuranceEstimate}
                  onChange={(event) => setUseInsuranceEstimate(event.target.checked)}
                />
                Apply insurance estimate in price breakdown
              </label>

              {useInsuranceEstimate ? (
                <>
                  <div className="row check-row">
                    <label className="check">
                      <input
                        type="radio"
                        name="plan-mode"
                        checked={planMode === "template"}
                        onChange={() => setPlanMode("template")}
                      />
                      Template plan
                    </label>
                    <label className="check">
                      <input
                        type="radio"
                        name="plan-mode"
                        checked={planMode === "upload"}
                        onChange={() => setPlanMode("upload")}
                      />
                      Upload plan text
                    </label>
                  </div>

                  {planMode === "template" ? (
                    <label>
                      Plan template
                      <select
                        value={selectedTemplateIndex}
                        onChange={(event) => setSelectedTemplateIndex(Number(event.target.value))}
                      >
                        {templates.map((plan, index) => (
                          <option key={plan.plan_name} value={index}>
                            {plan.plan_name}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}

                  <label>
                    Plan name hint (optional)
                    <input
                      value={uploadPlanName}
                      onChange={(event) => setUploadPlanName(event.target.value)}
                      placeholder="Acme Silver PPO"
                    />
                  </label>

                  <label>
                    Paste plan text
                    <textarea
                      value={uploadText}
                      onChange={(event) => setUploadText(event.target.value)}
                      placeholder="Plan Name: Acme Silver PPO\nIndividual deductible: $4,000\nCoinsurance: 30%"
                    />
                  </label>

                  <button type="button" className="secondary" onClick={handleParseUpload}>
                    {isParsingUpload ? "Parsing..." : "Parse plan text"}
                  </button>

                  <div className="row row-2">
                    <label>
                      Deductible progress
                      <input
                        type="range"
                        min={0}
                        max={1}
                        step={0.05}
                        value={deductibleProgress}
                        onChange={(event) => setDeductibleProgress(Number(event.target.value))}
                      />
                      <span className="muted">{toPercent(deductibleProgress)}</span>
                    </label>

                    <label>
                      OOP progress
                      <input
                        type="range"
                        min={0}
                        max={1}
                        step={0.05}
                        value={oopProgress}
                        onChange={(event) => setOopProgress(Number(event.target.value))}
                      />
                      <span className="muted">{toPercent(oopProgress)}</span>
                    </label>
                  </div>
                </>
              ) : null}

              {uploadResult ? (
                <div className="inline-card">
                  <strong>Parsed plan:</strong>
                  <p>{uploadResult.summary}</p>
                </div>
              ) : null}
            </details>

            <button type="submit">{isSearching ? "Searching..." : "Find Best Medicine Prices"}</button>
          </form>

          {errorMessage ? <p className="error">{errorMessage}</p> : null}
        </section>

        <section className="panel bubble-card">
          <h2>Results</h2>
          {!result ? <p className="muted">Run a medicine search to see matches and alternatives.</p> : null}

          {result ? (
            <>
              <div className="summary-grid">
                <article className="bubble-card">
                  <p className="label">Best cash price</p>
                  <p className="value">{toCurrency(result.summary.min_cash_price)}</p>
                </article>
                <article className="bubble-card">
                  <p className="label">Best adjusted price</p>
                  <p className="value">{toCurrency(result.summary.min_benefit_adjusted_price)}</p>
                </article>
                <article className="bubble-card">
                  <p className="label">Benefit estimate</p>
                  <p className="value">{toCurrency(result.summary.estimated_annual_benefit_subsidy)}</p>
                </article>
              </div>

              <h3>Primary medicine match</h3>
              {result.medicine_focus.primary_match ? (
                <article className="bubble-card result-card featured">
                  <p className="pill">Top Match</p>
                  <h4>{result.medicine_focus.primary_match.brand_name}</h4>
                  <p className="muted">
                    {result.medicine_focus.primary_match.generic_name} {" "}
                    {result.medicine_focus.primary_match.strength}
                  </p>
                  <p className="meta">
                    Found {result.medicine_focus.medicine_match_count} medicine match
                    {result.medicine_focus.medicine_match_count === 1 ? "" : "es"}
                  </p>
                </article>
              ) : (
                <p className="muted">No direct medicine match found for this query.</p>
              )}

              <h3>Alternative medicines</h3>
              <div className="result-list alt-grid">
                {result.medicine_focus.alternatives.length === 0 ? (
                  <p className="muted">No alternatives available for this medicine yet.</p>
                ) : (
                  result.medicine_focus.alternatives.map((alternative) => (
                    <AlternativeCard key={alternative.drug.ndc} alternative={alternative} />
                  ))
                )}
              </div>

              <h3>Ranked price options</h3>
              <div className="result-list">
                {result.ranked_options.map((option) => (
                  <article className="bubble-card result-card" key={option.option_id}>
                    <div className="result-top">
                      <p className="pill">{option.option_type}</p>
                      <p className="score">Rank {option.rank_score.toFixed(3)}</p>
                    </div>
                    <h4>{option.name}</h4>
                    <p className="provider">{option.provider_name}</p>
                    <p className="muted">{option.location}</p>
                    <div className="result-prices">
                      <span>Cash: {toCurrency(option.list_price)}</span>
                      <span>Insured: {toCurrency(option.insured_estimate)}</span>
                      <span>Adjusted: {toCurrency(option.benefit_adjusted_cost)}</span>
                    </div>
                    <ul>
                      {option.explanation.map((line, lineIndex) => (
                        <li key={`${option.option_id}-${lineIndex}`}>{line}</li>
                      ))}
                    </ul>
                  </article>
                ))}
              </div>

              <h3>Matched savings programs</h3>
              <div className="result-list">
                {result.eligible_programs.map((program) => (
                  <article className="bubble-card result-card" key={program.id}>
                    <h4>{program.name}</h4>
                    <p>{program.description}</p>
                    <p className="meta">Estimated savings: {program.estimated_savings}</p>
                    <a href={program.application_url} target="_blank" rel="noreferrer">
                      Learn more
                    </a>
                  </article>
                ))}
              </div>
            </>
          ) : null}
        </section>
      </main>
    </div>
  );
}
