import { useSession, signIn, signOut } from "next-auth/react";
import { GetServerSidePropsContext } from "next";
import { getSession } from "next-auth/react"; // Import getSession

// It's good practice to wrap the page content with SessionProvider at the _app.tsx level
// For this example, we'll just use useSession here directly.
// You would typically create `frontend/pages/_app.tsx` and wrap <Component {...pageProps} /> with <SessionProvider session={pageProps.session}>

export default function Home() {
  const { data: session, status } = useSession();
  const loading = status === "loading";

  if (loading) {
    return <p>Loading...</p>;
  }

  return (
    <div style={{ padding: "20px" }}>
      <h1>Next.js Azure AD Auth</h1>
      {!session && (
        <>
          <p>Not signed in</p>
          <button onClick={() => signIn("azure-ad")}>Sign in with Microsoft</button>
        </>
      )}
      {session && session.user && (
        <>
          <p>Signed in as: <strong>{session.user.name || session.user.email}</strong></p>
          <p>User ID: {session.user.id}</p>
          {/* <p>Access Token (first 20 chars): {session.accessToken?.substring(0, 20)}...</p> */}
          <button onClick={() => signOut()}>Sign out</button>
          
          {/* Example: How to get the token to send to backend */}
          {/* <pre>{JSON.stringify(session, null, 2)}</pre> */}
        </>
      )}
    </div>
  );
}

// Optional: If you want to pre-fetch the session on the server-side
// export async function getServerSideProps(context: GetServerSidePropsContext) {
//   const session = await getSession(context);
//   return {
//     props: {
//       session,
//     },
//   };
// }
