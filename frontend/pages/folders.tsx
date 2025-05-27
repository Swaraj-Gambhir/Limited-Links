import React, { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import Link from 'next/link';
import Layout from '../components/Layout';

interface FolderItem {
  id: string;
  name: string;
}

export default function FoldersPage() {
  const { data: session, status } = useSession();
  const loading = status === 'loading';
  const [folders, setFolders] = useState<FolderItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingFolders, setIsLoadingFolders] = useState(false);
  const [viewLink, setViewLink] = useState<string | null>(null); // For storing and displaying the generated link

  useEffect(() => {
    if (session) {
      const fetchFolders = async () => {
        setIsLoadingFolders(true);
        setError(null);
        setViewLink(null); // Clear previous link
        
        console.log("Access token:", session.accessToken);
        try {
          const response = await fetch('http://localhost:8000/api/v1/list-folders/', {
            headers: {
              'Authorization': `Bearer ${session.accessToken}`,
            },
          });

          if (response.ok) {
            const data: FolderItem[] = await response.json();
            setFolders(data);
          } else {
            const errorData = await response.json();
            setError(errorData.detail || 'Failed to fetch folders.');
          }
        } catch (err) {
          console.error('Failed to fetch folders:', err);
          setError('An unexpected error occurred while fetching folders.');
        } finally {
          setIsLoadingFolders(false);
        }
      };
      fetchFolders();
    }
  }, [session]);

  const handleGenerateViewLink = async (folderIdentifier: string, folderName: string) => {
    if (!session) return;
    setError(null);
    setViewLink(null);

    try {
      const response = await fetch(`http://localhost:8000/api/v1/generate-view-link/${encodeURIComponent(folderIdentifier)}`, {
        method: 'GET', // Or POST if your backend expects that
        headers: {
          'Authorization': `Bearer ${session.accessToken}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        // Construct the full URL for the link to be opened in a new tab
        const fullViewLink = `http://localhost:8000${data.view_link}`;
        setViewLink(fullViewLink);
        // Open in new tab:
        // window.open(fullViewLink, '_blank'); 
        // Or display it:
        alert(`View link for ${folderName}: ${fullViewLink}\n\n(This will be displayed on the page instead of an alert)`);
      } else {
        const errorData = await response.json();
        setError(errorData.detail || `Failed to generate link for ${folderName}.`);
      }
    } catch (err) {
      console.error(`Error generating link for ${folderName}:`, err);
      setError(`An unexpected error occurred while generating the link for ${folderName}.`);
    }
  };


  if (loading) {
    return <Layout><p>Loading session...</p></Layout>;
  }

  if (!session) {
    return (
      <Layout>
        <h1>My Folders</h1>
        <p>Please log in to view your uploaded folders.</p>
      </Layout>
    );
  }

  return (
    <Layout>
      <h1>My Uploaded Folders</h1>
      {isLoadingFolders && <p>Loading folders...</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      
      {viewLink && (
        <div style={{ margin: '20px 0', padding: '10px', border: '1px solid green' }}>
          <p>Generated View Link: <a href={viewLink} target="_blank" rel="noopener noreferrer">{viewLink}</a></p>
          <p><small>(Link will expire in {process.env.NEXT_PUBLIC_VIEW_TOKEN_EXPIRE_MINUTES || 15} minutes)</small></p>
        </div>
      )}

      {!isLoadingFolders && !error && folders.length === 0 && (
        <p>You haven't uploaded any folders yet.</p>
      )}
      {!isLoadingFolders && !error && folders.length > 0 && (
        <ul>
          {folders.map((folder) => (
            <li key={folder.id}>
              {folder.name}
              <button onClick={() => handleGenerateViewLink(folder.id, folder.name)} style={{ marginLeft: '10px' }}>
                Generate View Link
              </button>
            </li>
          ))}
        </ul>
      )}
      {!isLoadingFolders && folders.length === 0 && (
         <p>Want to upload something? <Link href="/upload">Upload a folder</Link></p>
      )}
    </Layout>
  );
}
