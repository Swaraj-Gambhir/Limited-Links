import NextAuth, { NextAuthOptions } from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";

// Ensure your environment variables are correctly prefixed if accessed client-side,
// but for this server-side file, process.env should work directly for vars defined in .env.local or deployment environment.
const azureADClientId = process.env.AZURE_AD_CLIENT_ID;
const azureADClientSecret = process.env.AZURE_AD_CLIENT_SECRET;
const azureADTenantId = process.env.AZURE_AD_TENANT_ID;

if (!azureADClientId || !azureADClientSecret || !azureADTenantId) {
  console.error("Azure AD environment variables are not set. Check AZURE_AD_CLIENT_ID, AZURE_AD_CLIENT_SECRET, AZURE_AD_TENANT_ID");
  // Optionally, throw an error to prevent startup if these are critical
  // throw new Error("Azure AD environment variables are not fully set.");
}

export const authOptions: NextAuthOptions = {
  providers: [
    AzureADProvider({
      clientId: azureADClientId!,
      clientSecret: azureADClientSecret!,
      tenantId: azureADTenantId!,
      authorization: {
        params: {
          scope: `openid profile email offline_access api://${azureADClientId}/.default`
          // This scope requests an access token for your own application (API).
          // The audience ('aud' claim) of this token will be your application's Client ID.
          // 'offline_access' is included to allow for refresh tokens if needed.
        },
      },
      // If you had a profile callback, it can remain:
      // profile(profile) {
      //   console.log("DEBUG: NextAuth profile callback, profile object:", profile); // Good for debugging claims
      //   return {
      //     id: profile.oid, // Or profile.sub
      //     name: profile.name,
      //     email: profile.email || profile.upn,
      //     // Add other properties you need from the Azure AD profile
      //   };
      // },
    }),
  ],
  // Callbacks for JWT and session handling can remain as previously defined
  // Ensure they correctly handle the claims from a v2.0 token
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account && profile) { // profile is available only upon sign-in
        token.accessToken = account.access_token;
        // For v2.0 tokens, 'oid' is the user's object ID, 'sub' can also be used.
        // 'tid' is the tenant ID.
        token.id = profile.oid; 
        token.tenantId = profile.tid;
        // You can add other profile information to the token here if needed
        // console.log("DEBUG: NextAuth jwt callback - account:", account);
        // console.log("DEBUG: NextAuth jwt callback - profile:", profile);
      }
      // console.log("DEBUG: NextAuth jwt callback - token:", token);
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      // Ensure session.user is properly typed or checked before assigning
      if (session.user) {
        session.user.id = token.id as string;
        // session.user.tenantId = token.tenantId as string; // If needed on client-side session
      }
      // console.log("DEBUG: NextAuth session callback - session:", session);
      return session;
    },
  },
  secret: process.env.NEXTAUTH_SECRET, // From .env.local
  // debug: process.env.NODE_ENV === 'development', // Uncomment for more NextAuth logs
};

export default NextAuth(authOptions);
