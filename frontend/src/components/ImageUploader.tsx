import { useState, useRef, useCallback } from "react";
import { ImageSummary, TaskImage } from "../types/task";
import { apiUploadFile, apiFetch, ApiError } from "../utils/api";
import "./ImageUploader.css";

interface ImageUploaderProps {
  taskId: string;
  images: ImageSummary[];
  onImagesChange: () => void;
}

export function ImageUploader({
  taskId,
  images,
  onImagesChange,
}: ImageUploaderProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;

      setIsUploading(true);
      setUploadError(null);

      try {
        for (const file of Array.from(files)) {
          await apiUploadFile<TaskImage>(`/tasks/${taskId}/images`, file);
        }
        onImagesChange();
      } catch (err) {
        if (err instanceof ApiError) {
          setUploadError(err.message);
        } else {
          setUploadError("Failed to upload image");
        }
      } finally {
        setIsUploading(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    },
    [taskId, onImagesChange]
  );

  const handleDelete = useCallback(
    async (imageId: string) => {
      try {
        await apiFetch(`/tasks/${taskId}/images/${imageId}`, {
          method: "DELETE",
        });
        onImagesChange();
      } catch (err) {
        if (err instanceof ApiError) {
          setUploadError(err.message);
        } else {
          setUploadError("Failed to delete image");
        }
      }
    },
    [taskId, onImagesChange]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      handleUpload(e.dataTransfer.files);
    },
    [handleUpload]
  );

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="image-uploader">
      <h3 className="image-uploader__title">Images</h3>
      <p className="image-uploader__hint">
        Attach images to provide visual context for Claude Code
      </p>

      {/* Upload area */}
      <div
        className={`image-uploader__dropzone ${isDragOver ? "image-uploader__dropzone--dragover" : ""} ${isUploading ? "image-uploader__dropzone--uploading" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp"
          multiple
          onChange={(e) => handleUpload(e.target.files)}
          className="image-uploader__input"
        />
        {isUploading ? (
          <span className="image-uploader__uploading-text">Uploading...</span>
        ) : (
          <>
            <span className="image-uploader__icon">+</span>
            <span className="image-uploader__text">
              Drop images here or click to upload
            </span>
            <span className="image-uploader__subtext">
              PNG, JPEG, GIF, WebP (max 10MB)
            </span>
          </>
        )}
      </div>

      {/* Error message */}
      {uploadError && (
        <div className="image-uploader__error">
          <span>{uploadError}</span>
          <button onClick={() => setUploadError(null)}>Dismiss</button>
        </div>
      )}

      {/* Image list */}
      {images.length > 0 && (
        <div className="image-uploader__list">
          {images.map((image) => (
            <div key={image.id} className="image-uploader__item">
              <div className="image-uploader__item-preview">
                <img
                  src={`/api/v1/tasks/${taskId}/images/${image.id}`}
                  alt={image.original_filename}
                  loading="lazy"
                />
              </div>
              <div className="image-uploader__item-info">
                <span className="image-uploader__item-name">
                  {image.original_filename}
                </span>
                <span className="image-uploader__item-size">
                  {formatFileSize(image.size_bytes)}
                </span>
              </div>
              <button
                className="image-uploader__item-delete"
                onClick={() => handleDelete(image.id)}
                title="Delete image"
              >
                x
              </button>
            </div>
          ))}
        </div>
      )}

      {images.length === 0 && (
        <p className="image-uploader__empty">No images attached</p>
      )}
    </div>
  );
}
