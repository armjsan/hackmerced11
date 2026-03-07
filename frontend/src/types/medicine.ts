export interface Drug {
  ndc: string;
  brand_name: string;
  generic_name: string;
  dosage_form: string;
  strength: string;
  manufacturer: string;
  is_generic: boolean;
  rx_required: boolean;
}

export interface PharmacyPrice {
  pharmacy_name: string;
  pharmacy_type: "retail" | "online" | "mail_order";
  price: number;
  quantity: number;
  unit: string;
  price_per_unit: number;
  with_coupon: boolean;
  coupon_name?: string;
  last_updated: string;
}

export interface DrugPriceComparison {
  drug: Drug;
  nadac_price_per_unit: number | null;
  pharmacy_prices: PharmacyPrice[];
  lowest_price: number;
  highest_price: number;
  potential_savings: number;
  generic_alternative?: Drug;
}

export interface DrugSearchResult {
  drugs: Drug[];
  total_count: number;
  query: string;
}
