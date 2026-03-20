export interface FileInfo {
  name: string;
  size: number;
  content_type: string;
  relative_path: string;
  modified_at: string;
  is_artifact: boolean;
}

export interface FileListResponse {
  files: FileInfo[];
  total_size: number;
}

export interface FileUploadResponse {
  uploaded: FileInfo[];
}
