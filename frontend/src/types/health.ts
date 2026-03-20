export interface HealthResponse {
  status: string;
  agent_ready: boolean;
  database: string;
  redis: string;
  celery_active: boolean;
  version: string;
}
