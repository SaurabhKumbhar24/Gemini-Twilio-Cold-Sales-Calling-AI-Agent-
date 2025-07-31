# Gemini-Twilio Cold Sales Calling AI Agent

# Cold Calling Sales Agent


This project is a voice-enabled AI sales assistant that automatically initiates and handles cold sales calls using **Twilio**, **Gemini (Google AI)**, and **FastAPI**. It acts as a friendly and persuasive sales rep for your company, records real-time transcripts, and stores them in a **public Google Sheet** via a **Google Apps Script endpoint** — all without needing OAuth.

---

## ✨ Features

- 🤖 AI-powered sales assistant ("Emily") using **Gemini 2.5 Flash** with native audio dialog.
- 📞 Outbound call initiation with **Twilio Programmable Voice**
- 🔁 Real-time voice streaming via Twilio `<Connect><Stream>`
- 🎙️ Converts MuLaw audio to PCM and vice versa
- 🧠 Natural-sounding conversation managed entirely by Gemini
- 📋 Full transcript generation and **call tracking**
- 📊 Stores call metadata and full conversation in **public Google Sheets**
- 🌐 Hosted with **FastAPI** and WebSocket support

---

## 🛠️ Tech Stack

- **FastAPI** – Backend API & WebSocket server
- **Twilio** – Programmable Voice for call initiation and audio streaming
- **Google Gemini** – Audio-dialog model for conversational AI
- **NumPy, SciPy, Audioop** – Audio resampling & format conversion
- **Google Apps Script Webhook** – Stores data in a public Google Sheet (no OAuth)
- **gTTS + Base64** – Audio encoding & decoding