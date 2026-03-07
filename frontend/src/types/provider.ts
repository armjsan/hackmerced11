export interface Provider {
  npi: string;
  name: string;
  provider_type: "individual" | "organization";
  specialty: string;
  facility_type: string;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
  };
  phone: string;
  accepts_medicaid: boolean;
  accepts_medicare: boolean;
  sliding_scale: boolean;
  distance_miles?: number;
}

export interface ProcedurePrice {
  cpt_code: string;
  procedure_name: string;
  cash_price: number;
  medicare_rate: number | null;
  estimated_insured_price: number | null;
  price_range_low: number;
  price_range_high: number;
}

export interface ProviderDetail extends Provider {
  procedure_prices: ProcedurePrice[];
  hours: string;
  website?: string;
  rating?: number;
}
