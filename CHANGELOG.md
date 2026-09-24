# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Chat with streaming responses over a Groq/OpenAI-compatible endpoint
- Persistent per-user conversation memory (SQLite locally, Postgres in production)
- Multi-step research mode with query planning, budgeted search via Tavily, and source synthesis
- Session-based authentication with HttpOnly cookies and CSRF protection
- Voice interaction API surface
- Per-user settings
