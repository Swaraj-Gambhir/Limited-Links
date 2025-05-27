import NextAuth, { NextAuthOptions } from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";

export const authOptions: NextAuthOptions = {
  providers: [
    AzureADProvider({
      clientId: process.env.AZURE_AD_CLIENT_ID!,
      clientSecret: process.env.AZURE_AD_CLIENT_SECRET!,
      tenantId: process.env.AZURE_AD_TENANT_ID!,
      authorization: {
        // explicitly hit the v2.0 authorize endpoint
        url: `https://login.microsoftonline.com/${process.env.AZURE_AD_TENANT_ID}/oauth2/v2.0/authorize`,
        params: {
          // request the v2.0 scopes you exposed
          scope: [
            "openid",
            "profile",
            "email",
            "offline_access",                           // for refresh tokens
            `api://${process.env.AZURE_AD_CLIENT_ID}/access_as_user/Write`
          ].join(" "),
          response_type: "code",                         // authorization code flow
          response_mode: "query"
        },
      },
    }),
  ],
  // Optional: Add callbacks for JWT and session handling
  callbacks: {
    async jwt({ token, account, profile }) {
      // Persist the access_token and other necessary info to the token right after signin
      if (account && profile) {
  token.accessToken = account.access_token;
  token.idToken = account.id_token;  // <-- add this
  token.id = profile.oid;
  token.tenantId = profile.tid;
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
