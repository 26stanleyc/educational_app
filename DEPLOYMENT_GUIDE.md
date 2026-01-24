# Deployment Guide: Algebra 1 Coach

This guide covers multiple ways to deploy your Streamlit app so others can use it as a website.

## Prerequisites

Before deploying, ensure you have:
- ✅ API keys for:
  - `ANTHROPIC_API_KEY` (required)
  - `LLAMA_CLOUD_API_KEY` (optional, for PDF parsing)
- ✅ A GitHub account (for most deployment options)
- ✅ Your code pushed to a GitHub repository

---

## Option 1: Streamlit Cloud (Recommended - Easiest)

**Best for:** Quick deployment, free hosting, automatic updates

### Steps:

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git push -u origin main
   ```

2. **Create a `.streamlit/secrets.toml` file** (for local testing, don't commit this!)
   ```toml
   ANTHROPIC_API_KEY = "your-anthropic-key-here"
   LLAMA_CLOUD_API_KEY = "your-llama-key-here"
   ```

3. **Go to [share.streamlit.io](https://share.streamlit.io)**
   - Sign in with GitHub
   - Click "New app"
   - Select your repository and branch
   - Set main file path: `ui.py`
   - Click "Deploy"

4. **Add secrets in Streamlit Cloud**
   - Go to your app settings
   - Click "Secrets"
   - Add your API keys:
     ```toml
     ANTHROPIC_API_KEY = "your-key"
     LLAMA_CLOUD_API_KEY = "your-key"
     ```

5. **Your app will be live at:** `https://YOUR_APP_NAME.streamlit.app`

**Pros:**
- ✅ Free
- ✅ Automatic deployments on git push
- ✅ Built-in secrets management
- ✅ No server management

**Cons:**
- ⚠️ Limited customization
- ⚠️ Public apps are free, private apps require Team plan

---

## Option 2: Heroku

**Best for:** More control, custom domains, background workers

### Steps:

1. **Create a `Procfile`**
   ```
   web: streamlit run ui.py --server.port=$PORT --server.address=0.0.0.0
   ```

2. **Create a `setup.sh`** (for Streamlit configuration)
   ```bash
   mkdir -p ~/.streamlit/
   echo "\
   [server]\n\
   headless = true\n\
   port = $PORT\n\
   enableCORS = false\n\
   \n\
   " > ~/.streamlit/config.toml
   ```

3. **Update `requirements.txt`** (add gunicorn if needed)
   ```
   anthropic>=0.18.0
   pymupdf>=1.23.0
   streamlit>=1.28.0
   llama-parse>=0.6.0
   ```

4. **Deploy to Heroku**
   ```bash
   heroku create your-app-name
   heroku config:set ANTHROPIC_API_KEY=your-key
   heroku config:set LLAMA_CLOUD_API_KEY=your-key
   git push heroku main
   ```

**Pros:**
- ✅ Custom domains
- ✅ More control over environment
- ✅ Add-ons available

**Cons:**
- ⚠️ Requires credit card (free tier limited)
- ⚠️ More setup required

---

## Option 3: Railway

**Best for:** Simple deployment, good free tier, modern platform

### Steps:

1. **Create a `railway.json`** (optional)
   ```json
   {
     "$schema": "https://railway.app/railway.schema.json",
     "build": {
       "builder": "NIXPACKS"
     },
     "deploy": {
       "startCommand": "streamlit run ui.py --server.port=$PORT --server.address=0.0.0.0",
       "restartPolicyType": "ON_FAILURE",
       "restartPolicyMaxRetries": 10
     }
   }
   ```

