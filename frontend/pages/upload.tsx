import React, { useState, ChangeEvent } from 'react';
import { useSession } from 'next-auth/react';
import Layout from '../components/Layout'; // Using the existing Layout
// import styles from './Upload.module.css'; // Optional: for page-specific styling

export default function UploadPage() {
  const { data: session } = useSession();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const selectedFile = event.target.files[0];
      if (selectedFile.name.endsWith('.zip')) {
        setFile(selectedFile);
        setError(null); // Clear previous error
      } else {
        setFile(null);
        setError('Invalid file type. Please upload a .zip file.');
      }
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError('Please select a .zip file to upload.');
      return;
    }
    if (!session || !session.accessToken) {
      setError('You must be logged in to upload files.');
      return;
    }

    setUploading(true);
    setMessage(null);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/v1/upload-zipped-folder/', { // Assuming backend runs on the same base URL or proxy is set up
        method: 'POST',
        headers: {
          // NextAuth.js automatically handles the Authorization header for relative API routes
          // if the backend is on a different domain, you'd need to manually add:
          'Authorization': `Bearer ${session.accessToken}`,
        },
        body: formData,
      });

      const result = await response.json();

      if (response.ok) {
        setMessage(result.message || 'File uploaded successfully!');
        setFile(null); // Clear the file input
        // Optionally, clear the actual input element value
        const fileInput = document.getElementById('fileInput') as HTMLInputElement;
        if (fileInput) {
            fileInput.value = "";
        }
      } else {
        setError(result.detail || 'Upload failed. Please try again.');
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError('An unexpected error occurred during upload.');
    } finally {
      setUploading(false);
    }
  };

  if (!session) {
    return (
      <Layout>
        <h1>Upload Folder</h1>
        <p>Please log in to upload folders.</p>
      </Layout>
    );
  }

  return (
    <Layout>
      <h1>Upload Zipped Folder</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="fileInput">Choose a .zip file:</label>
          <input 
            type="file" 
            id="fileInput"
            accept=".zip" 
            onChange={handleFileChange} 
            disabled={uploading}
          />
        </div>
        {file && <p>Selected file: {file.name}</p>}
        <button type="submit" disabled={uploading || !file}>
          {uploading ? 'Uploading...' : 'Upload'}
        </button>
      </form>
      {message && <p style={{ color: 'green' }}>{message}</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {/* Basic styling can be added via a CSS module or global styles */}
    </Layout>
  );
}
