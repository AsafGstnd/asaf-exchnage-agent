# Guide: Upload Project to GitHub

Target repository: **https://github.com/AsafGstnd/asaf-exchnage-agent**

---

## Prerequisites

1. **Git** installed on your machine (`git --version` to check)
2. **GitHub account** with access to the repository
3. **Authentication** set up (SSH key or HTTPS with personal access token)

---

## Option A: First-Time Upload (New Clone)

If the repo is empty or you want to replace it with your local project:

### 1. Open Terminal and go to your project folder

```bash
cd /Users/asi/Downloads/fez-exchange-agent-feature-course-finder-react-agent
```

### 2. Initialize Git (if not already a repo)

```bash
git init
```

### 3. Add the remote repository

```bash
git remote add origin https://github.com/AsafGstnd/asaf-exchnage-agent.git
```

If `origin` already exists and you want to change it:

```bash
git remote set-url origin https://github.com/AsafGstnd/asaf-exchnage-agent.git
```

### 4. Stage all files

```bash
git add .
```

### 5. Create initial commit

```bash
git commit -m "Initial commit: Fez Exchange Agent - multi-agent university recommendation system"
```

### 6. Push to GitHub

**If the remote has no commits yet (empty repo):**

```bash
git branch -M main
git push -u origin main
```

**If the remote already has commits (e.g. README):**

```bash
git pull origin main --allow-unrelated-histories   # merge remote first
git push -u origin main
```

---

## Option B: Update Existing Repo (Already Has Git)

If your project already has `.git` and is linked to the repo:

### 1. Go to project folder

```bash
cd /Users/asi/Downloads/fez-exchange-agent-feature-course-finder-react-agent
```

### 2. Check status

```bash
git status
```

### 3. Stage changes

```bash
git add .
```

### 4. Commit

```bash
git commit -m "Update: conversation-aware orchestration, tool registry, caching, API compliance"
```

### 5. Push

```bash
git push origin main
```

If your default branch is `master`:

```bash
git push origin master
```

---

## Authentication

### HTTPS

GitHub no longer accepts account passwords. Use a **Personal Access Token (PAT)**:

1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate a new token with `repo` scope
3. When prompted for password, paste the token

### SSH

1. Generate a key: `ssh-keygen -t ed25519 -C "your_email@example.com"`
2. Add the public key to GitHub → Settings → SSH and GPG keys
3. Use SSH URL: `git remote set-url origin git@github.com:AsafGstnd/asaf-exchnage-agent.git`
4. Push: `git push origin main`

---

## What Gets Uploaded

- All files under the project root **except** those in `.gitignore`
- Typical exclusions: `venv/`, `.env`, `__pycache__/`, `*.pyc`, `outputs/` (if listed)

Check `.gitignore` to see what is excluded. **Never commit** `.env` or secrets.

---

## Quick Reference

| Command               | Purpose                    |
|-----------------------|----------------------------|
| `git status`          | See changed/untracked files|
| `git add .`           | Stage all changes          |
| `git commit -m "msg"` | Commit with message        |
| `git push origin main`| Push to GitHub             |
| `git remote -v`       | Show remote URLs           |
| `git log --oneline -5`| View recent commits        |

---

## Troubleshooting

**"Repository not found"**  
- Confirm you have write access to `AsafGstnd/asaf-exchnage-agent`  
- Verify the repo URL and your authentication

**"Updates were rejected"**  
- Someone else pushed changes; run `git pull origin main` first, fix conflicts if any, then `git push`

**Large files**  
- GitHub rejects files > 100 MB. Use Git LFS for large assets or exclude them in `.gitignore`
