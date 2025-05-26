import Link from 'next/link';
import styles from './Sidebar.module.css'; // We'll create a basic CSS module

export default function Sidebar() {
  return (
    <nav className={styles.sidebar}>
      <ul>
        <li>
          <Link href="/">Home</Link>
        </li>
        <li>
          <Link href="/upload">Upload New Folder</Link>
        </li>
        <li>
          <Link href="/folders">View Folders</Link>
        </li>
        {/* Add more links as needed */}
      </ul>
    </nav>
  );
}
