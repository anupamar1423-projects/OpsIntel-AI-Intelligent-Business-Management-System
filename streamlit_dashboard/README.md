---
title: OpsIntel AI Analytics
emoji: 📈
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8501
---

# OpsIntel AI Analytics

This is the Streamlit analytics and model-training interface for OpsIntel AI. The main Django business application is in the parent folder. This app uses fictional, generated data by default and does not connect to or store a real company database.

Build the Docker image from this directory. The image generates the sample datasets and trains the demo models during build, then serves Streamlit on port 8501.
