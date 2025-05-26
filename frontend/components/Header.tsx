import Link from 'next/link';
import { useSession, signIn, signOut } from 'next-auth/react';
import styles from './Header.module.css';

export default function Header() {
  const { data: session, status } = useSession();
  const loading = status === 'loading';

  return (
    <header className={styles.header}>
      <div className={styles.logo}>
        <Link href="/">MyApp</Link>
      </div>
      <div className={styles.authControls}>
        {loading && <p>Loading...</p>}
        {!session && !loading && (
          <button onClick={() => signIn('azure-ad')}>Sign in</button>
        )}
        {session?.user && (
          <>
            <span style={{ marginRight: '10px' }}>
              {session.user.name || session.user.email}
            </span>
            <button onClick={() => signOut()}>Sign out</button>
          </>
        )}
      </div>
    </header>
  );
}
