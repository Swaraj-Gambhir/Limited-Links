import React, { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import Link from 'next/link'; // For linking to a future view page
import Layout from '../components/Layout';
// import styles from './Folders.module.css'; // Optional: for page-specific styling

interface FolderItem {
  id: string; // SharePoint item ID or path
  name: string;
  // Add other properties if your backend's FolderItem model includes them
}

export default function FoldersPage() {
  const { data: session, status } = useSession();
  const loading = status === 'loading';
  const [folders, setFolders] = useState<FolderItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoadingFolders, setIsLoadingFolders] = useState(false);

  useEffect(() => {
    if (session) {
      const fetchFolders = async () => {
        setIsLoadingFolders(true);
        setError(null);
        try {
          const response = await fetch('/api/v1/list-folders/', {
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
      {!isLoadingFolders && !error && folders.length === 0 && (
        <p>You haven't uploaded any folders yet.</p>
      )}
      {!isLoadingFolders && !error && folders.length > 0 && (
        <ul>
          {folders.map((folder) => (
            <li key={folder.id}>
              {folder.name}
              {/* 
                Placeholder for view link. 
                The href will eventually point to a page like /view/[folderId] 
                or trigger an action to generate and navigate to a temporary view link.
              */}
              {/* <Link href={`/view/${folder.id}`}> View </Link> */}
              <button onClick={() => alert(`Viewing folder: ${folder.name} (ID: ${folder.id}) - Link generation TBD`)} style={{ marginLeft: '10px' }}>
                View (Placeholder)
              </button>
            </li>
          ))}
        </ul>
      )}
      {/* You might want a link to the upload page from here if no folders exist */}
      {!isLoadingFolders && folders.length === 0 && (
         <p>Want to upload something? <Link href="/upload">Upload a folder</Link></p>
      )}
    </Layout>
  );
}
