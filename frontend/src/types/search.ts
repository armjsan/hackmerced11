import type { BenefitProgram, EligibilityInput } from "./benefits";
import type { InsurancePlan } from "./insurance";
import type { Drug } from "./medicine";

export type ConfidenceLevel = "high" | "medium" | "low";
export type OptionType = "medicine" | "provider_service";

export interface RankedCostOption {
  option_id: string;
  option_type: OptionType;
  name: string;
  provider_name: string;
  category: string;
  location: string;
  distance_miles: number | null;
  list_price: number;
  insured_estimate: number | null;
  benefit_adjusted_cost: number;
  confidence: ConfidenceLevel;
  source: string;
  network_status: string;
  rank_score: number;
  explanation: string[];
}

export interface UnifiedSearchSummary {
  min_cash_price: number | null;
  min_insured_price: number | null;
  min_benefit_adjusted_price: number | null;
  estimated_annual_benefit_subsidy: number;
}

export interface MedicineAlternative {
  drug: Drug;
  alternative_type: string;
  reason: string;
  estimated_lowest_price: number | null;
}

export interface MedicineFocus {
  primary_match: Drug | null;
  medicine_match_count: number;
  alternatives: MedicineAlternative[];
}

export interface UnifiedSearchRequest {
  query: string;
  zip_code: string;
  quantity: number;
  include_medicines: boolean;
  include_providers: boolean;
  max_results: number;
  household: EligibilityInput;
  insurance_plan: InsurancePlan | null;
  deductible_progress: number;
  oop_progress: number;
}

export interface UnifiedSearchResponse {
  query: string;
  zip_code: string;
  generated_at: string;
  fpl_percentage: number;
  medicine_focus: MedicineFocus;
  eligible_programs: BenefitProgram[];
  ranked_options: RankedCostOption[];
  summary: UnifiedSearchSummary;
  assumptions: string[];
}

export interface InsuranceUploadRequest {
  document_text: string;
  plan_name_hint?: string;
}

export interface InsuranceUploadResult {
  parsed_plan: InsurancePlan;
  confidence: number;
  covered_services: string[];
  excluded_services: string[];
  summary: string;
  extracted_fields: Record<string, string | number | boolean>;
}
