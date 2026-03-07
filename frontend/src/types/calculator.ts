import { InsurancePlan } from "./insurance";

export type ServiceType = "office_visit" | "specialist" | "urgent_care" | "er" | "prescription" | "procedure" | "preventive" | "lab" | "imaging";

export interface CostScenario {
  service_type: ServiceType;
  service_name: string;
  retail_price: number;
  frequency: number;
}

export interface CostCalculationRequest {
  insurance_plan: InsurancePlan;
  scenarios: CostScenario[];
}

export interface CostLineItem {
  service_name: string;
  retail_price: number;
  frequency: number;
  annual_retail_cost: number;
  annual_insured_cost: number;
  deductible_applied: number;
  copay_applied: number;
  coinsurance_applied: number;
  insurance_paid: number;
  savings: number;
}

export interface CostCalculationResult {
  line_items: CostLineItem[];
  totals: {
    annual_premiums: number;
    annual_retail_total: number;
    annual_insured_total: number;
    annual_insurance_pays: number;
    deductible_used: number;
    deductible_remaining: number;
    oop_max_remaining: number;
    total_true_cost_insured: number;
    net_savings: number;
    insurance_value_ratio: number;
  };
  recommendation: string;
}
