# AntiFake — Agents Guide

This repo is pre-implementation. No code, configs, or tooling exist yet.

## Source of truth

- **`product.md`** — product spec, architecture decisions, and roadmap for a closed-loop anti-counterfeit verification system (mobile app + Python backend + EVM blockchain + Redis).
- All future implementation should reference `product.md` first for product intent and architecture constraints.

## Current state

- No build system, language runtime, package manager, or CI configured.
- No entrypoints, no tests, no deployment pipeline.
- First task on this repo: scaffold the chosen stack (likely React Native frontend, Python/FastAPI backend, Redis cache, EVM smart contracts).

## Project identity

- Name: AntiFake
- Domain: pharmaceutical anti-counterfeit with spatial-temporal anomaly detection, crypto-anchor verification, and Community Shield database.
