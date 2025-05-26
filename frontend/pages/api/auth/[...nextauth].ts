import NextAuth, { NextAuthOptions } from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";

export const authOptions: NextAuthOptions = {
  providers: [
    AzureADProvider({
      clientId: process.env.AZURE_AD_CLIENT_ID!,
      clientSecret: process.env.AZURE_AD_CLIENT_SECRET!,
      tenantId: process.env.AZURE_AD_TENANT_ID!,
      // If you want to customize token claims:
      // profile(profile) {
      //   return {
      //     id: profile.oid, // Or profile.sub
      //     name: profile.name,
      //     email: profile.email || profile.upn,
      //     // Add other properties you need from the Azure AD profile
      //   };
      // },
    }),
  ],
  // Optional: Add callbacks for JWT and session handling
  callbacks: {
    async jwt({ token, account, profile }) {
      // Persist the access_token and other necessary info to the token right after signin
      if (account && profile) {
        token.accessToken = account.access_token;
        token.id = profile.oid; // Or profile.sub from Azure AD
        token.tenantId = profile.tid; // Tenant ID
        // You can add other profile information to the token here
      }
      return token;
    },
    async session({ session, token }) {
      // Send properties to the client, like an access_token and user id from the token
      session.accessToken = token.accessToken as string;
      session.user.id = token.id as string;
      // session.user.tenantId = token.tenantId as string; // If needed
      return session;
    },
  },
  // If using a custom secret for JWT signing (recommended)
  secret: process.env.NEXTAUTH_SECRET,
  // Enable debug messages in the console if you are having problems
  // debug: process.env.NODE_ENV === 'development',
};

export default NextAuth(authOptions);
