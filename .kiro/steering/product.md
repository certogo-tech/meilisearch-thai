# Product Overview

This project implements a custom Thai tokenizer for MeiliSearch to address the challenge of searching Thai compound words. Thai language lacks spaces between words, making compound word segmentation critical for accurate search results.

## Core Problem
MeiliSearch's default tokenization cannot properly handle Thai compound words, leading to poor search accuracy when users search for partial compound terms.

## Solution
A containerized Thai tokenization service that integrates with MeiliSearch through:
- Pre-processing pipeline for Thai text segmentation
- Custom MeiliSearch configuration for Thai word boundaries
- REST API for tokenization and document processing

## Key Features
- Accurate Thai compound word segmentation using PyThaiNLP
- Docker containerization for easy deployment
- REST API for integration and configuration
- Support for mixed Thai-English content
- Performance monitoring and health checks

## Target Users
- Developers integrating Thai search capabilities
- System administrators deploying search solutions
- Content managers working with Thai documents