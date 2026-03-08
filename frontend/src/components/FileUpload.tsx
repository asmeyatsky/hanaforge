import { useState, useRef, useCallback } from 'react';

interface FileUploadProps {
  accept?: string;
  maxSizeMB?: number;
  onFileSelected: (file: File) => void;
  uploading?: boolean;
  uploadProgress?: number;
}

export default function FileUpload({
  accept = '.zip',
  maxSizeMB = 200,
  onFileSelected,
  uploading = false,
  uploadProgress,
}: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSelect = useCallback(
    (file: File) => {
      setError(null);

      // Validate file type
      if (accept && !file.name.toLowerCase().endsWith(accept.replace('*', ''))) {
        setError(`Invalid file type. Please upload a ${accept} file.`);
        return;
      }

      // Validate file size
      const maxBytes = maxSizeMB * 1024 * 1024;
      if (file.size > maxBytes) {
        setError(`File too large. Maximum size is ${maxSizeMB}MB.`);
        return;
      }

      setSelectedFile(file);
      onFileSelected(file);
    },
    [accept, maxSizeMB, onFileSelected],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);

      const file = e.dataTransfer.files[0];
      if (file) {
        validateAndSelect(file);
      }
    },
    [validateAndSelect],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        validateAndSelect(file);
      }
    },
    [validateAndSelect],
  );

  return (
    <div className="space-y-3">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => inputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
          dragOver
            ? 'border-accent-500 bg-accent-50'
            : 'border-slate-300 hover:border-slate-400 hover:bg-slate-50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleInputChange}
          className="hidden"
        />

        {uploading ? (
          <div className="space-y-3">
            <svg className="animate-spin w-10 h-10 mx-auto text-accent-600" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <p className="text-sm font-medium text-slate-600">
              Uploading and parsing...
            </p>
            {uploadProgress !== undefined && (
              <div className="w-48 mx-auto bg-slate-200 rounded-full h-1.5">
                <div
                  className="bg-accent-500 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            )}
          </div>
        ) : (
          <div>
            <svg
              className={`w-10 h-10 mx-auto ${
                dragOver ? 'text-accent-500' : 'text-slate-300'
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
              />
            </svg>
            <p className="mt-3 text-sm font-medium text-slate-600">
              {selectedFile ? (
                <>
                  Selected:{' '}
                  <span className="text-accent-600">{selectedFile.name}</span>
                  <span className="text-slate-400">
                    {' '}
                    ({(selectedFile.size / 1024 / 1024).toFixed(1)} MB)
                  </span>
                </>
              ) : (
                <>
                  Drop your ABAP source ZIP here, or{' '}
                  <span className="text-accent-600 underline">browse</span>
                </>
              )}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              ZIP files up to {maxSizeMB}MB
            </p>
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-danger-50 border border-danger-200 rounded-lg text-sm text-danger-700">
          {error}
        </div>
      )}
    </div>
  );
}
