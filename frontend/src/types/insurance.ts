export type PlanType = "hmo" | "ppo" | "epo" | "hdhp" | "pos" | "other";

export interface InsurancePlan {
  plan_name: string;
  plan_type: PlanType;
  monthly_premium: number;
  annual_deductible_individual: number;
  annual_deductible_family: number | null;
  copay_primary: number;
  copay_specialist: number;
  copay_urgent_care: number;
  copay_er: number;
  copay_generic_rx: number;
  copay_brand_rx: number;
  coinsurance_percent: number;
  out_of_pocket_max_individual: number;
  out_of_pocket_max_family: number | null;
  covers_preventive_free: boolean;
  rx_deductible_separate: boolean;
  rx_deductible_amount: number | null;
}
