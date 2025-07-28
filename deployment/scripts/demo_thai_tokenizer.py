#!/usr/bin/env python3
"""
Thai Tokenizer Demonstration Script

This script demonstrates practical usage scenarios for the Thai Tokenizer API,
showing real-world examples of Thai text processing, compound word handling,
and search query enhancement.

Usage:
    python3 deployment/scripts/demo_thai_tokenizer.py

Requirements:
    - Thai Tokenizer service running on localhost:8001
    - requests library installed
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def demo_basic_tokenization():
    """Demo basic Thai tokenization"""
    print("🔤 DEMO 1: Basic Thai Tokenization")
    print("=" * 40)
    
    texts = [
        "สวัสดีครับ",
        "ปัญญาประดิษฐ์",
        "การเรียนรู้ของเครื่อง",
        "เทคโนโลยีสารสนเทศ"
    ]
    
    for text in texts:
        response = requests.post(
            f"{BASE_URL}/api/v1/tokenize",
            json={"text": text}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Input:  {text}")
            print(f"Output: {' | '.join(data['tokens'])}")
            print(f"Time:   {data['processing_time_ms']}ms")
            print()

def demo_compound_words():
    """Demo compound word handling"""
    print("🔗 DEMO 2: Compound Word Handling")
    print("=" * 40)
    
    compound_examples = [
        "รัฐมนตรีกระทรวงศึกษาธิการ",
        "สำนักงานคณะกรรมการการศึกษาขั้นพื้นฐาน",
        "เทคโนโลยีสารสนเทศและการสื่อสาร",
        "การประชุมคณะกรรมการบริหาร"
    ]
    
    for text in compound_examples:
        response = requests.post(
            f"{BASE_URL}/api/v1/tokenize",
            json={"text": text}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Compound: {text}")
            print(f"Tokens:   {' + '.join(data['tokens'])}")
            print(f"Count:    {len(data['tokens'])} tokens")
            print()

def demo_mixed_content():
    """Demo mixed Thai-English content"""
    print("🌐 DEMO 3: Mixed Thai-English Content")
    print("=" * 40)
    
    mixed_texts = [
        "การพัฒนา AI ในประเทศไทย",
        "Machine Learning และ Deep Learning",
        "บริษัท Google ประเทศไทย",
        "COVID-19 ในประเทศไทย"
    ]
    
    for text in mixed_texts:
        response = requests.post(
            f"{BASE_URL}/api/v1/tokenize",
            json={"text": text}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Mixed:  {text}")
            print(f"Tokens: {data['tokens']}")
            print()

def demo_search_query_processing():
    """Demo search query processing"""
    print("🔍 DEMO 4: Search Query Processing")
    print("=" * 40)
    
    queries = [
        "ปัญญาประดิษฐ์",
        "การเรียนรู้",
        "เทคโนโลยี AI"
    ]
    
    for query in queries:
        response = requests.post(
            f"{BASE_URL}/api/v1/query/process",
            json={
                "query": query,
                "options": {"expand_compounds": True}
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Query: {query}")
            print(f"Processed: {data['processed_query']}")
            print(f"Variants: {data['search_variants'][:3]}...")  # Show first 3
            print(f"Tokens: {len(data['query_tokens'])}")
            print()

def demo_performance_comparison():
    """Demo performance with different text lengths"""
    print("⚡ DEMO 5: Performance Comparison")
    print("=" * 40)
    
    texts = {
        "Short": "ปัญญาประดิษฐ์",
        "Medium": "การพัฒนาเทคโนโลยีปัญญาประดิษฐ์ในประเทศไทย",
        "Long": "การพัฒนาเทคโนโลยีปัญญาประดิษฐ์และการเรียนรู้ของเครื่องในประเทศไทยเป็นสิ่งสำคัญสำหรับการเติบโตทางเศรษฐกิจและสังคมในอนาคต เทคโนโลยีเหล่านี้จะช่วยเพิ่มประสิทธิภาพในการทำงานและสร้างนวัตกรรมใหม่ๆ ที่จะนำไปสู่การพัฒนาประเทศอย่างยั่งยืน"
    }
    
    for length, text in texts.items():
        response = requests.post(
            f"{BASE_URL}/api/v1/tokenize",
            json={"text": text}
        )
        
        if response.status_code == 200:
            data = response.json()
            char_count = len(text)
            token_count = len(data['tokens'])
            processing_time = data['processing_time_ms']
            speed = char_count / (processing_time / 1000) if processing_time > 0 else 0
            
            print(f"{length} Text:")
            print(f"  Characters: {char_count}")
            print(f"  Tokens: {token_count}")
            print(f"  Time: {processing_time}ms")
            print(f"  Speed: {speed:.0f} chars/sec")
            print()

def demo_thai_japanese_compounds():
    """Demo Thai-Japanese compound words like wakame seaweed"""
    print("🌊 DEMO 6: Thai-Japanese Compound Words")
    print("=" * 40)
    
    thai_japanese_examples = {
        "Wakame Seaweed": "สาหร่ายวากาเมะเป็นอาหารทะเลที่มีประโยชน์",
        "Ramen Noodles": "ราเมนต้นตำรับจากญี่ปุ่นรสชาติเข้มข้น", 
        "Sashimi Fish": "ซาชิมิปลาแซลมอนสดใหม่จากตลาดปลา",
        "Miso Soup": "ซุปมิโซะร้อนๆ เหมาะกับอากาศหนาว",
        "Tempura Style": "เทมปุระผักสไตล์ญี่ปุ่นแท้"
    }
    
    for category, text in thai_japanese_examples.items():
        response = requests.post(
            f"{BASE_URL}/api/v1/tokenize",
            json={"text": text}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"{category}:")
            print(f"  Text: {text}")
            print(f"  Tokens: {' | '.join(data['tokens'])}")
            print(f"  Count: {len(data['tokens'])} tokens")
            print()

def demo_real_world_examples():
    """Demo with real-world Thai text examples"""
    print("🌍 DEMO 7: Real-World Examples")
    print("=" * 40)
    
    examples = {
        "News Headline": "รัฐบาลเร่งพัฒนาเทคโนโลยีดิจิทัลเพื่อเศรษฐกิจไทย",
        "Academic Text": "การวิจัยด้านปัญญาประดิษฐ์ในมหาวิทยาลัยไทย",
        "Business": "บริษัทเทคโนโลยีสารสนเทศแห่งประเทศไทย จำกัด",
        "Government": "กระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม",
        "Food Review": "ร้านอาหารญี่ปุ่นเสิร์ฟสาหร่ายวากาเมะสดใหม่"
    }
    
    for category, text in examples.items():
        response = requests.post(
            f"{BASE_URL}/api/v1/tokenize",
            json={"text": text}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"{category}:")
            print(f"  Text: {text}")
            print(f"  Tokens: {' | '.join(data['tokens'])}")
            print(f"  Count: {len(data['tokens'])} tokens")
            print()

def main():
    """Run all demos"""
    print("🚀 Thai Tokenizer Practical Demos")
    print("=" * 50)
    
    # Check if service is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Service not available. Please start the Thai tokenizer first.")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Thai tokenizer. Please start the service first.")
        return
    
    print("✅ Service is running. Starting demos...\n")
    
    # Run all demos
    demo_basic_tokenization()
    demo_compound_words()
    demo_mixed_content()
    demo_search_query_processing()
    demo_performance_comparison()
    demo_thai_japanese_compounds()
    demo_real_world_examples()
    
    print("🎉 All demos completed!")
    print("\n💡 Tips:")
    print("- Visit http://localhost:8001/docs for full API documentation")
    print("- Use the tokenizer for Thai search applications")
    print("- Integrate with MeiliSearch for full-text search")
    print("- Monitor performance with the health endpoint")

if __name__ == "__main__":
    main()