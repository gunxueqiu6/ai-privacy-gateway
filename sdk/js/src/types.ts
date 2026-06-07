export interface Entity {
  type: string;
  value: string;
  placeholder: string;
  position?: number;
}

export interface MaskResult {
  masked_text: string;
  entities: Entity[];
  stats: Record<string, number>;
}

export interface RestoreResult {
  original_text: string;
}

export interface BatchMaskResult {
  original: string;
  masked: string;
  entities: Entity[];
  stats: Record<string, number>;
}

export interface BatchMaskResponse {
  results: BatchMaskResult[];
  total_count: number;
}

export interface EntityType {
  type: string;
  name: string;
  description: string;
  enabled: boolean;
}

export interface EntitiesResponse {
  entities: EntityType[];
  total: number;
  version: string;
}

export interface GatewayConfig {
  baseUrl: string;
  timeout?: number;
  headers?: Record<string, string>;
}

export interface ErrorResponse {
  error: string;
}