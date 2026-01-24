# Quick Start: Deploy Your Algebra 1 Coach App

## Fastest Way: Streamlit Cloud (5 minutes)

### Step 1: Push to GitHub
```bash
# If you haven't initialized git yet
git init
git add .
git commit -m "Initial commit"

# Create a new repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **"New app"**
4. Select your repository
5. Set **Main file path:** `ui.py`
6. Click **"Deploy"**

### Step 3: Add API Keys
1. In your app dashboard, go to **Settings** → **Secrets**
2. Add your keys:
   ```toml
   ANTHROPIC_API_KEY = "your-anthropic-key"
   LLAMA_CLOUD_API_KEY = "your-llama-key"
   ```
3. Your app will automatically redeploy

### Step 4: Share Your App!
Your app will be live at: `https://YOUR_APP_NAME.streamlit.app`

---

## What You Need

- **Anthropic API Key** (Required)
  - Get it from: https://console.anthropic.com/
  - Used for the tutoring AI

- **LlamaCloud API Key** (Optional, for PDF parsing)
  - Get it from: https://cloud.llamaindex.ai/
  - Used for automatic question extraction from PDFs

---

## Testing Locally First

Before deploying, test locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="your-key"
export LLAMA_CLOUD_API_KEY="your-key"

# Run the app
streamlit run ui.py
```

Or create `.streamlit/secrets.toml` (this file is gitignored):
```toml
ANTHROPIC_API_KEY = "your-key"
LLAMA_CLOUD_API_KEY = "your-key"
```

---

## Other Deployment Options

See `DEPLOYMENT_GUIDE.md` for:
- Heroku
- Railway
- Render
- DigitalOcean
- Self-hosting

---

## Troubleshooting

**App won't start?**
- Check that `ui.py` exists and is the main file
- Verify all dependencies in `requirements.txt`
- Check the deployment logs

**API errors?**
- Verify your API keys are set correctly
- Check that keys have credits/are valid
- Review error messages in the app logs

**PDF parsing not working?**
- Ensure `LLAMA_CLOUD_API_KEY` is set
- Check PDF file size limits
- Verify the PDF format is supported

---

## Next Steps

1. ✅ Deploy your app
2. 🎨 Customize the UI (optional)
3. 📊 Add analytics (optional)
4. 🔒 Consider adding authentication (optional)
5. 📢 Share with your users!

---

**Need help?** Check `DEPLOYMENT_GUIDE.md` for detailed instructions.

