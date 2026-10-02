# Agentic Study Assistant

A multi-agent study assistant (university assignment): course materials, RAG-grounded Q&A, quizzes, flashcards, summaries, and Google Calendar–aware study planning.

## What you need

- **Docker Desktop**, installed and running.
- **An OpenAI API key** and an **Anthropic API key** (step 2 says where to get them).
- **A Google account**, used both to sign in to the app and for the Google Calendar that the Study Planner reads and writes.

## How Google Calendar is connected

The Study Planner reaches Google Calendar through a **Calendar MCP server**. That server is part of this project (the `calendar-mcp` container) and starts automatically with `docker compose up`, so there is nothing to install for it. What it does need is a Google Cloud project where the **Google Calendar API is enabled**, plus an **OAuth client** so students can sign in with Google and grant Calendar access. Step 1 below sets both up. It takes about 10 minutes and is done once.

## Running it

### 1. Set up Google Cloud (one-time)

Google renames menus from time to time. If a link below doesn't land on the right page, use the search bar at the top of the console and search for the page name given in **bold**.

**1.1 Create a project**
1. Open https://console.cloud.google.com/projectcreate and sign in with your Google account.
2. **Project name:** `Study Assistant` (any name works).
3. Click **Create**, wait a few seconds, then make sure the new project is selected in the project picker at the top-left of the page.

**1.2 Enable the Google Calendar API**
1. Open https://console.cloud.google.com/apis/library/calendar-json.googleapis.com
   (or: menu ☰ → **APIs & Services** → **Library** → search `Google Calendar API` → click it).
2. Click **Enable**. The page then shows "API enabled".

**1.3 Configure the OAuth consent screen**

This is what students see when they click "Sign in with Google".
1. Open https://console.cloud.google.com/auth/overview
   (or: menu ☰ → **APIs & Services** → **OAuth consent screen**; newer consoles call it **Google Auth Platform**).
2. Click **Get started** and fill in:
   - **App name:** `Study Assistant`
   - **User support email:** your email
   - Click **Next**. For **Audience**, choose **External**, then **Next**.
   - **Contact information:** your email, then **Next**.
   - Tick the Google API Services user data policy checkbox, click **Continue**, then **Create**.
3. **Add test users.** Go to **Audience** (https://console.cloud.google.com/auth/audience). Leave **Publishing status** as **Testing**. Under **Test users**, click **Add users**, enter the Gmail address of **every account that will sign in** , and click **Save**. Only these accounts can sign in while the app is in Testing. This is also what lets university Google Workspace accounts sign in.

**1.4 Create the OAuth client (the credentials)**
1. Open https://console.cloud.google.com/apis/credentials
   (or: menu ☰ → **APIs & Services** → **Credentials**).
2. Click **+ Create credentials** → **OAuth client ID**.
3. **Application type:** `Web application`. **Name:** `Study Assistant web` (any name works).
4. Under **Authorized JavaScript origins**, click **+ Add URI** and enter:
   ```
   http://localhost:3000
   ```
5. Under **Authorized redirect URIs**, click **+ Add URI** and enter exactly this: `http`, not `https`, no trailing slash.
   ```
   http://localhost:3000/api/auth/callback
   ```
6. Click **Create**. A dialog shows the **Client ID** and **Client secret**. **Copy both now** (or click **Download JSON**). Newer consoles show the secret only once; if you lose it, open the client and click **Add secret** to make a new one.

### 2. Configure the app

1. In the project folder, copy `.env.example` to a new file named `.env`:
   ```
   cp .env.example .env          # macOS / Linux / Git Bash
   copy .env.example .env        # Windows Command Prompt / PowerShell
   ```
2. Open `.env` and fill in:
   - `GOOGLE_CLIENT_ID=` → the Client ID from step 1.4 (it ends in `.apps.googleusercontent.com`)
   - `GOOGLE_CLIENT_SECRET=` → the Client secret from step 1.4 (it starts with `GOCSPX-`)
   - `OPENAI_API_KEY` (used to index uploaded materials, You can create one from: https://platform.openai.com/api-keys )
   - `ANTHROPIC_API_KEY` (used by the chat assistant, You can create one from: https://platform.claude.com/settings/workspaces/default/keys)
   - `SECRET_KEY=` → any long random string. To generate one, run:
     ```
     python -c "import secrets; print(secrets.token_urlsafe(48))"
     ```

   The chat model defaults to `anthropic/claude-sonnet-5` (set in `CHAT_MODEL`); leave it as it is.


### 3. Start

1. Make sure Docker Desktop is running.
2. In the project folder, run:
   ```
   docker compose up --build
   ```
3. Open http://localhost:3000 and click **Sign in with Google**. Use an account you added as a test user in step 1.3.
   - Google shows **"Google hasn't verified this app"**. This is expected for an app in Testing: click **Continue**.
   - On the permissions screen, **tick the Google Calendar boxes**. Without Calendar access the app sends you back to the login page with an explanation, because the Study Planner depends on it.

The first build takes a few minutes. Docker installs every Python and Node package itself, so there is nothing else to install. No AI model is downloaded or run locally: the chat assistant calls Anthropic's API and material indexing calls OpenAI's embeddings API, using the keys from step 2.

To stop the app, press `Ctrl+C`, or run `docker compose down`. Your data stays in a Docker volume and is still there the next time you start.