2. **Deploy**
   - Go to [railway.app](https://railway.app)
   - Sign in with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Add environment variables in the dashboard

**Pros:**
- ✅ Generous free tier
- ✅ Simple setup
- ✅ Automatic HTTPS

**Cons:**
- ⚠️ Free tier has usage limits

---

## Option 4: Render

**Best for:** Free tier, easy setup, good documentation

### Steps:

1. **Create a `render.yaml`** (optional)
   ```yaml
   services:
     - type: web
       name: algebra-coach
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: streamlit run ui.py --server.port=$PORT --server.address=0.0.0.0
       envVars:
         - key: ANTHROPIC_API_KEY
           sync: false
         - key: LLAMA_CLOUD_API_KEY
           sync: false
   ```

2. **Deploy**
   - Go to [render.com](https://render.com)
   - Sign in with GitHub
   - Click "New" → "Web Service"
   - Connect your repository
   - Set start command: `streamlit run ui.py --server.port=$PORT --server.address=0.0.0.0`
   - Add environment variables

**Pros:**
- ✅ Free tier available
- ✅ Easy to use
- ✅ Good documentation

**Cons:**
- ⚠️ Free tier spins down after inactivity

---

## Option 5: DigitalOcean App Platform

**Best for:** Production apps, scalable, reliable

### Steps:

1. **Create `app.yaml`**
   ```yaml
   name: algebra-coach
   services:
     - name: web
       source_dir: /
       github:
         repo: YOUR_USERNAME/YOUR_REPO
         branch: main
       run_command: streamlit run ui.py --server.port=8080 --server.address=0.0.0.0
       environment_slug: python
       instance_count: 1
       instance_size_slug: basic-xxs
       envs:
         - key: ANTHROPIC_API_KEY
           scope: RUN_TIME
           type: SECRET
         - key: LLAMA_CLOUD_API_KEY
           scope: RUN_TIME
           type: SECRET
   ```

2. **Deploy via DigitalOcean dashboard**

**Pros:**
- ✅ Production-ready
- ✅ Scalable
- ✅ Good performance

**Cons:**
- ⚠️ Paid service (starts at $5/month)

---

## Option 6: Self-Hosted (VPS)

**Best for:** Full control, custom setup, learning

### Steps:

1. **Set up a VPS** (DigitalOcean, Linode, AWS EC2, etc.)

2. **Install dependencies**
   ```bash
   sudo apt update
   sudo apt install python3-pip nginx
   pip3 install -r requirements.txt
   ```

3. **Create systemd service** (`/etc/systemd/system/streamlit.service`)
   ```ini
   [Unit]
   Description=Streamlit App
   After=network.target

   [Service]
   Type=simple
   User=your-user
   WorkingDirectory=/path/to/your/app
   Environment="ANTHROPIC_API_KEY=your-key"
   Environment="LLAMA_CLOUD_API_KEY=your-key"
   ExecStart=/usr/bin/streamlit run ui.py --server.port=8501
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

4. **Set up Nginx reverse proxy**
5. **Configure SSL with Let's Encrypt**

**Pros:**
- ✅ Full control
- ✅ Can be cost-effective
- ✅ Learn server management

**Cons:**
- ⚠️ Requires technical knowledge
- ⚠️ You manage security/updates

---

## Security Checklist

Before deploying publicly:

- [ ] Never commit API keys to git
- [ ] Use environment variables or secrets management
- [ ] Add rate limiting (consider using Streamlit's built-in options)
- [ ] Consider adding authentication if needed
- [ ] Review file upload size limits
- [ ] Set up monitoring/error tracking (optional)

---

## Cost Comparison

| Platform | Free Tier | Paid Starts At | Best For |
|----------|-----------|----------------|----------|
| Streamlit Cloud | ✅ Yes | $20/month (Team) | Quick deployment |
| Heroku | ⚠️ Limited | $7/month | Custom domains |
| Railway | ✅ Yes | $5/month | Modern platform |
| Render | ✅ Yes | $7/month | Simple setup |
| DigitalOcean | ❌ No | $5/month | Production |
| VPS | ❌ No | $5/month | Full control |

---

## Recommended: Start with Streamlit Cloud

For your use case, **Streamlit Cloud is the best starting point** because:
1. Your app is already built with Streamlit
2. Zero configuration needed
3. Free for public apps
4. Automatic deployments
5. Built-in secrets management

Once you outgrow it or need more features, you can migrate to other platforms.

---

## Next Steps

1. **Choose a deployment platform** (recommend Streamlit Cloud)
2. **Push your code to GitHub**
3. **Set up API keys as secrets**
4. **Deploy!**
5. **Share your URL** with users

---

## Troubleshooting

### App won't start
- Check that `ui.py` is the correct entry point
- Verify all dependencies are in `requirements.txt`
- Check logs for error messages

### API keys not working
- Ensure secrets are set correctly in your platform
- Verify key names match exactly (case-sensitive)
- Check that keys are valid and have credits

### PDF parsing not working
- Verify `LLAMA_CLOUD_API_KEY` is set
- Check that `llama-parse` is in requirements.txt
- Review PDF file size limits on your platform

---

## Need Help?

- Streamlit docs: https://docs.streamlit.io
- Streamlit Cloud: https://docs.streamlit.io/streamlit-community-cloud
- Your platform's documentation

Good luck with your deployment! 🚀

