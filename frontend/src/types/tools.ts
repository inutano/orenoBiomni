export interface ToolModule {
  domain: string;
  name: string;
  description: string;
  function_count: number;
}

export interface ToolListResponse {
  tools: ToolModule[];
  total: number;
}

export interface Dataset {
  name: string;
  description: string;
  category: "data_lake" | "library";
}

export interface DatasetListResponse {
  datasets: Dataset[];
  total: number;
}
