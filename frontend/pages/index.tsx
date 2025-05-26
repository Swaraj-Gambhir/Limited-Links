import { useSession } from "next-auth/react";
import Layout from '../components/Layout'; // We will create this

export default function HomePage() {
  const { data: session } = useSession();

  return (
    <Layout>
      <h1>Welcome to the Folder Viewer App</h1>
      {session && <p>You are signed in as {session.user?.name || session.user?.email}.</p>}
      <p>This is the main dashboard area. More content will be added here soon.</p>
      {/* Future dashboard components will go here */}
    </Layout>
  );
}
