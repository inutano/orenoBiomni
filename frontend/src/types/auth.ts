export interface AuthUser {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  provider: string;
}

export interface AuthProviders {
  google: boolean;
  github: boolean;
  auth_enabled: boolean;
}
