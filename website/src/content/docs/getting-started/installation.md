---
title: Installation
description: Install and run AI Test Lab locally.
---

# Installation

## Clone the repository

```bash
git clone https://github.com/AnthonyVinokur/AI-Test-Lab.git
cd AI-Test-Lab
```

## Create a virtual environment

```bash
python -m venv .venv
```

## Activate the environment on Windows

```powershell
.venv\Scripts\Activate.ps1
```

## Install dependencies

```bash
pip install -r requirements.txt
```

## Run the tests

```bash
python -m pytest -v
```

## Run AI Test Lab

```bash
python main.py
```