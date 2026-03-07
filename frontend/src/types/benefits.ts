export interface BenefitProgram {
  id: string;
  name: string;
  type: "federal" | "state" | "local" | "nonprofit";
  category: "insurance" | "prescription" | "clinic" | "financial_assistance";
  description: string;
  eligibility_summary: string;
  income_limit_fpl_percent: number | null;
  age_min: number | null;
  age_max: number | null;
  requires_children: boolean;
  requires_disability: boolean;
  requires_pregnancy: boolean;
  states: string[];
  application_url: string;
  phone: string;
  estimated_savings: string;
}

export interface EligibilityInput {
  annual_income: number;
  household_size: number;
  state: string;
  age: number;
  has_children: boolean;
  is_pregnant: boolean;
  has_disability: boolean;
  currently_insured: boolean;
  zip_code: string;
}

export interface EligibilityResult {
  eligible_programs: BenefitProgram[];
  nearby_health_centers: HealthCenter[];
  fpl_percentage: number;
  summary: string;
}

export interface HealthCenter {
  name: string;
  address: string;
  phone: string;
  distance_miles: number;
  services: string[];
  sliding_scale: boolean;
  website: string;
}
